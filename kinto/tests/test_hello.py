from kinto.config import render_template, HERE, init
import os
import unittest

class ConfigTest(unittest.TestCase):

#to check if values dict is not empty    
        
#To check if rendered template generates a file
   
    def test_init(self):
        
        destination = os.path.join(os.path.abspath(os.path.dirname(__file__)), test.ini)
        
        self.assertEqual(init(destination,1),kinto1)