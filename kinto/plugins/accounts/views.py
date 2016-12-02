import functools

import colander
from pyramid.settings import aslist
from pyramid.exceptions import HTTPForbidden
from pyramid.security import Authenticated

from kinto.core import resource
from kinto.core.resource.viewset import ShareableViewSet
from kinto.core import utils
from kinto.core import authorization
from kinto.views import NameGenerator
from kinto.core.errors import raise_invalid, http_error


class AccountSchema(resource.ResourceSchema):
    password = colander.SchemaNode(colander.String())


# class AccountRouteFactory(authorization.RouteFactory):
#     def __init__(self, request):
#         settings = request.registry.settings
#         account_administrators = aslist(settings.get('account_write_principals', []))
#         self.is_administrator = len(set(request.prefixed_principals) & set(account_administrators)) > 0
#         super(AccountRouteFactory, self).__init__(request)


# class ViewSet(resource.ViewSet):
#     def get_view_arguments(self, endpoint_type, resource_cls, method):
#         args = super(AccountViewSet, self).get_view_arguments(endpoint_type,
#                                                               resource_cls,
#                                                               method)
#         if method.lower() not in ('get', 'head'):
#             args['permission'] = 'write'
#         else:
#             args['permission'] = 'read'
#         return args

#     def get_service_arguments(self):
#         args = super(AccountViewSet, self).get_service_arguments()
#         args['factory'] = authorization.RouteFactory
#         return args


# @resource.register(viewset=ShareableViewSet())
# class Account(resource.UserResource):

class LowerCaseGenerator(NameGenerator):
    def __call__(self):
        gen = super(LowerCaseGenerator, self).__call__()
        return gen.lower()


@resource.register()
class Account(resource.ShareableResource):

    schema = AccountSchema
    permissions = ('read', 'write')

    def __init__(self, *args, **kwargs):
        super(Account, self).__init__(*args, **kwargs)
        self.model.id_generator = LowerCaseGenerator()
        # XXX: this will go into new account `write` principals
        self.model.current_principal = 'account:%s' % self.model.parent_id

    def get_parent_id(self, request):

        self.context.is_administrator = len(set(self.context.allowed_principals(permission='write')) &
                                            set(request.prefixed_principals)) > 0
        if self.context.is_administrator:
            if self.context.on_collection:
                return '*'  # Return all with same collection_id (i.e. 'account')
            else:
                return request.matchdict['id']

        if Authenticated in request.effective_principals:
            return request.unauthenticated_userid

        if 'id' in request.matchdict:
            return request.matchdict['id']

        try:
            return request.json['data']['id']
        except (ValueError, KeyError) as e:
            return '__no_match__'

    def collection_post(self):
        result = super(Account, self).collection_post()
        is_anonymous = Authenticated not in self.request.effective_principals
        if is_anonymous and self.request.response.status_code == 200:
            error_details = {
                'message': 'User %r already exists' % result['data']['id']
            }
            raise http_error(HTTPForbidden(), **error_details)
        return result

    def process_record(self, new, old=None):
        new = super(Account, self).process_record(new, old)

        # XXX: bcrypt whatever
        # new["password"] = bcrypt(...)

        # When creating accounts, we are anonymous.
        if Authenticated not in self.request.effective_principals:
            return new

        # Otherwise, we force the id to match the authenticated username.
        if not self.context.is_administrator and new[self.model.id_field] != self.request.selected_userid:
            error_details = {
                'name': 'data',
                'description': 'Username and account id do not match.',
            }
            raise_invalid(self.request, **error_details)

        return new
