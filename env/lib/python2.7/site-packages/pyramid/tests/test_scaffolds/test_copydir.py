# -*- coding: utf-8 -*-
import unittest
import os
import pkg_resources

class Test_copy_dir(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pyramid.compat import NativeIO
        self.dirname = tempfile.mkdtemp()
        self.out = NativeIO()
        self.fixturetuple = ('pyramid.tests.test_scaffolds',
                             'fixture_scaffold')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dirname, ignore_errors=True)
        self.out.close()

    def _callFUT(self, *arg, **kw):
        kw['out_'] = self.out
        from pyramid.scaffolds.copydir import copy_dir
        return copy_dir(*arg, **kw)

    def test_copy_source_as_pkg_resource(self):
        vars = {'package':'mypackage'}
        self._callFUT(self.fixturetuple,
                      self.dirname,
                      vars,
                      1, False,
                      template_renderer=dummy_template_renderer)
        result = self.out.getvalue()
        self.assertTrue('Creating' in result)
        self.assertTrue(
            'Copying fixture_scaffold/+package+/__init__.py_tmpl to' in result)
        source = pkg_resources.resource_filename(
            'pyramid.tests.test_scaffolds',
            'fixture_scaffold/+package+/__init__.py_tmpl')
        target = os.path.join(self.dirname, 'mypackage', '__init__.py')
        with open(target, 'r') as f:
            tcontent = f.read()
        with open(source, 'r') as f:
            scontent = f.read()
        self.assertEqual(scontent, tcontent)

    def test_copy_source_as_dirname(self):
        vars = {'package':'mypackage'}
        source = pkg_resources.resource_filename(*self.fixturetuple)
        self._callFUT(source,
                      self.dirname,
                      vars,
                      1, False,
                      template_renderer=dummy_template_renderer)
        result = self.out.getvalue()
        self.assertTrue('Creating' in result)
        self.assertTrue('Copying __init__.py_tmpl to' in result)
        source = pkg_resources.resource_filename(
            'pyramid.tests.test_scaffolds',
            'fixture_scaffold/+package+/__init__.py_tmpl')
        target = os.path.join(self.dirname, 'mypackage', '__init__.py')
        with open(target, 'r') as f:
            tcontent = f.read()
        with open(source, 'r') as f:
            scontent = f.read()
        self.assertEqual(scontent, tcontent)

    def test_content_is_same_message(self):
        vars = {'package':'mypackage'}
        source = pkg_resources.resource_filename(*self.fixturetuple)
        self._callFUT(source,
                      self.dirname,
                      vars,
                      2, False,
                      template_renderer=dummy_template_renderer)
        self._callFUT(source,
                      self.dirname,
                      vars,
                      2, False,
                      template_renderer=dummy_template_renderer)
        result = self.out.getvalue()
        self.assertTrue('%s already exists (same content)' % \
            os.path.join(self.dirname, 'mypackage', '__init__.py') in result)

    def test_direxists_message(self):
        vars = {'package':'mypackage'}
        source = pkg_resources.resource_filename(*self.fixturetuple)
        # if not os.path.exists(self.dirname):
        #     os.mkdir(self.dirname)
        self._callFUT(source,
                      self.dirname,
                      vars,
                      2, False,
                      template_renderer=dummy_template_renderer)
        result = self.out.getvalue()
        self.assertTrue('Directory %s exists' % self.dirname in result, result)

    def test_overwrite_false(self):
        vars = {'package':'mypackage'}
        source = pkg_resources.resource_filename(*self.fixturetuple)
        self._callFUT(source,
                      self.dirname,
                      vars,
                      1, False,
                      overwrite=False,
                      template_renderer=dummy_template_renderer)
        # toplevel file
        toplevel = os.path.join(self.dirname, 'mypackage', '__init__.py')
        with open(toplevel, 'w') as f:
            f.write('These are the words you are looking for.')
        # sub directory file
        sub = os.path.join(self.dirname, 'mypackage', 'templates', 'mytemplate.pt')
        with open(sub, 'w') as f:
            f.write('These are the words you are looking for.')
        self._callFUT(source,
                      self.dirname,
                      vars,
                      1, False,
                      overwrite=False,
                      template_renderer=dummy_template_renderer)
        with open(toplevel, 'r') as f:
            tcontent = f.read()
        self.assertEqual('These are the words you are looking for.', tcontent)
        with open(sub, 'r') as f:
            tcontent = f.read()
        self.assertEqual('These are the words you are looking for.', tcontent)

    def test_overwrite_true(self):
        vars = {'package':'mypackage'}
        source = pkg_resources.resource_filename(*self.fixturetuple)
        self._callFUT(source,
                      self.dirname,
                      vars,
                      1, False,
                      overwrite=True,
                      template_renderer=dummy_template_renderer)
        # toplevel file
        toplevel = os.path.join(self.dirname, 'mypackage', '__init__.py')
        with open(toplevel, 'w') as f:
            f.write('These are not the words you are looking for.')
        # sub directory file
        sub = os.path.join(self.dirname, 'mypackage', 'templates', 'mytemplate.pt')
        with open(sub, 'w') as f:
            f.write('These are not the words you are looking for.')
        self._callFUT(source,
                      self.dirname,
                      vars,
                      1, False,
                      overwrite=True,
                      template_renderer=dummy_template_renderer)
        with open(toplevel, 'r') as f:
            tcontent = f.read()
        self.assertNotEqual('These are not the words you are looking for.', tcontent)
        with open(sub, 'r') as f:
            tcontent = f.read()
        self.assertNotEqual('These are not the words you are looking for.', tcontent)
    
    def test_detect_SkipTemplate(self):
        vars = {'package':'mypackage'}
        source = pkg_resources.resource_filename(*self.fixturetuple)
        def dummy_template_renderer(*args, **kwargs):
            from pyramid.scaffolds.copydir import SkipTemplate
            raise SkipTemplate
        self._callFUT(source,
                      self.dirname,
                      vars,
                      1, False,
                      template_renderer=dummy_template_renderer)

    def test_query_interactive(self):
        from pyramid.scaffolds import copydir
        vars = {'package':'mypackage'}
        source = pkg_resources.resource_filename(*self.fixturetuple)
        self._callFUT(source,
                      self.dirname,
                      vars,
                      1, False,
                      overwrite=False,
                      template_renderer=dummy_template_renderer)
        target = os.path.join(self.dirname, 'mypackage', '__init__.py')
        with open(target, 'w') as f:
            f.write('These are not the words you are looking for.')
        # We need query_interactive to return False in order to force
        # execution of a branch
        original_code_object = copydir.query_interactive
        copydir.query_interactive = lambda *args, **kwargs: False
        self._callFUT(source,
                      self.dirname,
                      vars,
                      1, False,
                      interactive=True,
                      overwrite=False,
                      template_renderer=dummy_template_renderer)
        copydir.query_interactive = original_code_object

