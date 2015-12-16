""" Backwards compatibility shim module (forever). """
from pyramid.asset import * # b/w compat
resolve_resource_spec = resolve_asset_spec
resource_spec_from_abspath = asset_spec_from_abspath
abspath_from_resource_spec = abspath_from_asset_spec
