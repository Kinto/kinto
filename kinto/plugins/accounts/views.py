import colander
from pyramid import httpexceptions
from pyramid.decorator import reify
from pyramid.security import Authenticated, Everyone
from pyramid.settings import aslist
from pyramid.events import subscriber

from kinto.views import NameGenerator
from kinto.core import resource, utils
from kinto.core.errors import raise_invalid, http_error
from kinto.core.events import ResourceChanged, ACTIONS

from .utils import hash_password, ACCOUNT_CACHE_KEY, ACCOUNT_POLICY_NAME


def _extract_posted_body_id(request):
    try:
        # Anonymous creation with POST.
        return request.json["data"]["id"]
    except (ValueError, KeyError):
        # Bad POST data.
        if request.method.lower() == "post":
            error_details = {"name": "data.id", "description": "data.id in body: Required"}
            raise_invalid(request, **error_details)
        # Anonymous GET
        error_msg = "Cannot read accounts."
        raise http_error(httpexceptions.HTTPUnauthorized(), error=error_msg)


class AccountIdGenerator(NameGenerator):
    """Allow @ signs in account IDs."""

    regexp = r"^[a-zA-Z0-9][.@a-zA-Z0-9_-]*$"


class AccountSchema(resource.ResourceSchema):
    password = colander.SchemaNode(colander.String())


@resource.register()
class Account(resource.ShareableResource):

    schema = AccountSchema

    def __init__(self, request, context):
        # Store if current user is administrator (before accessing get_parent_id())
        allowed_from_settings = request.registry.settings.get("account_write_principals", [])
        context.is_administrator = (
            len(set(aslist(allowed_from_settings)) & set(request.prefixed_principals)) > 0
        )
        # Shortcut to check if current is anonymous (before get_parent_id()).
        context.is_anonymous = Authenticated not in request.effective_principals

        super().__init__(request, context)

        # Overwrite the current principal set by ShareableResource.
        if self.model.current_principal == Everyone or context.is_administrator:
            # Creation is anonymous, but author with write perm is this:
            self.model.current_principal = f"{ACCOUNT_POLICY_NAME}:{self.model.parent_id}"

    @reify
    def id_generator(self):
        # This generator is used for ID validation.
        return AccountIdGenerator()

    def get_parent_id(self, request):
        # The whole challenge here is that we want to isolate what
        # authenticated users can list, but give access to everything to
        # administrators.
        # Plus when anonymous create accounts, we have to set their parent id
        # to the same value they would obtain when authenticated.
        if self.context.is_administrator:
            if self.context.on_collection:
                # Accounts created by admin should have userid as parent.
                if request.method.lower() == "post":
                    return _extract_posted_body_id(request)
                else:
                    # Admin see all accounts.
                    return "*"
            else:
                # No pattern matching for admin on single record.
                return request.matchdict["id"]

        if not self.context.is_anonymous:
            # Authenticated users see their own account only.
            return request.selected_userid

        # Anonymous creation with PUT.
        if "id" in request.matchdict:
            return request.matchdict["id"]

        return _extract_posted_body_id(request)

    def collection_post(self):
        result = super(Account, self).collection_post()
        if self.context.is_anonymous and self.request.response.status_code == 200:
            error_details = {"message": "Account ID %r already exists" % result["data"]["id"]}
            raise http_error(httpexceptions.HTTPForbidden(), **error_details)
        return result

    def process_record(self, new, old=None):
        new = super(Account, self).process_record(new, old)

        new["password"] = hash_password(new["password"])

        # Administrators can reach other accounts and anonymous have no
        # selected_userid. So do not try to enforce.
        if self.context.is_administrator or self.context.is_anonymous:
            return new

        # Do not let accounts be created without usernames.
        if self.model.id_field not in new:
            error_details = {"name": "data.id", "description": "Accounts must have an ID."}
            raise_invalid(self.request, **error_details)

        # Otherwise, we force the id to match the authenticated username.
        if new[self.model.id_field] != self.request.selected_userid:
            error_details = {
                "name": "data.id",
                "description": "Username and account ID do not match.",
            }
            raise_invalid(self.request, **error_details)

        return new


# Clear cache on account change
@subscriber(
    ResourceChanged, for_resources=("account",), for_actions=(ACTIONS.UPDATE, ACTIONS.DELETE)
)
def on_account_changed(event):
    request = event.request
    cache = request.registry.cache
    settings = request.registry.settings
    # Extract username and password from current user
    username = request.matchdict["id"]
    hmac_secret = settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_CACHE_KEY.format(username))
    # Delete cache
    cache.delete(cache_key)