class Test_raise_SkipTemplate(unittest.TestCase):

    def _callFUT(self, *arg, **kw):
        from pyramid.scaffolds.copydir import skip_template
        return skip_template(*arg, **kw)

    def test_raise_SkipTemplate(self):
        from pyramid.scaffolds.copydir import SkipTemplate
        self.assertRaises(SkipTemplate, 
            self._callFUT, True, "exc-message")

class Test_makedirs(unittest.TestCase):

    def _callFUT(self, *arg, **kw):
        from pyramid.scaffolds.copydir import makedirs
        return makedirs(*arg, **kw)

    def test_makedirs_parent_dir(self):
        import shutil
        import tempfile
        tmpdir = tempfile.mkdtemp()
        target = os.path.join(tmpdir, 'nonexistent_subdir')
        self._callFUT(target, 2, None)
        shutil.rmtree(tmpdir)

    def test_makedirs_no_parent_dir(self):
        import shutil
        import tempfile
        tmpdir = tempfile.mkdtemp()
        target = os.path.join(tmpdir, 'nonexistent_subdir', 'non2')
        self._callFUT(target, 2, None)
        shutil.rmtree(tmpdir)

class Test_support_functions(unittest.TestCase):

    def _call_html_quote(self, *arg, **kw):
        from pyramid.scaffolds.copydir import html_quote
        return html_quote(*arg, **kw)

    def _call_url_quote(self, *arg, **kw):
        from pyramid.scaffolds.copydir import url_quote
        return url_quote(*arg, **kw)

    def _call_test(self, *arg, **kw):
        from pyramid.scaffolds.copydir import test
        return test(*arg, **kw)

    def test_html_quote(self):
        import string
        s = None
        self.assertEqual(self._call_html_quote(s), '')
        s = string.ascii_letters
        self.assertEqual(self._call_html_quote(s), s)
        s = "Λεμεσός"
        self.assertEqual(self._call_url_quote(s), 
            "%CE%9B%CE%B5%CE%BC%CE%B5%CF%83%CF%8C%CF%82")

    def test_url_quote(self):
        import string
        s = None
        self.assertEqual(self._call_url_quote(s), '')
        s = string.ascii_letters
        self.assertEqual(self._call_url_quote(s), s)
        s = "Λεμεσός"
        self.assertEqual(self._call_url_quote(s), 
            "%CE%9B%CE%B5%CE%BC%CE%B5%CF%83%CF%8C%CF%82")

    def test_test(self):
        conf = True
        true_cond = "faked"
        self.assertEqual(self._call_test(
                conf, true_cond, false_cond=None), "faked")
        conf = False
        self.assertEqual(self._call_test(
                conf, true_cond, false_cond="alsofaked"), "alsofaked")


