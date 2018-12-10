import logging
import getpass

import transaction as current_transaction
from pyramid.settings import asbool

from .utils import hash_password
from .views import AccountIdGenerator


logger = logging.getLogger(__name__)


def create_user(env, username=None, password=None):
    """Administrative command to create a new user."""
    registry = env["registry"]
    settings = registry.settings
    readonly_mode = asbool(settings.get("readonly", False))
    if readonly_mode:
        message = "Cannot create a user with a readonly server."
        logger.error(message)
        return 51

    if "kinto.plugins.accounts" not in settings["includes"]:
        message = "Cannot create a user when the accounts plugin is not installed."
        logger.error(message)
        return 52

    try:
        validator = AccountIdGenerator()
        if username is None:
            username = input("Username: ")
        while not validator.match(username):
            print("{} is not a valid username.")
            print(f"Username should match {validator.regexp}, please try again.")
            username = input("Username: ")

        if password is None:
            while True:  # The user didn't entered twice the same password
                password = getpass.getpass(f"Please enter a password for {username}: ")
                confirm = getpass.getpass("Please confirm the password: ".format(username))

                if password != confirm:
                    print("Sorry, passwords do not match, please try again.")
                else:
                    break
    except EOFError:
        print("User creation aborted")
        return 53

    print(f"Creating user '{username}'")
    entry = {"id": username, "password": hash_password(password)}
    registry.storage.update(
        resource_name="account", parent_id=username, object_id=username, obj=entry
    )
    registry.permission.add_principal_to_ace(
        f"/accounts/{username}", "write", f"account:{username}"
    )

    current_transaction.commit()

    return 0
