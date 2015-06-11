from cliquet.authorization import AuthorizationPolicy as CliquetAuthorization
from pyramid.security import IAuthorizationPolicy, Authenticated
from zope.interface import implementer

from kinto.permission import build_permissions_set


@implementer(IAuthorizationPolicy)
class AuthorizationPolicy(CliquetAuthorization):
    def get_bound_permissions(self, *args, **kwargs):
        return build_permissions_set(*args, **kwargs)

    def permits(self, context, principals, permission):
        is_bucket_creation = (context.resource_name == 'bucket' and
                              context.required_permission == 'create')

        if is_bucket_creation:
            # XXX: Read settings.
            return Authenticated in principals

        return super(AuthorizationPolicy, self).permits(context,
                                                        principals,
                                                        permission)