class Test_should_skip_file(unittest.TestCase):

    def _callFUT(self, *arg, **kw):
        from pyramid.scaffolds.copydir import should_skip_file
        return should_skip_file(*arg, **kw)

    def test_should_skip_dot_hidden_file(self):
        self.assertEqual(
            self._callFUT('.a_filename'), 
            'Skipping hidden file %(filename)s')

    def test_should_skip_backup_file(self):
        for name in ('a_filename~', 'a_filename.bak'):
            self.assertEqual(
                self._callFUT(name),
                'Skipping backup file %(filename)s')

    def test_should_skip_bytecompiled_file(self):
        for name in ('afilename.pyc', 'afilename.pyo'):
            extension = os.path.splitext(name)[1]
            self.assertEqual(
                self._callFUT(name),
                'Skipping %s file ' % extension + '%(filename)s')

    def test_should_skip_jython_class_file(self):
        self.assertEqual(
            self._callFUT('afilename$py.class'),
            'Skipping $py.class file %(filename)s') 

    def test_should_skip_version_control_directory(self):
        for name in ('CVS', '_darcs'):
            self.assertEqual(
                self._callFUT(name),
                'Skipping version control directory %(filename)s')         

    def test_valid_file_is_not_skipped(self):
        self.assertEqual(
            self._callFUT('a_filename'), None)

class RawInputMockObject( object ):
    count = 0
    def __init__( self, fake_input ):
        self.input= fake_input
        self.count = 0
    def __call__( self, prompt ):
        # Don't cycle endlessly.
        self.count += 1
        if self.count > 1:
            return 'y'
        else:
            return self.input

