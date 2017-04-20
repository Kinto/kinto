# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Pyramid authn policy that ties together multiple backends.
"""
import sys

from zope.interface import implementer

from pyramid.interfaces import IAuthenticationPolicy, PHASE2_CONFIG
from pyramid.security import Everyone, Authenticated

__ver_major__ = 0
__ver_minor__ = 4
__ver_patch__ = 0
__ver_sub__ = ""
__ver_tuple__ = (__ver_major__, __ver_minor__, __ver_patch__, __ver_sub__)
__version__ = "%d.%d.%d%s" % __ver_tuple__


if sys.version_info > (3,):  # pragma: nocover
    basestring = str


class MultiAuthPolicySelected(object):
    """Event for tracking which authentication policy was used.

    This event is fired whenever a particular backend policy is successfully
    used for authentication.  It can be used by other parts of the code in
    order to act based on the selected policy::

        from pyramid.events import subscriber

        @subscriber(MultiAuthPolicySelected)
        def track_policy(event):
            print("We selected policy %s" % event.policy)

    """
    def __init__(self, policy, request, userid=None):
        self.policy = policy
        self.policy_name = getattr(policy, "_pyramid_multiauth_name", None)
        self.request = request
        self.userid = userid


@implementer(IAuthenticationPolicy)
class MultiAuthenticationPolicy(object):
    """Pyramid authentication policy for stacked authentication.

    This is a pyramid authentication policy that stitches together other
    authentication policies into a flexible auth stack.  You give it a
    list of IAuthenticationPolicy objects, and it will try each one in
    turn until it obtains a usable response:

        * authenticated_userid:    return userid from first successful policy
        * unauthenticated_userid:  return userid from first successful policy
        * effective_principals:    return union of principals from all policies
        * remember:                return headers from all policies
        * forget:                  return headers from all policies

    """

    def __init__(self, policies, callback=None):
        self._policies = policies
        self._callback = callback

    def authenticated_userid(self, request):
        """Find the authenticated userid for this request.

        This method delegates to each authn policy in turn, taking the
        userid from the first one that doesn't return None.  If a
        groupfinder callback is configured, it is also used to validate
        the userid before returning.
        """
        userid = None
        for policy in self._policies:
            userid = policy.authenticated_userid(request)
            if userid is not None:
                request.registry.notify(MultiAuthPolicySelected(policy,
                                                                request,
                                                                userid))

                if self._callback is None:
                    break
                if self._callback(userid, request) is not None:
                    break
                else:
                    userid = None
        return userid

    def unauthenticated_userid(self, request):
        """Find the unauthenticated userid for this request.

        This method delegates to each authn policy in turn, taking the
        userid from the first one that doesn't return None.
        """
        userid = None
        for policy in self._policies:
            userid = policy.unauthenticated_userid(request)
            if userid is not None:
                break
        return userid

    def effective_principals(self, request):
        """Get the list of effective principals for this request.

        This method returns the union of the principals returned by each
        authn policy.  If a groupfinder callback is registered, its output
        is also added to the list.
        """
        principals = set((Everyone,))
        for policy in self._policies:
            principals.update(policy.effective_principals(request))
        if self._callback is not None:
            principals.discard(Authenticated)
            groups = None
            for policy in self._policies:
                userid = policy.authenticated_userid(request)
                if userid is None:
                    continue
                request.registry.notify(MultiAuthPolicySelected(policy,
                                                                request,
                                                                userid))
                groups = self._callback(userid, request)
                if groups is not None:
                    break
            if groups is not None:
                principals.add(userid)
                principals.add(Authenticated)
                principals.update(groups)
        return list(principals)

    def remember(self, request, principal, **kw):
        """Remember the authenticated userid.

        This method returns the concatentation of the headers returned by each
        authn policy.
        """
        headers = []
        for policy in self._policies:
            headers.extend(policy.remember(request, principal, **kw))
        return headers

    def forget(self, request):
        """Forget a previusly remembered userid.

        This method returns the concatentation of the headers returned by each
        authn policy.
        """
        headers = []
        for policy in self._policies:
            headers.extend(policy.forget(request))
        return headers

    def get_policies(self):
        """Get the list of contained authentication policies, as tuple of
        name and instances.

        This may be useful to instrospect the configured policies, and their
        respective name defined in configuration.
        """
        return [(getattr(policy, "_pyramid_multiauth_name", None), policy)
                for policy in self._policies]

    def get_policy(self, name_or_class):
        """Get one of the contained authentication policies, by name or class.

        This method can be used to obtain one of the subpolicies loaded
        by this policy object.  The policy can be looked up either by the
        name given to it in the config settings, or or by its class.  If
        no policy is found matching the given query, None is returned.

        This may be useful if you need to access non-standard methods or
        properties on one of the loaded policy objects.
        """
        for policy in self._policies:
            if isinstance(name_or_class, basestring):
                policy_name = getattr(policy, "_pyramid_multiauth_name", None)
                if policy_name == name_or_class:
                    return policy
            else:
                if isinstance(policy, name_or_class):
                    return policy
        return None


def includeme(config):
    """Include pyramid_multiauth into a pyramid configurator.

    This function provides a hook for pyramid to include the default settings
    for auth via pyramid_multiauth.  Activate it like so:

        config.include("pyramid_multiauth")

    This will pull the list of registered authn policies from the deployment
    settings, and configure and install each policy in order.  The policies to
    use can be specified in one of two ways:

        * as the name of a module to be included.
        * as the name of a callable along with a set of parameters.

    Here's an example suite of settings:

        multiauth.policies = ipauth1 ipauth2 pyramid_browserid

        multiauth.policy.ipauth1.use = pyramid_ipauth.IPAuthentictionPolicy
        multiauth.policy.ipauth1.ipaddrs = 123.123.0.0/16
        multiauth.policy.ipauth1.userid = local1

        multiauth.policy.ipauth2.use = pyramid_ipauth.IPAuthentictionPolicy
        multiauth.policy.ipauth2.ipaddrs = 124.124.0.0/16
        multiauth.policy.ipauth2.userid = local2

    This will configure a MultiAuthenticationPolicy with three policy objects.
    The first two will be IPAuthenticationPolicy objects created by passing
    in the specified keyword arguments.  The third will be a BrowserID
    authentication policy just like you would get from executing:

        config.include("pyramid_browserid")

    As a side-effect, the configuration will also get the additional views
    that pyramid_browserid sets up by default.

    The *group finder function* and the *authorization policy* are also read
    from configuration if specified:

        multiauth.authorization_policy = mypyramidapp.acl.Custom
        multiauth.groupfinder  = mypyramidapp.acl.groupfinder
    """
    # Grab the pyramid-wide settings, to look for any auth config.
    settings = config.get_settings()
    # Hook up a default AuthorizationPolicy.
    # Get the authorization policy from config if present.
    # Default ACLAuthorizationPolicy is usually what you want.
    authz_class = settings.get("multiauth.authorization_policy",
                               "pyramid.authorization.ACLAuthorizationPolicy")
    authz_policy = config.maybe_dotted(authz_class)()
    # If the app configures one explicitly then this will get overridden.
    # In autocommit mode this needs to be done before setting the authn policy.
    config.set_authorization_policy(authz_policy)
    # Get the groupfinder from config if present.
    groupfinder = settings.get("multiauth.groupfinder", None)
    groupfinder = config.maybe_dotted(groupfinder)
    # Look for callable policy definitions.
    # Suck them all out at once and store them in a dict for later use.
    policy_definitions = get_policy_definitions(settings)
    # Read and process the list of policies to load.
    # We build up a list of callables which can be executed at config commit
    # time to obtain the final list of policies.
    # Yeah, it's complicated.  But we want to be able to inherit any default
    # views or other config added by the sub-policies when they're included.
    # Process policies in reverse order so that things at the front of the
    # list can override things at the back of the list.
    policy_factories = []
    policy_names = settings.get("multiauth.policies", "").split()
    for policy_name in reversed(policy_names):
        if policy_name in policy_definitions:
            # It's a policy defined using a callable.
            # Just append it straight to the list.
            definition = policy_definitions[policy_name]
            factory = config.maybe_dotted(definition.pop("use"))
            policy_factories.append((factory, policy_name, definition))
        else:
            # It's a module to be directly included.
            try:
                factory = policy_factory_from_module(config, policy_name)
            except ImportError:
                err = "pyramid_multiauth: policy %r has no settings "\
                      "and is not importable" % (policy_name,)
                raise ValueError(err)
            policy_factories.append((factory, policy_name, {}))
    # OK.  We now have a list of callbacks which need to be called at
    # commit time, and will return the policies in reverse order.
    # Register a special action to pull them into our list of policies.
    policies = []

    def grab_policies():
        for factory, name, kwds in policy_factories:
            policy = factory(**kwds)
            if policy:
                policy._pyramid_multiauth_name = name
                if not policies or policy is not policies[0]:
                    # Remember, they're being processed in reverse order.
                    # So each new policy needs to go at the front.
                    policies.insert(0, policy)

    config.action(None, grab_policies, order=PHASE2_CONFIG)
    authn_policy = MultiAuthenticationPolicy(policies, groupfinder)
    config.set_authentication_policy(authn_policy)


def policy_factory_from_module(config, module):
    """Create a policy factory that works by config.include()'ing a module.

    This function does some trickery with the Pyramid config system. Loosely,
    it does config.include(module), and then sucks out information about the
    authn policy that was registered.  It's complicated by pyramid's delayed-
    commit system, which means we have to do the work via callbacks.
    """
    # Remember the policy that's active before including the module, if any.
    orig_policy = config.registry.queryUtility(IAuthenticationPolicy)
    # Include the module, so we get any default views etc.
    config.include(module)
    # That might have registered and commited a new policy object.
    policy = config.registry.queryUtility(IAuthenticationPolicy)
    if policy is not None and policy is not orig_policy:
        return lambda: policy
    # Or it might have set up a pending action to register one later.
    # Find the most recent IAuthenticationPolicy action, and grab
    # out the registering function so we can call it ourselves.
    for action in reversed(config.action_state.actions):
        # Extract the discriminator and callable.  This is complicated by
        # Pyramid 1.3 changing action from a tuple to a dict.
        try:
            discriminator = action["discriminator"]
            callable = action["callable"]
        except TypeError:              # pragma: nocover
            discriminator = action[0]  # pragma: nocover
            callable = action[1]       # pragma: nocover
        # If it's not setting the authn policy, keep looking.
        if discriminator is not IAuthenticationPolicy:
            continue

        # Otherwise, wrap it up so we can extract the registered object.
        def grab_policy(register=callable):
            old_policy = config.registry.queryUtility(IAuthenticationPolicy)
            register()
            new_policy = config.registry.queryUtility(IAuthenticationPolicy)
            config.registry.registerUtility(old_policy, IAuthenticationPolicy)
            return new_policy

        return grab_policy
    # Or it might not have done *anything*.
    # So return a null policy factory.
    return lambda: None


def get_policy_definitions(settings):
    """Find all multiauth policy definitions from the settings dict.

    This function processes the paster deployment settings looking for items
    that start with "multiauth.policy.<policyname>.".  It pulls them all out
    into a dict indexed by the policy name.
    """
    policy_definitions = {}
    for name in settings:
        if not name.startswith("multiauth.policy."):
            continue
        value = settings[name]
        name = name[len("multiauth.policy."):]
        policy_name, setting_name = name.split(".", 1)
        if policy_name not in policy_definitions:
            policy_definitions[policy_name] = {}
        policy_definitions[policy_name][setting_name] = value
    return policy_definitions
