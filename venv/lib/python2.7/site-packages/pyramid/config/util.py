from hashlib import md5
import inspect

from pyramid.compat import (
    bytes_,
    is_nonstr_iter,
    )

from pyramid.compat import im_func
from pyramid.exceptions import ConfigurationError
from pyramid.registry import predvalseq

from pyramid.util import (
    TopologicalSorter,
    action_method,
    ActionInfo,
    )

action_method = action_method # support bw compat imports
ActionInfo = ActionInfo # support bw compat imports

MAX_ORDER = 1 << 30
DEFAULT_PHASH = md5().hexdigest()

def as_sorted_tuple(val):
    if not is_nonstr_iter(val):
        val = (val,)
    val = tuple(sorted(val))
    return val

class not_(object):
    """

    You can invert the meaning of any predicate value by wrapping it in a call
    to :class:`pyramid.config.not_`.

    .. code-block:: python
       :linenos:

       from pyramid.config import not_

       config.add_view(
           'mypackage.views.my_view',
           route_name='ok', 
           request_method=not_('POST')
           )

    The above example will ensure that the view is called if the request method
    is *not* ``POST``, at least if no other view is more specific.

    This technique of wrapping a predicate value in ``not_`` can be used
    anywhere predicate values are accepted:

    - :meth:`pyramid.config.Configurator.add_view`

    - :meth:`pyramid.config.Configurator.add_route`

    - :meth:`pyramid.config.Configurator.add_subscriber`

    - :meth:`pyramid.view.view_config`

    - :meth:`pyramid.events.subscriber`

    .. versionadded:: 1.5
    """
    def __init__(self, value):
        self.value = value

class Notted(object):
    def __init__(self, predicate):
        self.predicate = predicate

    def _notted_text(self, val):
        # if the underlying predicate doesnt return a value, it's not really
        # a predicate, it's just something pretending to be a predicate,
        # so dont update the hash
        if val: 
            val = '!' + val
        return val

    def text(self):
        return self._notted_text(self.predicate.text())

    def phash(self):
        return self._notted_text(self.predicate.phash())

    def __call__(self, context, request):
        result = self.predicate(context, request)
        phash = self.phash()
        if phash:
            result = not result
        return result

# under = after
# over = before

class PredicateList(object):
    
    def __init__(self):
        self.sorter = TopologicalSorter()
        self.last_added = None

    def add(self, name, factory, weighs_more_than=None, weighs_less_than=None):
        # Predicates should be added to a predicate list in (presumed)
        # computation expense order.
        ## if weighs_more_than is None and weighs_less_than is None:
        ##     weighs_more_than = self.last_added or FIRST
        ##     weighs_less_than = LAST
        self.last_added = name
        self.sorter.add(
            name,
            factory,
            after=weighs_more_than,
            before=weighs_less_than,
            )

    def make(self, config, **kw):
        # Given a configurator and a list of keywords, a predicate list is
        # computed.  Elsewhere in the code, we evaluate predicates using a
        # generator expression.  All predicates associated with a view or
        # route must evaluate true for the view or route to "match" during a
        # request.  The fastest predicate should be evaluated first, then the
        # next fastest, and so on, as if one returns false, the remainder of
        # the predicates won't need to be evaluated.
        #
        # While we compute predicates, we also compute a predicate hash (aka
        # phash) that can be used by a caller to identify identical predicate
        # lists.
        ordered = self.sorter.sorted()
        phash = md5()
        weights = []
        preds = []
        for n, (name, predicate_factory) in enumerate(ordered):
            vals = kw.pop(name, None)
            if vals is None: # XXX should this be a sentinel other than None?
                continue
            if not isinstance(vals, predvalseq):
                vals = (vals,)
            for val in vals:
                realval = val
                notted = False
                if isinstance(val, not_):
                    realval = val.value
                    notted = True
                pred = predicate_factory(realval, config)
                if notted:
                    pred = Notted(pred)
                hashes = pred.phash()
                if not is_nonstr_iter(hashes):
                    hashes = [hashes]
                for h in hashes:
                    phash.update(bytes_(h))
                weights.append(1 << n+1)
                preds.append(pred)
        if kw:
            raise ConfigurationError('Unknown predicate values: %r' % (kw,))
        # A "order" is computed for the predicate list.  An order is
        # a scoring.
        #
        # Each predicate is associated with a weight value.  The weight of a
        # predicate symbolizes the relative potential "importance" of the
        # predicate to all other predicates.  A larger weight indicates
        # greater importance.
        #
        # All weights for a given predicate list are bitwise ORed together
        # to create a "score"; this score is then subtracted from
        # MAX_ORDER and divided by an integer representing the number of
        # predicates+1 to determine the order.
        #
        # For views, the order represents the ordering in which a "multiview"
        # ( a collection of views that share the same context/request/name
        # triad but differ in other ways via predicates) will attempt to call
        # its set of views.  Views with lower orders will be tried first.
        # The intent is to a) ensure that views with more predicates are
        # always evaluated before views with fewer predicates and b) to
        # ensure a stable call ordering of views that share the same number
        # of predicates.  Views which do not have any predicates get an order
        # of MAX_ORDER, meaning that they will be tried very last.
        score = 0
        for bit in weights:
            score = score | bit
        order = (MAX_ORDER - score) / (len(preds) + 1)
        return order, preds, phash.hexdigest()

def takes_one_arg(callee, attr=None, argname=None):
    ismethod = False
    if attr is None:
        attr = '__call__'
    if inspect.isroutine(callee):
        fn = callee
    elif inspect.isclass(callee):
        try:
            fn = callee.__init__
        except AttributeError:
            return False
        ismethod = hasattr(fn, '__call__')
    else:
        try:
            fn = getattr(callee, attr)
        except AttributeError:
            return False

    try:
        argspec = inspect.getargspec(fn)
    except TypeError:
        return False

    args = argspec[0]

    if hasattr(fn, im_func) or ismethod:
        # it's an instance method (or unbound method on py2)
        if not args:
            return False
        args = args[1:]

    if not args:
        return False

    if len(args) == 1:
        return True

    if argname:

        defaults = argspec[3]
        if defaults is None:
            defaults = ()

        if args[0] == argname:
            if len(args) - len(defaults) == 1:
                return True

    return False
