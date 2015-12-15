import unittest

from pyramid.compat import bytes_

class TestTemplate(unittest.TestCase):
    def _makeOne(self, name='whatever'):
        from pyramid.scaffolds.template import Template
        return Template(name)

    def test_render_template_success(self):
        inst = self._makeOne()
        result = inst.render_template('{{a}} {{b}}', {'a':'1', 'b':'2'})
        self.assertEqual(result, bytes_('1 2'))

    def test_render_template_expr_failure(self):
        inst = self._makeOne()
        self.assertRaises(AttributeError, inst.render_template,
                          '{{a.foo}}', {'a':'1', 'b':'2'})

    def test_render_template_expr_success(self):
        inst = self._makeOne()
        result = inst.render_template('{{a.lower()}}', {'a':'A'})
        self.assertEqual(result, b'a')

    def test_render_template_expr_success_via_pipe(self):
        inst = self._makeOne()
        result = inst.render_template('{{b|c|a.lower()}}', {'a':'A'})
        self.assertEqual(result, b'a')

    def test_render_template_expr_success_via_pipe2(self):
        inst = self._makeOne()
        result = inst.render_template('{{b|a.lower()|c}}', {'a':'A'})
        self.assertEqual(result, b'a')

    def test_render_template_expr_value_is_None(self):
        inst = self._makeOne()
        result = inst.render_template('{{a}}', {'a':None})
        self.assertEqual(result, b'')

    def test_render_template_with_escaped_double_braces(self):
        inst = self._makeOne()
        result = inst.render_template('{{a}} {{b}} \{\{a\}\} \{\{c\}\}', {'a':'1', 'b':'2'})
        self.assertEqual(result, bytes_('1 2 {{a}} {{c}}'))

    def test_render_template_with_breaking_escaped_braces(self):
        inst = self._makeOne()
        result = inst.render_template('{{a}} {{b}} \{\{a\} \{b\}\}', {'a':'1', 'b':'2'})
        self.assertEqual(result, bytes_('1 2 \{\{a\} \{b\}\}'))

    def test_render_template_with_escaped_single_braces(self):
        inst = self._makeOne()
        result = inst.render_template('{{a}} {{b}} \{a\} \{b', {'a':'1', 'b':'2'})
        self.assertEqual(result, bytes_('1 2 \{a\} \{b'))

    def test_module_dir(self):
        import sys
        import pkg_resources
        package = sys.modules['pyramid.scaffolds.template']
        path = pkg_resources.resource_filename(package.__name__, '')
        inst = self._makeOne()
        result = inst.module_dir()
        self.assertEqual(result, path)

    def test_template_dir__template_dir_is_None(self):
        inst = self._makeOne()
        self.assertRaises(AssertionError, inst.template_dir)

    def test_template_dir__template_dir_is_tuple(self):
        inst = self._makeOne()
        inst._template_dir = ('a', 'b')
        self.assertEqual(inst.template_dir(), ('a', 'b'))

    def test_template_dir__template_dir_is_not_None(self):
        import os
        import sys
        import pkg_resources
        package = sys.modules['pyramid.scaffolds.template']
        path = pkg_resources.resource_filename(package.__name__, '')
        inst = self._makeOne()
        inst._template_dir ='foo'
        result = inst.template_dir()
        self.assertEqual(result, os.path.join(path, 'foo'))

    def test_write_files_path_exists(self):
        import os
        import sys
        import pkg_resources
        package = sys.modules['pyramid.scaffolds.template']
        path = pkg_resources.resource_filename(package.__name__, '')
        inst = self._makeOne()
        inst._template_dir = 'foo'
        inst.exists = lambda *arg: True
        copydir = DummyCopydir()
        inst.copydir = copydir
        command = DummyCommand()
        inst.write_files(command, 'output dir', {'a':1})
        self.assertEqual(copydir.template_dir, os.path.join(path, 'foo'))
        self.assertEqual(copydir.output_dir, 'output dir')
        self.assertEqual(copydir.vars, {'a':1})
        self.assertEqual(copydir.kw,
                         {'template_renderer':inst.render_template,
                          'indent':1,
                          'verbosity':1,
                          'simulate':False,
                          'overwrite':False,
                          'interactive':False,
                          })

    def test_write_files_path_missing(self):
        L = []
        inst = self._makeOne()
        inst._template_dir = 'foo'
        inst.exists = lambda *arg: False
        inst.out = lambda *arg: None
        inst.makedirs = lambda dir: L.append(dir)
        copydir = DummyCopydir()
        inst.copydir = copydir
        command = DummyCommand()
        inst.write_files(command, 'output dir', {'a':1})
        self.assertEqual(L, ['output dir'])

    def test_run(self):
        L = []
        inst = self._makeOne()
        inst._template_dir = 'foo'
        inst.exists = lambda *arg: False
        inst.out = lambda *arg: None
        inst.makedirs = lambda dir: L.append(dir)
        copydir = DummyCopydir()
        inst.copydir = copydir
        command = DummyCommand()
        inst.run(command, 'output dir', {'a':1})
        self.assertEqual(L, ['output dir'])

    def test_check_vars(self):
        inst = self._makeOne()
        self.assertRaises(RuntimeError, inst.check_vars, 'one', 'two')

class DummyCopydir(object):
    def copy_dir(self, template_dir, output_dir, vars, **kw):
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.vars = vars
        self.kw = kw

class DummyOptions(object):
    simulate = False
    overwrite = False
    interactive = False

class DummyCommand(object):
    options = DummyOptions()
    verbosity = 1


