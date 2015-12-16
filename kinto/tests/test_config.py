from ..config import render_template as origin
from .support import unittest

class ConfigTest(unittest.TestCase):

#to check if values dict is not empty
    def test_values_is_not_empty(self):
        self.assertNotEqual(origin.values, {})
        
        
#To check if template location is correct
    def test_template_location_is_not_null(self):
        self.assertNotEqual(origin.template, '')


#To check if destination location is correct
    def test_destination_location_is_not_null(self):
        self.assertNotEqual(origin.destination, '')



#To check if file is created at correct location
    def test_file_is_craeted(self):
        self.assertNotEqual(origin.output, NULL)
    