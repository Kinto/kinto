import colander
from pyramid.exceptions import HTTPForbidden
from pyramid.security import Authenticated

from kinto.core import resource
from kinto.core.errors import raise_invalid, http_error


class AccountSchema(resource.ResourceSchema):
    password = colander.SchemaNode(colander.String())


@resource.register()
class Account(resource.UserResource):

    mapping = AccountSchema()

    def get_parent_id(self, request):
        # Only one parent for all records.
        return ''

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
        if new[self.model.id_field] != self.request.selected_userid:
            error_details = {
                'name': 'data',
                'description': 'Username and account id do not match.',
            }
            raise_invalid(self.request, **error_details)

        return new
