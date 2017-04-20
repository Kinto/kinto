import os
import pkg_resources

from pyramid.compat import string_types

from pyramid.path import (
    package_path,
    package_name,
    )

def resolve_asset_spec(spec, pname='__main__'):
    if pname and not isinstance(pname, string_types):
        pname = pname.__name__ # as package
    if os.path.isabs(spec):
        return None, spec
    filename = spec
    if ':' in spec:
        pname, filename = spec.split(':', 1)
    elif pname is None:
        pname, filename = None, spec
    return pname, filename

def asset_spec_from_abspath(abspath, package):
    """ Try to convert an absolute path to a resource in a package to
    a resource specification if possible; otherwise return the
    absolute path.  """
    if getattr(package, '__name__', None) == '__main__':
        return abspath
    pp = package_path(package) + os.path.sep
    if abspath.startswith(pp):
        relpath = abspath[len(pp):]
        return '%s:%s' % (package_name(package),
                          relpath.replace(os.path.sep, '/'))
    return abspath

# bw compat only; use pyramid.path.AssetDescriptor.abspath() instead
def abspath_from_asset_spec(spec, pname='__main__'):
    if pname is None:
        return spec
    pname, filename = resolve_asset_spec(spec, pname)
    if pname is None:
        return filename
    return pkg_resources.resource_filename(pname, filename)

