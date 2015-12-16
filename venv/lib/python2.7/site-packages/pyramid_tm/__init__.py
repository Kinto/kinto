import sys
import transaction

from pyramid.settings import asbool
from pyramid.util import DottedNameResolver
from pyramid.tweens import EXCVIEW

from pyramid_tm.compat import reraise
from pyramid_tm.compat import native_

resolver = DottedNameResolver(None)

def default_commit_veto(request, response):
    """
    When used as a commit veto, the logic in this function will cause the
    transaction to be aborted if:

    - An ``X-Tm`` response header with the value ``abort`` (or any value
      other than ``commit``) exists.

    - The response status code starts with ``4`` or ``5``.

    Otherwise the transaction will be allowed to commit.
    """
    xtm = response.headers.get('x-tm')
    if xtm is not None:
        return xtm != 'commit'
    return response.status.startswith(('4', '5'))

class AbortResponse(Exception):
    def __init__(self, response):
        self.response = response

def tm_tween_factory(handler, registry):
    old_commit_veto = registry.settings.get('pyramid_tm.commit_veto', None)
    commit_veto = registry.settings.get('tm.commit_veto', old_commit_veto)
    activate = registry.settings.get('tm.activate_hook')
    attempts = int(registry.settings.get('tm.attempts', 1))
    commit_veto = resolver.maybe_resolve(commit_veto) if commit_veto else None
    activate = resolver.maybe_resolve(activate) if activate else None
    annotate_user = asbool(registry.settings.get("tm.annotate_user", True))
    assert attempts > 0

    def tm_tween(request):
        if 'repoze.tm.active' in request.environ:
            # don't handle txn mgmt if repoze.tm is in the WSGI pipeline
            return handler(request)

        if activate is not None:
            if not activate(request):
                return handler(request)

        manager = getattr(request, 'tm', None)
        if manager is None: # pragma: no cover (pyramid < 1.4)
            manager = create_tm(request)
            request.tm = manager
        number = attempts
        if annotate_user:
            if hasattr(request, 'unauthenticated_userid'):
                userid = request.unauthenticated_userid
            else: # pragma no cover (for pyramid < 1.5)
                from pyramid.security import unauthenticated_userid
                userid = unauthenticated_userid(request)
        else:
            userid = None

        while number:
            number -= 1
            try:
                manager.begin()
                # make_body_seekable will copy wsgi.input if necessary,
                # otherwise it will rewind the copy to position zero
                if attempts != 1:
                    request.make_body_seekable()
                t = manager.get()
                if userid:
                    userid = native_(userid, 'utf-8')
                    t.setUser(userid, '')
                try:
                    t.note(native_(request.path_info, 'utf-8'))
                except UnicodeDecodeError:
                    t.note("Unable to decode path as unicode")
                response = handler(request)
                if manager.isDoomed():
                    raise AbortResponse(response)
                if commit_veto is not None:
                    veto = commit_veto(request, response)
                    if veto:
                        raise AbortResponse(response)
                manager.commit()
                return response
            except AbortResponse as e:
                manager.abort()
                return e.response
            except:
                exc_info = sys.exc_info()
                try:
                    retryable = manager._retryable(*exc_info[:-1])
                    manager.abort()
                    if (number <= 0) or (not retryable):
                        reraise(*exc_info)
                finally:
                    del exc_info # avoid leak

    return tm_tween


def create_tm(request):
    manager_hook = request.registry.settings.get('tm.manager_hook')
    if manager_hook:
        manager_hook = resolver.maybe_resolve(manager_hook)
        return manager_hook(request)
    else:
        return transaction.manager


def includeme(config):
    """
    Set up am implicit 'tween' to do transaction management using the
    ``transaction`` package.  The tween will be slotted between the main
    Pyramid app and the Pyramid exception view handler.

    For every request it handles, the tween will begin a transaction by
    calling ``transaction.begin()``, and will then call the downstream
    handler (usually the main Pyramid application request handler) to obtain
    a response.  When attempting to call the downstream handler:

    - If an exception is raised by downstream handler while attempting to
      obtain a response, the transaction will be rolled back
      (``transaction.abort()`` will be called).

    - If no exception is raised by the downstream handler, but the
      transaction is doomed (``transaction.doom()`` has been called), the
      transaction will be rolled back.

    - If the deployment configuration specifies a ``tm.commit_veto`` setting,
      and the transaction management tween receives a response from the
      downstream handler, the commit veto hook will be called.  If it returns
      True, the transaction will be rolled back.  If it returns False, the
      transaction will be committed.

    - If none of the above conditions are True, the transaction will be
      committed (via ``transaction.commit()``).
    """
    # pyramid 1.4+
    if hasattr(config, 'add_request_method'):
        config.add_request_method(
            'pyramid_tm.create_tm', name='tm', reify=True)
    # pyramid 1.3
    elif hasattr(config, 'set_request_property'): # pragma: no cover
        config.set_request_property(
            'pyramid_tm.create_tm', name='tm', reify=True)
    config.add_tween('pyramid_tm.tm_tween_factory', under=EXCVIEW)

    def ensure():
        manager_hook = config.registry.settings.get("tm.manager_hook")
        if manager_hook is not None:
            manager_hook = resolver.maybe_resolve(manager_hook)
            config.registry.settings["tm.manager_hook"] = manager_hook

    config.action(None, ensure, order=10)
