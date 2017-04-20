import sys

from pyramid.compat import reraise
from pyramid.exceptions import PredicateMismatch
from pyramid.interfaces import (
    IExceptionViewClassifier,
    IRequest,
    )

from zope.interface import providedBy
from pyramid.view import _call_view

def excview_tween_factory(handler, registry):
    """ A :term:`tween` factory which produces a tween that catches an
    exception raised by downstream tweens (or the main Pyramid request
    handler) and, if possible, converts it into a Response using an
    :term:`exception view`."""

    def excview_tween(request):
        attrs = request.__dict__
        try:
            response = handler(request)
        except Exception as exc:
            # WARNING: do not assign the result of sys.exc_info() to a local
            # var here, doing so will cause a leak.  We used to actually
            # explicitly delete both "exception" and "exc_info" from ``attrs``
            # in a ``finally:`` clause below, but now we do not because these
            # attributes are useful to upstream tweens.  This actually still
            # apparently causes a reference cycle, but it is broken
            # successfully by the garbage collector (see
            # https://github.com/Pylons/pyramid/issues/1223).
            attrs['exc_info'] = sys.exc_info()
            attrs['exception'] = exc
            # clear old generated request.response, if any; it may
            # have been mutated by the view, and its state is not
            # sane (e.g. caching headers)
            if 'response' in attrs:
                del attrs['response']
            # we use .get instead of .__getitem__ below due to
            # https://github.com/Pylons/pyramid/issues/700
            request_iface = attrs.get('request_iface', IRequest)
            provides = providedBy(exc)
            try:
                response = _call_view(
                    registry,
                    request,
                    exc,
                    provides,
                    '',
                    view_classifier=IExceptionViewClassifier,
                    request_iface=request_iface.combined
                    )

            # if views matched but did not pass predicates, squash the error
            # and re-raise the original exception
            except PredicateMismatch:
                response = None

            # re-raise the original exception as no exception views were
            # able to handle the error
            if response is None:
                reraise(*attrs['exc_info'])

        return response

    return excview_tween

MAIN = 'MAIN'
INGRESS = 'INGRESS'
EXCVIEW = 'pyramid.tweens.excview_tween_factory'
