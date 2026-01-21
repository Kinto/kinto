import unittest

import colander

from kinto.core.cornice_swagger.converters import convert_schema as convert
from kinto.core.cornice_swagger.swagger import DefinitionHandler


class MyListSchema(colander.SequenceSchema):
    entry = colander.SchemaNode(colander.String())


class BoredoomSchema(colander.MappingSchema):
    motivators = MyListSchema()
    status = colander.SchemaNode(
        colander.String(), validator=colander.OneOf(["increasing", "decrasing"])
    )


class AnxietySchema(colander.MappingSchema):
    level = colander.SchemaNode(colander.Integer(), validator=colander.Range(42, 9000))


class FeelingsSchema(colander.MappingSchema):
    bleh = BoredoomSchema()
    aaaa = AnxietySchema()


class DefinitionTest(unittest.TestCase):
    def setUp(self):
        self.handler = DefinitionHandler()

    def test_from_schema(self):
        self.assertDictEqual(self.handler.from_schema(FeelingsSchema()), convert(FeelingsSchema()))


class RefDefinitionTest(unittest.TestCase):
    def test_single_level(self):
        handler = DefinitionHandler(ref=1)
        ref = handler.from_schema(FeelingsSchema(title="Feelings"))

        self.assertEqual(ref, {"$ref": "#/definitions/Feelings"})
        self.assertDictEqual(
            handler.definition_registry["Feelings"], convert(FeelingsSchema(title="Feelings"))
        )
