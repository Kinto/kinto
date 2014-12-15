from eve.auth import BasicAuth


class FxaAuth(BasicAuth):
    def check_auth(self, username, password, allowed_roles, resource,
                   method):
        self.set_request_auth_value(username)
        return (username, password) in [('alice', 'secret'), ('john', 'secret')]
