from collections import OrderedDict

from cliquet.utils import strip_uri_prefix, Enum, current_service


ACTIONS = Enum(CREATE='create',
               DELETE='delete',
               READ='read',
               UPDATE='update')


class _ResourceEvent(object):
    def __init__(self, action, resource, request):
        self.request = request
        # XXX: Move to reified request method.
        service = current_service(request)
        resource_name = service.viewset.get_name(resource.__class__)

        self.payload = {'timestamp': resource.timestamp,
                        'action': action,
                        'uri': strip_uri_prefix(request.path),
                        'user_id': request.prefixed_userid,
                        'resource_name': resource_name}

        matchdict = dict(request.matchdict)

        if 'id' in request.matchdict:
            matchdict[resource_name + '_id'] = matchdict.pop('id')

        self.payload.update(**matchdict)


class ResourceRead(_ResourceEvent):
    """Triggered when a resource is read.
    """
    def __init__(self, action, resource, read_records, request):
        super(ResourceRead, self).__init__(action, resource, request)
        self.read_records = read_records


class ResourceChanged(_ResourceEvent):
    """Triggered when a resource is changed.
    """
    def __init__(self, action, resource, impacted_records, request):
        super(ResourceChanged, self).__init__(action, resource, request)
        self.impacted_records = impacted_records


def get_resource_events(request, ):
    events = request.bound_data.get("resource_events")
    if events is None:
        return []
    return events.values()


def notify_resource_event(request, resource, data, action, old):
    """
    XXX
    """
    if action == ACTIONS.READ:
        if not isinstance(data, list):
            data = [data]
        impacted = data
    elif action == ACTIONS.CREATE:
        impacted = [{'new': data}]
    elif action == ACTIONS.DELETE:
        if not isinstance(data, list):
            data = [data]
        impacted = [{'old': r} for r in data]
    elif action == ACTIONS.UPDATE:
        impacted = [{'new': data, 'old': old}]

    # Get previously triggered events.
    events = request.bound_data.setdefault("resource_events", OrderedDict())
    # XXX: Move to reified request method
    service = current_service(request)
    resource_name = service.viewset.get_name(resource.__class__)

    # Add to impacted records or create new event.
    group_by = resource_name + action
    if group_by in events:
        events[group_by].impacted_records.extend(impacted)
    else:
        if action == ACTIONS.READ:
            event_cls = ResourceRead
        else:
            event_cls = ResourceChanged
        event = event_cls(action, resource, impacted, request)
        events[group_by] = event
