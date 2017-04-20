import unittest

from pyramid.tests.test_config import dummy_tween_factory
from pyramid.tests.test_config import dummy_tween_factory2

from pyramid.exceptions import ConfigurationConflictError

class TestTweensConfiguratorMixin(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_add_tweens_names_distinct(self):
        from pyramid.interfaces import ITweens
        from pyramid.tweens import excview_tween_factory
        def factory1(handler, registry): return handler
        def factory2(handler, registry): return handler
        config = self._makeOne()
        config.add_tween(
            'pyramid.tests.test_config.dummy_tween_factory')
        config.add_tween(
            'pyramid.tests.test_config.dummy_tween_factory2')
        config.commit()
        tweens = config.registry.queryUtility(ITweens)
        implicit = tweens.implicit()
        self.assertEqual(
            implicit,
            [
                ('pyramid.tests.test_config.dummy_tween_factory2',
                 dummy_tween_factory2),
                ('pyramid.tests.test_config.dummy_tween_factory',
                 dummy_tween_factory),
                ('pyramid.tweens.excview_tween_factory',
                 excview_tween_factory),
                ]
            )

    def test_add_tweens_names_with_underover(self):
        from pyramid.interfaces import ITweens
        from pyramid.tweens import excview_tween_factory
        from pyramid.tweens import MAIN
        config = self._makeOne()
        config.add_tween(
            'pyramid.tests.test_config.dummy_tween_factory',
            over=MAIN)
        config.add_tween(
            'pyramid.tests.test_config.dummy_tween_factory2',
            over=MAIN,
            under='pyramid.tests.test_config.dummy_tween_factory')
        config.commit()
        tweens = config.registry.queryUtility(ITweens)
        implicit = tweens.implicit()
        self.assertEqual(
            implicit,
            [
                ('pyramid.tweens.excview_tween_factory', excview_tween_factory),
                ('pyramid.tests.test_config.dummy_tween_factory',
                 dummy_tween_factory),
                ('pyramid.tests.test_config.dummy_tween_factory2',
                 dummy_tween_factory2),
             ])

    def test_add_tweens_names_with_under_nonstringoriter(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        self.assertRaises(
            ConfigurationError, config.add_tween,
            'pyramid.tests.test_config.dummy_tween_factory',
            under=False)

    def test_add_tweens_names_with_over_nonstringoriter(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        self.assertRaises(
            ConfigurationError, config.add_tween,
            'pyramid.tests.test_config.dummy_tween_factory',
            over=False)

    def test_add_tween_dottedname(self):
        from pyramid.interfaces import ITweens
        from pyramid.tweens import excview_tween_factory
        config = self._makeOne()
        config.add_tween('pyramid.tests.test_config.dummy_tween_factory')
        config.commit()
        tweens = config.registry.queryUtility(ITweens)
        self.assertEqual(
            tweens.implicit(),
            [
                ('pyramid.tests.test_config.dummy_tween_factory',
                 dummy_tween_factory),
                ('pyramid.tweens.excview_tween_factory',
                 excview_tween_factory),
                ])

    def test_add_tween_instance(self):
        from pyramid.exceptions import ConfigurationError
        class ATween(object): pass
        atween = ATween()
        config = self._makeOne()
        self.assertRaises(ConfigurationError, config.add_tween, atween)

    def test_add_tween_unsuitable(self):
        from pyramid.exceptions import ConfigurationError
        import pyramid.tests.test_config
        config = self._makeOne()
        self.assertRaises(ConfigurationError, config.add_tween,
                          pyramid.tests.test_config)

    def test_add_tween_name_ingress(self):
        from pyramid.exceptions import ConfigurationError
        from pyramid.tweens import INGRESS
        config = self._makeOne()
        self.assertRaises(ConfigurationError, config.add_tween, INGRESS)

    def test_add_tween_name_main(self):
        from pyramid.exceptions import ConfigurationError
        from pyramid.tweens import MAIN
        config = self._makeOne()
        self.assertRaises(ConfigurationError, config.add_tween, MAIN)

    def test_add_tweens_conflict(self):
        config = self._makeOne()
        config.add_tween('pyramid.tests.test_config.dummy_tween_factory')
        config.add_tween('pyramid.tests.test_config.dummy_tween_factory')
        self.assertRaises(ConfigurationConflictError, config.commit)

    def test_add_tween_over_ingress(self):
        from pyramid.exceptions import ConfigurationError
        from pyramid.tweens import INGRESS
        config = self._makeOne()
        self.assertRaises(
            ConfigurationError,
            config.add_tween,
            'pyramid.tests.test_config.dummy_tween_factory',
            over=INGRESS)

    def test_add_tween_over_ingress_iterable(self):
        from pyramid.exceptions import ConfigurationError
        from pyramid.tweens import INGRESS
        config = self._makeOne()
        self.assertRaises(
            ConfigurationError,
            config.add_tween,
            'pyramid.tests.test_config.dummy_tween_factory',
            over=('a', INGRESS))

    def test_add_tween_under_main(self):
        from pyramid.exceptions import ConfigurationError
        from pyramid.tweens import MAIN
        config = self._makeOne()
        self.assertRaises(
            ConfigurationError,
            config.add_tween,
            'pyramid.tests.test_config.dummy_tween_factory',
            under=MAIN)

    def test_add_tween_under_main_iterable(self):
        from pyramid.exceptions import ConfigurationError
        from pyramid.tweens import MAIN
        config = self._makeOne()
        self.assertRaises(
            ConfigurationError,
            config.add_tween,
            'pyramid.tests.test_config.dummy_tween_factory',
            under=('a', MAIN))

class TestTweens(unittest.TestCase):
    def _makeOne(self):
        from pyramid.config.tweens import Tweens
        return Tweens()

    def test_add_explicit(self):
        tweens = self._makeOne()
        tweens.add_explicit('name', 'factory')
        self.assertEqual(tweens.explicit, [('name',  'factory')])
        tweens.add_explicit('name2', 'factory2')
        self.assertEqual(tweens.explicit, [('name',  'factory'),
                                           ('name2', 'factory2')])

    def test_add_implicit(self):
        tweens = self._makeOne()
        tweens.add_implicit('name', 'factory')
        tweens.add_implicit('name2', 'factory2')
        self.assertEqual(tweens.sorter.sorted(),
                         [('name2',  'factory2'),
                          ('name', 'factory')])

    def test___call___explicit(self):
        tweens = self._makeOne()
        def factory1(handler, registry):
            return handler
        def factory2(handler, registry):
            return '123'
        tweens.explicit = [('name', factory1), ('name', factory2)]
        self.assertEqual(tweens(None, None), '123')

    def test___call___implicit(self):
        tweens = self._makeOne()
        def factory1(handler, registry):
            return handler
        def factory2(handler, registry):
            return '123'
        tweens.add_implicit('name2', factory2)
        tweens.add_implicit('name1', factory1)
        self.assertEqual(tweens(None, None), '123')

    def test_implicit_ordering_1(self):
        tweens = self._makeOne()
        tweens.add_implicit('name1', 'factory1')
        tweens.add_implicit('name2', 'factory2')
        self.assertEqual(tweens.implicit(),
                         [
                             ('name2', 'factory2'),
                             ('name1', 'factory1'),
                             ])

    def test_implicit_ordering_2(self):
        from pyramid.tweens import MAIN
        tweens = self._makeOne()
        tweens.add_implicit('name1', 'factory1')
        tweens.add_implicit('name2', 'factory2', over=MAIN)
        self.assertEqual(tweens.implicit(),
                         [
                             ('name1', 'factory1'),
                             ('name2', 'factory2'),
                             ])

    def test_implicit_ordering_3(self):
        from pyramid.tweens import MAIN
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('auth', 'auth_factory', under='browserid')
        add('dbt', 'dbt_factory') 
        add('retry', 'retry_factory', over='txnmgr', under='exceptionview')
        add('browserid', 'browserid_factory')
        add('txnmgr', 'txnmgr_factory', under='exceptionview')
        add('exceptionview', 'excview_factory', over=MAIN)
        self.assertEqual(tweens.implicit(),
                         [
                             ('browserid', 'browserid_factory'),
                             ('auth', 'auth_factory'),
                             ('dbt', 'dbt_factory'),
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ('txnmgr', 'txnmgr_factory'),
                             ])

    def test_implicit_ordering_4(self):
        from pyramid.tweens import MAIN
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('exceptionview', 'excview_factory', over=MAIN)
        add('auth', 'auth_factory', under='browserid')
        add('retry', 'retry_factory', over='txnmgr', under='exceptionview')
        add('browserid', 'browserid_factory')
        add('txnmgr', 'txnmgr_factory', under='exceptionview')
        add('dbt', 'dbt_factory') 
        self.assertEqual(tweens.implicit(),
                         [
                             ('dbt', 'dbt_factory'),
                             ('browserid', 'browserid_factory'),
                             ('auth', 'auth_factory'),
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ('txnmgr', 'txnmgr_factory'),
                             ])

    def test_implicit_ordering_5(self):
        from pyramid.tweens import MAIN, INGRESS
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('exceptionview', 'excview_factory', over=MAIN)
        add('auth', 'auth_factory', under=INGRESS)
        add('retry', 'retry_factory', over='txnmgr', under='exceptionview')
        add('browserid', 'browserid_factory', under=INGRESS)
        add('txnmgr', 'txnmgr_factory', under='exceptionview', over=MAIN)
        add('dbt', 'dbt_factory') 
        self.assertEqual(tweens.implicit(),
                         [
                             ('dbt', 'dbt_factory'),
                             ('browserid', 'browserid_factory'),
                             ('auth', 'auth_factory'),
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ('txnmgr', 'txnmgr_factory'),
                             ])

    def test_implicit_ordering_missing_over_partial(self):
        from pyramid.exceptions import ConfigurationError
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('dbt', 'dbt_factory')
        add('auth', 'auth_factory', under='browserid')
        add('retry', 'retry_factory', over='txnmgr', under='exceptionview')
        add('browserid', 'browserid_factory')
        self.assertRaises(ConfigurationError, tweens.implicit)

    def test_implicit_ordering_missing_under_partial(self):
        from pyramid.exceptions import ConfigurationError
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('dbt', 'dbt_factory')
        add('auth', 'auth_factory', under='txnmgr')
        add('retry', 'retry_factory', over='dbt', under='exceptionview')
        add('browserid', 'browserid_factory')
        self.assertRaises(ConfigurationError, tweens.implicit)

    def test_implicit_ordering_missing_over_and_under_partials(self):
        from pyramid.exceptions import ConfigurationError
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('dbt', 'dbt_factory')
        add('auth', 'auth_factory', under='browserid')
        add('retry', 'retry_factory', over='foo', under='txnmgr')
        add('browserid', 'browserid_factory')
        self.assertRaises(ConfigurationError, tweens.implicit)

    def test_implicit_ordering_missing_over_partial_with_fallback(self):
        from pyramid.tweens import MAIN
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('exceptionview', 'excview_factory', over=MAIN)
        add('auth', 'auth_factory', under='browserid')
        add('retry', 'retry_factory', over=('txnmgr',MAIN),
                                      under='exceptionview')
        add('browserid', 'browserid_factory')
        add('dbt', 'dbt_factory') 
        self.assertEqual(tweens.implicit(),
                         [
                             ('dbt', 'dbt_factory'),
                             ('browserid', 'browserid_factory'),
                             ('auth', 'auth_factory'),
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ])

    def test_implicit_ordering_missing_under_partial_with_fallback(self):
        from pyramid.tweens import MAIN
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('exceptionview', 'excview_factory', over=MAIN)
        add('auth', 'auth_factory', under=('txnmgr','browserid'))
        add('retry', 'retry_factory', under='exceptionview')
        add('browserid', 'browserid_factory')
        add('dbt', 'dbt_factory')
        self.assertEqual(tweens.implicit(),
                         [
                             ('dbt', 'dbt_factory'),
                             ('browserid', 'browserid_factory'),
                             ('auth', 'auth_factory'),
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ])

    def test_implicit_ordering_with_partial_fallbacks(self):
        from pyramid.tweens import MAIN
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('exceptionview', 'excview_factory', over=('wontbethere', MAIN))
        add('retry', 'retry_factory', under='exceptionview')
        add('browserid', 'browserid_factory', over=('wont2', 'exceptionview'))
        self.assertEqual(tweens.implicit(),
                         [
                             ('browserid', 'browserid_factory'),
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ])

    def test_implicit_ordering_with_multiple_matching_fallbacks(self):
        from pyramid.tweens import MAIN
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('exceptionview', 'excview_factory', over=MAIN)
        add('retry', 'retry_factory', under='exceptionview')
        add('browserid', 'browserid_factory', over=('retry', 'exceptionview'))
        self.assertEqual(tweens.implicit(),
                         [
                             ('browserid', 'browserid_factory'),
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ])

    def test_implicit_ordering_with_missing_fallbacks(self):
        from pyramid.exceptions import ConfigurationError
        from pyramid.tweens import MAIN
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('exceptionview', 'excview_factory', over=MAIN)
        add('retry', 'retry_factory', under='exceptionview')
        add('browserid', 'browserid_factory', over=('txnmgr', 'auth'))
        self.assertRaises(ConfigurationError, tweens.implicit)

    def test_implicit_ordering_conflict_direct(self):
        from pyramid.exceptions import CyclicDependencyError
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('browserid', 'browserid_factory')
        add('auth', 'auth_factory', over='browserid', under='browserid')
        self.assertRaises(CyclicDependencyError, tweens.implicit)

    def test_implicit_ordering_conflict_indirect(self):
        from pyramid.exceptions import CyclicDependencyError
        tweens = self._makeOne()
        add = tweens.add_implicit
        add('browserid', 'browserid_factory')
        add('auth', 'auth_factory', over='browserid')
        add('dbt', 'dbt_factory', under='browserid', over='auth')
        self.assertRaises(CyclicDependencyError, tweens.implicit)

