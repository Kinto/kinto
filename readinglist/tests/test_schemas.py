import mock
import colander

from readinglist.resource import TimeStamp
from readinglist.views.article import ArticleSchema

from .support import unittest


class TimeStampTest(unittest.TestCase):
    @mock.patch('readinglist.resource.msec_time')
    def test_default_value_comes_from_timestamper(self, time_mocked):
        time_mocked.return_value = 666
        default = TimeStamp().deserialize(colander.null)
        self.assertEqual(default, 666)


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
        self.assertEqual(self.deserialized['read_position'], 0)
        self.assertIsNone(self.deserialized.get('marked_read_by'))
        self.assertIsNone(self.deserialized.get('marked_read_on'))
        self.assertIsNone(self.deserialized.get('word_count'))
        self.assertIsNone(self.deserialized.get('resolved_url'))
        self.assertIsNone(self.deserialized.get('resolved_title'))

    def test_record_validation_computed_values(self):
        self.assertIsNotNone(self.deserialized.get('stored_on'))
        self.assertIsNotNone(self.deserialized.get('added_on'))
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

    def test_resolved_url_is_stripped(self):
        self.record['resolved_url'] = '  http://charliehebdo.fr'
        deserialized = self.schema.deserialize(self.record)
        self.assertEqual(deserialized['resolved_url'],
                         'http://charliehebdo.fr')

    def test_url_has_max_length(self):
        self.record['url'] = 'http://charliehebdo.fr/#' + ('a' * 2048)
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_resolved_url_has_max_length(self):
        self.record['resolved_url'] = 'http://charliehebdo.fr/#' + ('a' * 2048)
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_title_is_required(self):
        self.record.pop('title')
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_title_is_stripped(self):
        self.record['title'] = '  Nous Sommes Charlie  '
        deserialized = self.schema.deserialize(self.record)
        self.assertEqual(deserialized['title'], 'Nous Sommes Charlie')

    def test_title_max_length_represents_characters_not_bytes(self):
        self.record['title'] = u'\u76d8' * 1024
        self.schema.deserialize(self.record)  # not raising

    def test_title_has_max_length(self):
        self.record['title'] = u'\u76d8' * 1025
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_resolved_title_has_max_length(self):
        self.record['resolved_title'] = u'\u76d8' * 1025
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_resolved_title_is_stripped(self):
        self.record['resolved_title'] = '  Nous Sommes Charlie  '
        deserialized = self.schema.deserialize(self.record)
        self.assertEqual(deserialized['resolved_title'], 'Nous Sommes Charlie')

    def test_title_must_be_at_least_one_character(self):
        self.record['title'] = ''
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_resolved_title_must_be_at_least_one_character(self):
        self.record['resolved_title'] = ' '
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

    def test_read_position_must_be_positive(self):
        self.record['read_position'] = -1
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_status_cannot_be_negative(self):
        self.record['status'] = -1
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)

    def test_status_cannot_be_set_to_deleted(self):
        self.record['status'] = 2
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          self.record)
