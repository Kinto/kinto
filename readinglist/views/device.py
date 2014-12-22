import json
from cornice import Service

from readinglist.decorators import exists_or_404


devices = Service(name="devices",
                  path='/devices',
                  description="Collection of devices.")


device = Service(name="device",
                 path='/devices/{record_id}',
                 description="Single device.")


@devices.get()
def get_devices(request):
    """List of devices of user."""
    devices = request.db.get_all('device', '')
    body = {
        '_items': devices
    }
    return body


@devices.post()
def create_device(request):
    """Create device for user."""
    device = json.loads(request.body)
    device = request.db.create('device', '', device)
    return device


@device.get()
@exists_or_404()
def get_device(request):
    """Fetch single device of user."""
    record_id = request.matchdict['record_id']
    device = request.db.get('device', '', record_id)
    return device


@device.patch()
@exists_or_404()
def modify_device(request):
    """Modify device of user."""
    record_id = request.matchdict['record_id']
    device = json.loads(request.body)
    device = request.db.update('device', '', record_id, device)
    return device


@device.delete()
@exists_or_404()
def delete_device(request):
    """Delete device of user."""
    record_id = request.matchdict['record_id']
    device = request.db.delete('device', '', record_id)
    return device
