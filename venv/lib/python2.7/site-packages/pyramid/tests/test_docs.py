import unittest

if 0:
    # no released version of manuel actually works with :lineno:
    # settings yet
    class ManuelDocsCase(unittest.TestCase):
        def __new__(self, test):
            return getattr(self, test)()

        @classmethod
        def test_docs(cls):
            import os
            import pkg_resources
            import manuel.testing
            import manuel.codeblock
            import manuel.capture
            import manuel.ignore
            m = manuel.ignore.Manuel()
            m += manuel.codeblock.Manuel()
            m += manuel.capture.Manuel()
            docs = []

            egg_path = pkg_resources.get_distribution('pyramid').location
            path = os.path.join(egg_path, 'docs')
            for root, dirs, files in os.walk(path):
                for ignore in ('.svn', '.build', '.hg', '.git', 'CVS'):
                    if ignore in dirs:
                        dirs.remove(ignore)

                for filename in files:
                    if filename.endswith('.rst'):
                        docs.append(os.path.join(root, filename))

            print(path)
            return manuel.testing.TestSuite(m, *docs)