class Test_query_interactive(unittest.TestCase):

    def setUp(self):
        import tempfile
        from pyramid.compat import NativeIO
        self.dirname = tempfile.mkdtemp()
        self.out = NativeIO()
        self.fixturetuple = ('pyramid.tests.test_scaffolds',
                             'fixture_scaffold')
        self.src_content = """\
These are not the droids
that you are looking for."""
        self.dest_content = """\
These are the droids for
whom you are looking;
now you have found them."""
        self.src_fn = os.path.join(self.dirname, 'mypackage', '__init__.py')
        self.dest_fn = os.path.join(self.dirname, 'mypackage', '__init__.py')
        # query_interactive is only normally executed when the destination 
        # is discovered to be already occupied by existing files, so ...
        # create the required occupancy.
        from pyramid.scaffolds.copydir import copy_dir
        copy_dir(self.fixturetuple,
                      self.dirname,
                      {'package':'mypackage'},
                      0, False,
                      template_renderer=dummy_template_renderer)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dirname, ignore_errors=True)
        self.out.close()

    def _callFUT(self, *arg, **kw):
        from pyramid.scaffolds.copydir import query_interactive
        return query_interactive(*arg, **kw)

    def test_query_interactive_0y(self):
        from pyramid.scaffolds import copydir
        copydir.input_ = RawInputMockObject("y")
        self._callFUT(self.src_fn, self.dest_fn, 
                      self.src_content, self.dest_content, 
                      simulate=False,
                      out_=self.out)
        self.assertTrue("Replace" in self.out.getvalue())

    def test_query_interactive_1n(self):
        from pyramid.scaffolds import copydir
        copydir.input_ = RawInputMockObject("n")
        self._callFUT(self.src_fn, self.dest_fn, 
                      self.src_content, 
                      '\n'.join(self.dest_content.split('\n')[:-1]), 
                      simulate=False,
                      out_=self.out)
        self.assertTrue("Replace" in self.out.getvalue())

    def test_query_interactive_2b(self):
        from pyramid.scaffolds import copydir
        copydir.input_ = RawInputMockObject("b")
        with open(os.path.join(
            self.dirname, 'mypackage', '__init__.py.bak'), 'w') as fp:
            fp.write("")
            fp.close()
        self._callFUT(self.src_fn, self.dest_fn, 
                      self.dest_content, self.src_content, 
                      simulate=False,
                      out_=self.out)
        self.assertTrue("Backing up" in self.out.getvalue())

    def test_query_interactive_3d(self):
        from pyramid.scaffolds import copydir
        copydir.input_ = RawInputMockObject("d")
        self._callFUT(self.src_fn, self.dest_fn, 
                      self.dest_content, self.src_content, 
                      simulate=False,
                      out_=self.out)
        output = self.out.getvalue()
        # The useful text in self.out gets wiped out on the second
        # call to raw_input, otherwise the test could be made
        # more usefully precise...
        # print("3d", output)
        # self.assertTrue("@@" in output, output)
        self.assertTrue("Replace" in output)

    def test_query_interactive_4dc(self):
        from pyramid.scaffolds import copydir
        copydir.input_ = RawInputMockObject("dc")
        self._callFUT(self.src_fn, self.dest_fn, 
                      self.dest_content, self.src_content, 
                      simulate=False,
                      out_=self.out)
        output = self.out.getvalue()
        # The useful text in self.out gets wiped out on the second
        # call to raw_input, otherwise, the test could be made
        # more usefully precise...
        # print("4dc", output)
        # self.assertTrue("***" in output, output)
        self.assertTrue("Replace" in output)

    def test_query_interactive_5allbad(self):
        from pyramid.scaffolds import copydir
        copydir.input_ = RawInputMockObject("all z")
        self._callFUT(self.src_fn, self.dest_fn, 
                      self.src_content, self.dest_content, 
                      simulate=False,
                      out_=self.out)
        output = self.out.getvalue()
        # The useful text in self.out gets wiped out on the second
        # call to raw_input, otherwise the test could be made
        # more usefully precise...
        # print("5allbad", output)
        # self.assertTrue("Responses" in output, output)
        self.assertTrue("Replace" in output)

    def test_query_interactive_6all(self):
        from pyramid.scaffolds import copydir
        copydir.input_ = RawInputMockObject("all b")
        self._callFUT(self.src_fn, self.dest_fn, 
                      self.src_content, self.dest_content, 
                      simulate=False,
                      out_=self.out)
        output = self.out.getvalue()
        # The useful text in self.out gets wiped out on the second
        # call to raw_input, otherwise the test could be made
        # more usefully precise...
        # print("6all", output)
        # self.assertTrue("Responses" in output, output)
        self.assertTrue("Replace" in output)

def dummy_template_renderer(content, v, filename=None):
    return content
    
