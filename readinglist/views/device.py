import json
from cornice import Service


devices = Service(name="devices",
                  path='/devices',
                  description="Collection of devices.")


device = Service(name="device",
                 path='/devices/{device_id}',
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
def get_device(request):
    """Fetch single device of user."""
    device_id = request.matchdict['device_id']
    device = request.db.get('device', '', device_id)
    return device


@device.patch()
def modify_device(request):
    """Modify device of user."""
    device_id = request.matchdict['device_id']
    device = json.loads(request.body)
    device = request.db.update('device', '', device_id, device)
    return device


@device.delete()
def delete_device(request):
    """Delete device of user."""
    device_id = request.matchdict['device_id']
    device = request.db.delete('device', '', device_id)
    return device
