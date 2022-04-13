import logging
import warnings
from collections import OrderedDict
from enum import Enum

import pyramid.tweens
import transaction
from pyramid.events import NewRequest

from kinto.core.utils import strip_uri_prefix

logger = logging.getLogger(__name__)


class ACTIONS(Enum):
    CREATE = "create"
    DELETE = "delete"
    READ = "read"
    UPDATE = "update"

    @staticmethod
    def from_string_list(elements):
        return tuple(ACTIONS(el) for el in elements)


class _ResourceEvent:
    def __init__(self, payload, request):
        self.payload = payload
        self.request = request

    def __repr__(self):
        return f"<{self.__class__.__name__} action={self.payload['action']} uri={self.payload['uri']}>"

    @property
    def read_records(self):
        message = "`read_records` is deprecated, use `read_objects` instead."
        warnings.warn(message, DeprecationWarning)
        return self.read_objects

    @property
    def impacted_records(self):
        message = "`impacted_records` is deprecated, use `impacted_objects` instead."
        warnings.warn(message, DeprecationWarning)
        return self.impacted_objects


class ResourceRead(_ResourceEvent):
    """Triggered when a resource is being read."""

    def __init__(self, payload, read_objects, request):
        super().__init__(payload, request)
        self.read_objects = read_objects


class ResourceChanged(_ResourceEvent):
    """Triggered when a resource is being changed."""

    def __init__(self, payload, impacted_objects, request):
        super().__init__(payload, request)
        self.impacted_objects = impacted_objects


class AfterResourceRead(_ResourceEvent):
    """Triggered after a resource was successfully read."""

    def __init__(self, payload, read_objects, request):
        super().__init__(payload, request)
        self.read_objects = read_objects


class AfterResourceChanged(_ResourceEvent):
    """Triggered after a resource was successfully changed."""

    def __init__(self, payload, impacted_objects, request):
        super().__init__(payload, request)
        self.impacted_objects = impacted_objects


class EventCollector(object):
    """A collection to gather events emitted over the course of a request.

    Events are gathered by parent id, resource type, and event
    type. This serves as a primitive normalization so that we can emit
    fewer events.
    """

    def __init__(self, cascade_level=1):
        self.cascade_level = cascade_level
        """Current level of event cascade. When we start consuming the
        gathered events, we increment it. This way, events emitted from
        events listeners (cascade) are not merged with upstream ones.
        """

        self.event_dict = OrderedDict()
        """The events as collected so far.

        The key of the event_dict is a quadruple (cascade_level, resource_name,
        parent_id, action). The value is a triple (impacted, request,
        payload). If the same (cascade_level, resource_name, parent_id, action) is
        encountered, we just extend the existing impacted with the new
        impacted. N.B. this means all values in the payload must not
        be specific to a single impacted_object. See
        https://github.com/Kinto/kinto/issues/945 and
        https://github.com/Kinto/kinto/issues/1731.
        """

    def add_event(self, resource_name, parent_id, action, payload, impacted, request):
        key = (self.cascade_level, resource_name, parent_id, action)
        if key not in self.event_dict:
            value = (payload, impacted, request)
            self.event_dict[key] = value
        else:
            old_value = self.event_dict[key]
            (old_payload, old_impacted, old_request) = old_value
            # May be a good idea to assert that old_payload == payload here.
            self.event_dict[key] = (old_payload, old_impacted + impacted, old_request)

    def drain(self):
        """Return an iterator that removes elements from this EventCollector.

        This can be used to process events while still allowing events
        to be added (for instance, as part of a cascade where events
        add other events).

        Items yielded will be of a tuple suitable for using as
        arguments to EventCollector.add_event.
        """
        # Since we start consuming the gathered events, we increment the cascade level.
        self.cascade_level += 1
        return EventCollectorDrain(self)


class EventCollectorDrain(object):
    """An iterator that drains an EventCollector.

    Get one using EventCollector.drain()."""

    def __init__(self, event_collector):
        self.event_collector = event_collector

    def __iter__(self):
        return self

    def __next__(self):
        if self.event_collector.event_dict:
            # Get the "first" key in insertion order, so as to process
            # events in the same order they were queued.
            key = next(iter(self.event_collector.event_dict.keys()))
            value = self.event_collector.event_dict.pop(key)
            return key + value
        else:
            raise StopIteration


