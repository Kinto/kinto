import sys
import os
import shutil
import subprocess
import tempfile
import time

try:
    import http.client as httplib
except ImportError:
    import httplib


class TemplateTest(object):
    def make_venv(self, directory):  # pragma: no cover
        import virtualenv
        from virtualenv import Logger
        logger = Logger([(Logger.level_for_integer(2), sys.stdout)])
        virtualenv.logger = logger
        virtualenv.create_environment(directory,
                                      site_packages=False,
                                      clear=False,
                                      unzip_setuptools=True)

    def install(self, tmpl_name):  # pragma: no cover
        try:
            self.old_cwd = os.getcwd()
            self.directory = tempfile.mkdtemp()
            self.make_venv(self.directory)
            here = os.path.abspath(os.path.dirname(__file__))
            os.chdir(os.path.dirname(os.path.dirname(here)))
            pip = os.path.join(self.directory, 'bin', 'pip')
            subprocess.check_call([pip, 'install', '-e', '.'])
            os.chdir(self.directory)
            subprocess.check_call(['bin/pcreate', '-s', tmpl_name, 'Dingle'])
            os.chdir('Dingle')
            subprocess.check_call([pip, 'install', '.[testing]'])
            if tmpl_name == 'alchemy':
                populate = os.path.join(self.directory, 'bin',
                                        'initialize_Dingle_db')
                subprocess.check_call([populate, 'development.ini'])
            subprocess.check_call([
                os.path.join(self.directory, 'bin', 'py.test')])
            pserve = os.path.join(self.directory, 'bin', 'pserve')
            for ininame, hastoolbar in (('development.ini', True),
                                        ('production.ini', False)):
                proc = subprocess.Popen([pserve, ininame])
                try:
                    time.sleep(5)
                    proc.poll()
                    if proc.returncode is not None:
                        raise RuntimeError('%s didnt start' % ininame)
                    conn = httplib.HTTPConnection('localhost:6543')
                    conn.request('GET', '/')
                    resp = conn.getresponse()
                    assert resp.status == 200, ininame
                    data = resp.read()
                    toolbarchunk = b'<div id="pDebug"'
                    if hastoolbar:
                        assert toolbarchunk in data, ininame
                    else:
                        assert toolbarchunk not in data, ininame
                finally:
                    proc.terminate()
        finally:
            shutil.rmtree(self.directory)
            os.chdir(self.old_cwd)

if __name__ == '__main__':     # pragma: no cover
    templates = ['starter', 'alchemy', 'zodb']

    for name in templates:
        test = TemplateTest()
        test.install(name)
    
