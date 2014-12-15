from eve.auth import BasicAuth


class FxaAuth(BasicAuth):
    def check_auth(self, username, password, allowed_roles, resource,
                   method):
        accounts = [('alice', 'secret'), ('john', 'secret')]
        userid = accounts.index((username, password)) + 1
        self.set_request_auth_value(userid)
        return userid > 0
