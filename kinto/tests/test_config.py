from kinto.config import render_template, HERE, init
import os
import unittest
import codecs
import tempfile


class ConfigTest(unittest.TestCase):        
    def test_transpose_parameters_into_template(self):
        self.maxDiff = None
        template = "kinto.tpl"
        dest = tempfile.mktemp()
        #dest = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test.ini") #mtemp
        render_template(template, dest,
                        secret='secret',
                        storage_backend='storage_backend',
                        cache_backend='cache_backend',  
                        permission_backend='permission_backend',
                        storage_url='storage_url',
                        cache_url='cache_url',
                        permission_url='permission_url')
       
        with codecs.open(dest, 'r', encoding='utf-8') as d:
            destination_temp = d.read()
        
        sample_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),"test_configuration/test.ini") 
        with codecs.open(sample_path, 'r', encoding='utf-8') as c:
            sample = c.read()
        
        self.assertEqual(destination_temp, sample)
               
    def test_create_destination_directory(self):
        dest = os.path.join(tempfile.gettempdir(), 'config/kinto.ini')
        
        render_template("kinto.tpl", dest,
                        secret='secret',
                        storage_backend='storage_backend',
                        cache_backend='cache_backend',  
                        permission_backend='permission_backend',
                        storage_url='storage_url',
                        cache_url='cache_url',
                        permission_url='permission_url')
        
        self.assertTrue(os.path.exists(dest))
