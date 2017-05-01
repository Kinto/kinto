import logging
from collections import OrderedDict

import transaction
from pyramid.events import NewRequest
from enum import Enum

from kinto.core.utils import strip_uri_prefix


logger = logging.getLogger(__name__)


class ACTIONS(Enum):
    CREATE = 'create'
    DELETE = 'delete'
    READ = 'read'
    UPDATE = 'update'

    @staticmethod
    def from_string_list(elements):
        return tuple(ACTIONS(el) for el in elements)


class _ResourceEvent:
    def __init__(self, payload, request):
        self.payload = payload
        self.request = request

    def __repr__(self):
        return "<{klass} action={action} uri={uri}>".format(
            klass=self.__class__.__name__,
            **self.payload)


class ResourceRead(_ResourceEvent):
    """Triggered when a resource is being read.
    """
    def __init__(self, payload, read_records, request):
        super().__init__(payload, request)
        self.read_records = read_records


class ResourceChanged(_ResourceEvent):
    """Triggered when a resource is being changed.
    """
    def __init__(self, payload, impacted_records, request):
        super().__init__(payload, request)
        self.impacted_records = impacted_records


class AfterResourceRead(_ResourceEvent):
    """Triggered after a resource was successfully read.
    """
    def __init__(self, payload, read_records, request):
        super().__init__(payload, request)
        self.read_records = read_records


class AfterResourceChanged(_ResourceEvent):
    """Triggered after a resource was successfully changed.
    """
    def __init__(self, payload, impacted_records, request):
        super().__init__(payload, request)
        self.impacted_records = impacted_records


def setup_transaction_hook(config):
    """
    Resource events are plugged with the transactions of ``pyramid_tm``.

    Once a transaction is committed, ``AfterResourceRead`` and
    ``AfterResourceChanged`` events are sent.
    """
    def _notify_resource_events_before(request):
        """Notify the accumulated resource events before end of transaction.
        """
        for event in request.get_resource_events():
            request.registry.notify(event)

    def _notify_resource_events_after(success, request):
        """Notify the accumulated resource events if transaction succeeds.
        """
        if not success:  # pragma: no cover
            return

        for event in request.get_resource_events(after_commit=True):
            try:
                request.registry.notify(event)
            except Exception:
                logger.error("Unable to notify", exc_info=True)

    def on_new_request(event):
        """When a new request comes in, hook on transaction commit.
        """
        # Since there is one transaction per batch, ignore subrequests.
        if hasattr(event.request, 'parent'):
            return
        current = transaction.get()
        current.addBeforeCommitHook(_notify_resource_events_before,
                                    args=(event.request,))
        current.addAfterCommitHook(_notify_resource_events_after,
                                   args=(event.request,))

    config.add_subscriber(on_new_request, NewRequest)


def get_resource_events(request, after_commit=False):
    """
    Request helper to return the list of events triggered on resources.
    The list is sorted chronologically (see OrderedDict)
    """
    by_resource = request.bound_data.get("resource_events", {})
    events = []
    for (action, payload, impacted, request) in by_resource.values():
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
        event = event_cls(payload, impacted, request)
        events.append(event)
    return events


def notify_resource_event(request, parent_id, timestamp, data, action,
                          old=None):
    """
    Request helper to stack a resource event.

    If a similar event (same resource, same action) already occured during the
    current transaction (e.g. batch) then just extend the impacted records of
    the previous one.
    """
    if action == ACTIONS.READ:
        if not isinstance(data, list):
            data = [data]
        impacted = data
    elif action == ACTIONS.CREATE:
        impacted = [{'new': data}]
    elif action == ACTIONS.DELETE:
        if not isinstance(data, list):
            impacted = [{'new': data, 'old': old}]
        else:
            impacted = []
            for i, new in enumerate(data):
                impacted.append({'new': new, 'old': old[i]})
    else:  # ACTIONS.UPDATE:
        impacted = [{'new': data, 'old': old}]

    # Get previously triggered events.
    events = request.bound_data.setdefault("resource_events", OrderedDict())

    resource_name = request.current_resource_name

    # Group events by resource and action.
    group_by = '{}-{}-{}'.format(resource_name, parent_id, action.value)

    if group_by in events:
        # Add to impacted records of existing event.
        already_impacted = events[group_by][2]
        already_impacted.extend(impacted)
    else:
        # Create new event.
        payload = {'timestamp': timestamp,
                   'action': action.value,
                   'uri': strip_uri_prefix(request.path),
                   'user_id': request.prefixed_userid,
                   'resource_name': resource_name}

        matchdict = dict(request.matchdict)

        if 'id' in request.matchdict:
            matchdict[resource_name + '_id'] = matchdict.pop('id')

        payload.update(**matchdict)

        events[group_by] = (action, payload, impacted, request)
