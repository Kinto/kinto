from collections import OrderedDict

from cliquet.utils import strip_uri_prefix, Enum, current_service


ACTIONS = Enum(CREATE='create',
               DELETE='delete',
               READ='read',
               UPDATE='update')


class _ResourceEvent(object):
    def __init__(self, action, resource, request):
        self.request = request
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


def merge_by_resource(events):
    """
    Emit a :class:`cliquet.event.ResourceChanged` event with the
    impacted records.
    """
    merged = OrderedDict()
    for event in events:
        group_by = '{resource_name}-{action}'.format(**event.payload)
        if group_by not in merged:
            merged[group_by] = event
        else:
            impacted_records = event.impacted_records
            merged[group_by].impacted_records.extend(impacted_records)
    return merged.values()


def build_event(resource, request, result, action, old):
    """
    """
    if not isinstance(result, list):
        result = [result]

    if action == ACTIONS.READ:
        event_cls = ResourceRead
    else:
        event_cls = ResourceChanged

    if action == ACTIONS.READ:
        impacted = result
    elif action == ACTIONS.CREATE:
        impacted = [{'new': r} for r in result]
    elif action == ACTIONS.DELETE:
        impacted = [{'old': r} for r in result]
    elif action == ACTIONS.UPDATE:
        # XXX `old` is "always" the same, since currently, we can only
        # notify one update at a time.
        # This code will change when plugged with transactions (and batch).
        impacted = [{'new': r, 'old': old} for r in result]

    event = event_cls(action, resource, impacted, request)
    return event
