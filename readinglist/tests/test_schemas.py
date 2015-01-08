import unittest

import colander

from readinglist.views.article import ArticleSchema


class ArticleSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = ArticleSchema()
        self.schema = self.schema.bind()
        self.record = dict(title="We are Charlie",
                           url="http://charliehebdo.fr",
                           added_by="FxOS")
        self.deserialized = self.schema.deserialize(self.record)

    def test_record_validation(self):
        self.assertEqual(self.deserialized['title'], self.record['title'])

    def test_record_validation_default_values(self):
        self.assertEqual(self.deserialized['status'], 0)
        self.assertEqual(self.deserialized['excerpt'], '')
        self.assertEqual(self.deserialized['favorite'], False)
        self.assertEqual(self.deserialized['unread'], True)
        self.assertEqual(self.deserialized['is_article'], True)
        self.assertIsNone(self.deserialized.get('marked_read_by'))
        self.assertIsNone(self.deserialized.get('marked_read_on'))
        self.assertIsNone(self.deserialized.get('word_count'))

    def test_record_validation_computed_values(self):
        self.assertEqual(self.deserialized['resolved_url'],
                         "http://charliehebdo.fr")
        self.assertEqual(self.deserialized['resolved_title'],
                         "We are Charlie")
        self.assertIsNotNone(self.deserialized.get('stored_on'))
        self.assertIsNotNone(self.deserialized.get('last_modified'))

    def test_url_is_required(self):
        self.record.pop('url')
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_url_is_stripped(self):
        self.record['url'] = '  http://charliehebdo.fr'
        deserialized = self.schema.deserialize(self.record)
        self.assertEqual(deserialized['url'], 'http://charliehebdo.fr')

    def test_title_is_required(self):
        self.record.pop('title')
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_title_is_stripped(self):
        self.record['title'] = '  Nous Sommes Charlie  '
        deserialized = self.schema.deserialize(self.record)
        self.assertEqual(deserialized['title'], 'Nous Sommes Charlie')

    def test_title_must_be_at_least_one_character(self):
        self.record['title'] = ''
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_added_by_is_required(self):
        self.record.pop('added_by')
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_added_by_must_be_at_least_one_character(self):
        self.record['added_by'] = ''
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_marked_read_by_must_be_at_least_one_character(self):
        self.record['marked_read_by'] = ' '
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)
