import unittest

class TestPDistReportCommand(unittest.TestCase):
    def _callFUT(self, **kw):
        argv = []
        from pyramid.scripts.pdistreport import main
        return main(argv, **kw)

    def test_no_dists(self):
        def platform():
            return 'myplatform'
        pkg_resources = DummyPkgResources()
        L = []
        def out(*args):
            L.extend(args)
        result = self._callFUT(pkg_resources=pkg_resources, platform=platform,
                               out=out)
        self.assertEqual(result, None)
        self.assertEqual(
            L,
            ['Pyramid version:', '1',
             'Platform:', 'myplatform',
             'Packages:']
            )

    def test_with_dists(self):
        def platform():
            return 'myplatform'
        working_set = (DummyDistribution('abc'), DummyDistribution('def'))
        pkg_resources = DummyPkgResources(working_set)
        L = []
        def out(*args):
            L.extend(args)
        result = self._callFUT(pkg_resources=pkg_resources, platform=platform,
                               out=out)
        self.assertEqual(result, None)
        self.assertEqual(
            L,
            ['Pyramid version:',
             '1',
             'Platform:',
             'myplatform',
             'Packages:',
             ' ',
             'abc',
             '1',
             '   ',
             '/projects/abc',
             ' ',
             'def',
             '1',
             '   ',
             '/projects/def']
            )

class DummyPkgResources(object):
    def __init__(self, working_set=()):
        self.working_set = working_set

    def get_distribution(self, name):
        return Version('1')

class Version(object):
    def __init__(self, version):
        self.version = version

class DummyDistribution(object):
    def __init__(self, name):
        self.project_name = name
        self.version = '1'
        self.location = '/projects/%s' % name
        
        