def notify_resource_events_before(handler, registry):
    """Tween that runs ResourceChanged events.

    This tween runs under EXCVIEW, so exceptions raised by
    ResourceChanged events are caught and dealt the same as any other
    exceptions.

    """

    def tween(request):
        response = handler(request)
        for event in request.get_resource_events():
            request.registry.notify(event)

        return response

    return tween


def setup_transaction_hook(config):
    """
    Resource events are plugged with the transactions of ``pyramid_tm``.

    Once a transaction is committed, ``AfterResourceRead`` and
    ``AfterResourceChanged`` events are sent.
    """

    def _notify_resource_events_after(success, request):
        """Notify the accumulated resource events if transaction succeeds."""
        if not success:  # pragma: no cover
            return

        for event in request.get_resource_events(after_commit=True):
            try:
                request.registry.notify(event)
            except Exception:
                logger.error("Unable to notify", exc_info=True)

    def on_new_request(event):
        """When a new request comes in, hook on transaction commit."""
        # Since there is one transaction per batch, ignore subrequests.
        if hasattr(event.request, "parent"):
            return
        current = transaction.get()
        current.addAfterCommitHook(_notify_resource_events_after, args=(event.request,))

    config.add_subscriber(on_new_request, NewRequest)
    config.add_tween(
        "kinto.core.events.notify_resource_events_before", under=pyramid.tweens.EXCVIEW
    )


def get_resource_events(request, after_commit=False):
    """Generator to iterate the list of events triggered on resources.

    The list is sorted chronologically (see OrderedDict).

    This drains the resource_events currently in the request, which
    allows us to process new events as they are added by current
    events. However, once the iteration is over, we merge all the
    events we've emitted into a new resource_events, which we store on
    the request so we can reprocess the same events in an after-commit
    tween.

    This generator must be completely consumed!
    """
    by_resource = request.bound_data.get("resource_events", EventCollector())
    afterwards = EventCollector()

    for event in by_resource.drain():
        (_, resource_name, parent_id, action, payload, impacted, request) = event
        afterwards.add_event(resource_name, parent_id, action, payload, impacted, request)

        if after_commit:
            if action == ACTIONS.READ:
                event_cls = AfterResourceRead
            else:
                event_cls = AfterResourceChanged
        else:
            if action == ACTIONS.READ:
                event_cls = ResourceRead
            else:
                event_cls = ResourceChanged

        yield event_cls(payload, impacted, request)

    request.bound_data["resource_events"] = afterwards


def notify_resource_event(
    request, parent_id, timestamp, data, action, old=None, resource_name=None, resource_data=None
):
    """Request helper to stack a resource event.

    If a similar event (same resource, same action) already occured during the
    current transaction (e.g. batch) then just extend the impacted objects of
    the previous one.

    :param resource_name: The name of the resource on which the event
        happened (taken from the request if not provided).
    :param resource_data: Information about the resource on which the
        event is being emitted. Usually contains information about how
        to find this object in the hierarchy (for instance,
        ``bucket_id`` and ``collection_id`` for a record). Taken from
        the request matchdict if absent.
    :type resource_data: dict

    """
    if action == ACTIONS.READ:
        if not isinstance(data, list):
            data = [data]
        impacted = data
    elif action == ACTIONS.CREATE:
        impacted = [{"new": data}]
    elif action == ACTIONS.DELETE:
        if not isinstance(data, list):
            impacted = [{"new": data, "old": old}]
        else:
            impacted = []
            for i, new in enumerate(data):
                impacted.append({"new": new, "old": old[i]})
    else:  # ACTIONS.UPDATE:
        impacted = [{"new": data, "old": old}]

    # Get previously triggered events.
    events = request.bound_data.setdefault("resource_events", EventCollector())

    resource_name = resource_name or request.current_resource_name
    matchdict = resource_data or dict(request.matchdict)

    payload = {
        "timestamp": timestamp,
        "action": action.value,
        # Deprecated: don't actually use URI (see #945).
        "uri": strip_uri_prefix(request.path),
        "user_id": request.prefixed_userid,
        "resource_name": resource_name,
    }

    # Deprecated: don't actually use `resource_name_id` either (see #945).
    if "id" in request.matchdict:
        matchdict[resource_name + "_id"] = matchdict.pop("id")

    payload.update(**matchdict)

    events.add_event(resource_name, parent_id, action, payload, impacted, request)
