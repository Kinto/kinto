# -*- coding:utf-8 -*-
import unittest
from colander.compat import text_, text_type

def invalid_exc(func, *arg, **kw):
    from colander import Invalid
    try:
        func(*arg, **kw)
    except Invalid as e:
        return e
    else:
        raise AssertionError('Invalid not raised') # pragma: no cover

class TestInvalid(unittest.TestCase):
    def _makeOne(self, node, msg=None, val=None):
        from colander import Invalid
        exc = Invalid(node, msg, val)
        return exc

    def test_ctor(self):
        exc = self._makeOne(None, 'msg', 'val')
        self.assertEqual(exc.node, None)
        self.assertEqual(exc.msg, 'msg')
        self.assertEqual(exc.value, 'val')
        self.assertEqual(exc.children, [])

    def test_add(self):
        exc = self._makeOne(None, 'msg')
        other = Dummy()
        exc.add(other)
        self.assertFalse(hasattr(other, 'positional'))
        self.assertEqual(exc.children, [other])

    def test_add_positional(self):
        from colander import Positional
        p = Positional()
        node = DummySchemaNode(p)
        exc = self._makeOne(node, 'msg')
        other = Dummy()
        exc.add(other)
        self.assertEqual(other.positional, True)
        self.assertEqual(exc.children, [other])

    def test__keyname_no_parent(self):
        node = DummySchemaNode(None, name='name')
        exc = self._makeOne(None, '')
        exc.node = node
        self.assertEqual(exc._keyname(), 'name')

    def test__keyname_positional(self):
        exc = self._makeOne(None, '')
        exc.positional = True
        exc.pos = 2
        self.assertEqual(exc._keyname(), '2')

    def test__keyname_nonpositional_parent(self):
        parent = Dummy()
        parent.node = DummySchemaNode(None)
        exc = self._makeOne(None, 'me')
        exc.parent = parent
        exc.pos = 2
        exc.node = DummySchemaNode(None, name='name')
        self.assertEqual(exc._keyname(), 'name')

    def test_paths(self):
        exc1 = self._makeOne(None, 'exc1')
        exc2 = self._makeOne(None, 'exc2')
        exc3 = self._makeOne(None, 'exc3')
        exc4 = self._makeOne(None, 'exc4')
        exc1.add(exc2)
        exc2.add(exc3)
        exc1.add(exc4)
        paths = list(exc1.paths())
        self.assertEqual(paths, [(exc1, exc2, exc3), (exc1, exc4)])

    def test_asdict(self):
        from colander import Positional
        node1 = DummySchemaNode(None, 'node1')
        node2 = DummySchemaNode(Positional(), 'node2')
        node3 = DummySchemaNode(Positional(), 'node3')
        node4 = DummySchemaNode(Positional(), 'node4')
        exc1 = self._makeOne(node1, 'exc1')
        exc1.pos = 1
        exc2 = self._makeOne(node2, 'exc2')
        exc3 = self._makeOne(node3, 'exc3')
        exc4 = self._makeOne(node4, 'exc4')
        exc1.add(exc2, 2)
        exc2.add(exc3, 3)
        exc1.add(exc4, 4)
        d = exc1.asdict()
        self.assertEqual(d, {'node1.node2.3': 'exc1; exc2; exc3',
                             'node1.node4': 'exc1; exc4'})

    def test_asdict_with_all_validator(self):
        # see https://github.com/Pylons/colander/pull/27
        from colander import All
        from colander import Positional
        node1 = DummySchemaNode(None, 'node1')
        node2 = DummySchemaNode(Positional(), 'node2')
        node3 = DummySchemaNode(Positional(), 'node3')
        node1.children = [node3]
        validator1 = DummyValidator('validator1')
        validator2 = DummyValidator('validator2')
        validator = All(validator1, validator2)
        exc1 =  self._makeOne(node1, 'exc1')
        exc1.pos = 1
        exc1['node3'] = 'message1'
        exc2 = self._makeOne(node2, 'exc2')
        exc3 = invalid_exc(validator, None, None)
        exc1.add(exc2, 2)
        exc2.add(exc3, 3)
        d = exc1.asdict()
        self.assertEqual(
            d,
            {'node1.node2.3': 'exc1; exc2; validator1; validator2',
             'node1.node3': 'exc1; message1'})

    def test_asdict_with_all_validator_functional(self):
        # see https://github.com/Pylons/colander/issues/2
        import colander as c
        class MySchema(c.MappingSchema):
            number1 = c.SchemaNode(c.Int(), validator=c.Range(min=1))
            number2 = c.SchemaNode(c.Int(), validator=c.Range(min=1))
        def validate_higher(node, val):
            if val['number1'] >= val['number2']:
                raise c.Invalid(node, 'Number 1 must be lower than number 2')
        def validate_different(node, val):
            if val['number1'] == val['number2']:
                raise c.Invalid(node, "They can't be the same, either")
        schema = MySchema(validator=c.All(validate_higher, validate_different))
        try:
            schema.deserialize(dict(number1=2, number2=2))
        except c.Invalid as e:
            result = e.asdict()
            self.assertEqual(
                result,
                {'': ("Number 1 must be lower than number 2; "
                      "They can't be the same, either")})
        try:
            schema.deserialize(dict(number1=2, number2=2))
        except c.Invalid as e:
            result = e.asdict(separator=None)
            self.assertEqual(
                result,
                {'': ["Number 1 must be lower than number 2",
                      "They can't be the same, either"]})

    def test___str__(self):
        from colander import Positional
        node1 = DummySchemaNode(None, 'node1')
        node2 = DummySchemaNode(Positional(), 'node2')
        node3 = DummySchemaNode(Positional(), 'node3')
        node4 = DummySchemaNode(Positional(), 'node4')
        exc1 = self._makeOne(node1, 'exc1')
        exc1.pos = 1
        exc2 = self._makeOne(node2, 'exc2')
        exc3 = self._makeOne(node3, 'exc3')
        exc4 = self._makeOne(node4, 'exc4')
        exc1.add(exc2, 2)
        exc2.add(exc3, 3)
        exc1.add(exc4, 4)
        result = str(exc1)
        self.assertEqual(
            result,
            "{'node1.node2.3': 'exc1; exc2; exc3', "
            "'node1.node4': 'exc1; exc4'}"
            )

    def test___setitem__fails(self):
        node = DummySchemaNode(None)
        exc = self._makeOne(node, 'msg')
        self.assertRaises(KeyError, exc.__setitem__, 'notfound', 'msg')

    def test___setitem__succeeds(self):
        node = DummySchemaNode(None)
        child = DummySchemaNode(None)
        child.name = 'found'
        node.children = [child]
        exc = self._makeOne(node, 'msg')
        exc['found'] = 'msg2'
        self.assertEqual(len(exc.children), 1)
        childexc = exc.children[0]
        self.assertEqual(childexc.pos, 0)
        self.assertEqual(childexc.node.name, 'found')

    def test_messages_msg_iterable(self):
        node = DummySchemaNode(None)
        exc = self._makeOne(node, [123, 456])
        self.assertEqual(exc.messages(), [123, 456])

    def test_messages_msg_not_iterable(self):
        node = DummySchemaNode(None)
        exc = self._makeOne(node, 'msg')
        self.assertEqual(exc.messages(), ['msg'])

    def test_messages_msg_None(self):
        node = DummySchemaNode(None)
        exc = self._makeOne(node, None)
        self.assertEqual(exc.messages(), [])

class TestAll(unittest.TestCase):
    def _makeOne(self, validators):
        from colander import All
        return All(*validators)

    def test_success(self):
        validator1 = DummyValidator()
        validator2 = DummyValidator()
        validator = self._makeOne([validator1, validator2])
        self.assertEqual(validator(None, None), None)

    def test_failure(self):
        validator1 = DummyValidator('msg1')
        validator2 = DummyValidator('msg2')
        validator = self._makeOne([validator1, validator2])
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg, ['msg1', 'msg2'])

    def test_Invalid_children(self):
        from colander import Invalid
        node1 = DummySchemaNode(None, 'node1')
        node = DummySchemaNode(None, 'node')
        node.children = [node1]
        exc1 = Invalid(node1, 'exc1')
        exc2 = Invalid(node1, 'exc2')
        validator1 = DummyValidator('validator1', [exc1])
        validator2 = DummyValidator('validator2', [exc2])
        validator = self._makeOne([validator1, validator2])
        exc = invalid_exc(validator, node, None)
        self.assertEqual(exc.children, [exc1, exc2])

class TestAny(unittest.TestCase):
    def _makeOne(self, validators):
        from colander import Any
        return Any(*validators)

    def test_success(self):
        validator1 = DummyValidator('msg1')
        validator2 = DummyValidator()
        validator = self._makeOne([validator1, validator2])
        self.assertEqual(validator(None, None), None)

    def test_failure(self):
        validator1 = DummyValidator('msg1')
        validator2 = DummyValidator('msg2')
        validator = self._makeOne([validator1, validator2])
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg, ['msg1', 'msg2'])

    def test_Invalid_children(self):
        from colander import Invalid
        node1 = DummySchemaNode(None, 'node1')
        node = DummySchemaNode(None, 'node')
        node.children = [node1]
        exc1 = Invalid(node1, 'exc1')
        validator1 = DummyValidator('validator1', [exc1])
        validator2 = DummyValidator()
        validator = self._makeOne([validator1, validator2])
        self.assertEqual(validator(None, None), None)

class TestFunction(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from colander import Function
        return Function(*arg, **kw)

    def test_success_function_returns_True(self):
        validator = self._makeOne(lambda x: True)
        self.assertEqual(validator(None, None), None)

    def test_fail_function_returns_empty_string(self):
        validator = self._makeOne(lambda x: '')
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg, 'Invalid value')

    def test_fail_function_returns_False(self):
        validator = self._makeOne(lambda x: False)
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg, 'Invalid value')

    def test_fail_function_returns_string(self):
        validator = self._makeOne(lambda x: 'fail')
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg, 'fail')

    def test_deprecated_message(self):
        import warnings
        orig_warn = warnings.warn
        log = []
        def warn(message, category=None, stacklevel=1):
            log.append((message, category, stacklevel))
        try:
            # Monkey patching warn so that tests run quietly
            warnings.warn = warn
            validator = self._makeOne(lambda x: False, message='depr')
            e = invalid_exc(validator, None, None)
            self.assertEqual(e.msg.interpolate(), 'depr')
        finally:
            warnings.warn = orig_warn


    def test_deprecated_message_warning(self):
        import warnings
        orig_warn = warnings.warn
        log = []
        def warn(message, category=None, stacklevel=1):
            log.append((message, category, stacklevel))
        try:
            # Monkey patching warn since catch_warnings context manager
            # is not working when running the full suite
            warnings.warn = warn
            validator = self._makeOne(lambda x: False, message='depr')
            invalid_exc(validator, None, None)
            self.assertEqual(len(log), 1)
        finally:
            warnings.warn = orig_warn

    def test_msg_and_message_error(self):
        self.assertRaises(ValueError, self._makeOne,
                          lambda x: False, msg='one', message='two')

    def test_error_message_adds_mapping_to_configured_message(self):
        validator = self._makeOne(lambda x: False, msg='fail ${val}')
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg.interpolate(), 'fail None')

    def test_error_message_adds_mapping_to_return_message(self):
        validator = self._makeOne(lambda x: 'fail ${val}')
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg.interpolate(), 'fail None')

    def test_error_message_does_not_overwrite_configured_domain(self):
        import translationstring
        _ = translationstring.TranslationStringFactory('fnord')
        validator = self._makeOne(lambda x: False, msg=_('fail ${val}'))
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg.domain, 'fnord')

    def test_error_message_does_not_overwrite_returned_domain(self):
        import translationstring
        _ = translationstring.TranslationStringFactory('fnord')
        validator = self._makeOne(lambda x: _('fail ${val}'))
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg.domain, 'fnord')

    def test_propagation(self):
        validator = self._makeOne(lambda x: 'a' in x, 'msg')
        self.assertRaises(TypeError, validator, None, None)

class TestRange(unittest.TestCase):
    def _makeOne(self, **kw):
        from colander import Range
        return Range(**kw)

    def test_success_no_bounds(self):
        validator = self._makeOne()
        self.assertEqual(validator(None, 1), None)

    def test_success_upper_bound_only(self):
        validator = self._makeOne(max=1)
        self.assertEqual(validator(None, -1), None)

    def test_success_minimum_bound_only(self):
        validator = self._makeOne(min=0)
        self.assertEqual(validator(None, 1), None)

    def test_success_min_and_max(self):
        validator = self._makeOne(min=1, max=1)
        self.assertEqual(validator(None, 1), None)

    def test_min_failure(self):
        validator = self._makeOne(min=1)
        e = invalid_exc(validator, None, 0)
        self.assertEqual(e.msg.interpolate(), '0 is less than minimum value 1')

    def test_min_failure_msg_override(self):
        validator = self._makeOne(min=1, min_err='wrong')
        e = invalid_exc(validator, None, 0)
        self.assertEqual(e.msg, 'wrong')

    def test_max_failure(self):
        validator = self._makeOne(max=1)
        e = invalid_exc(validator, None, 2)
        self.assertEqual(e.msg.interpolate(),
                         '2 is greater than maximum value 1')

    def test_max_failure_msg_override(self):
        validator = self._makeOne(max=1, max_err='wrong')
        e = invalid_exc(validator, None, 2)
        self.assertEqual(e.msg, 'wrong')

class TestRegex(unittest.TestCase):
    def _makeOne(self, pattern):
        from colander import Regex
        return Regex(pattern)

    def test_valid_regex(self):
        self.assertEqual(self._makeOne('a')(None, 'a'), None)
        self.assertEqual(self._makeOne('[0-9]+')(None, '1111'), None)
        self.assertEqual(self._makeOne('')(None, ''), None)
        self.assertEqual(self._makeOne('.*')(None, ''), None)

    def test_invalid_regexs(self):
        from colander import Invalid
        self.assertRaises(Invalid, self._makeOne('[0-9]+'), None, 'a')
        self.assertRaises(Invalid, self._makeOne('a{2,4}'), None, 'ba')

    def test_regex_not_string(self):
        from colander import Invalid
        import re
        regex = re.compile('[0-9]+')
        self.assertEqual(self._makeOne(regex)(None, '01'), None)
        self.assertRaises(Invalid, self._makeOne(regex), None, 't')


class TestEmail(unittest.TestCase):
    def _makeOne(self):
        from colander import Email
        return Email()

    def test_valid_emails(self):
        validator = self._makeOne()
        self.assertEqual(validator(None, 'me@here.com'), None)
        self.assertEqual(validator(None, 'me1@here1.com'), None)
        self.assertEqual(validator(None, 'name@here1.us'), None)
        self.assertEqual(validator(None, 'name@here1.info'), None)
        self.assertEqual(validator(None, 'foo@bar.baz.biz'), None)
        self.assertEqual(validator(None, "tip'oneill@house.gov"), None)

    def test_empty_email(self):
        validator = self._makeOne()
        e = invalid_exc(validator, None, '')
        self.assertEqual(e.msg, 'Invalid email address')

    def test_invalid_emails(self):
        validator = self._makeOne()
        from colander import Invalid
        self.assertRaises(Invalid, validator, None, 'me@here.')
        self.assertRaises(Invalid,
                          validator, None, 'name@here.tldiswaytoolooooooooong')
        self.assertRaises(Invalid, validator, None, '@here.us')
        self.assertRaises(Invalid, validator, None, 'me@here..com')
        self.assertRaises(Invalid, validator, None, 'me@we-here-.com')


class TestLength(unittest.TestCase):
    def _makeOne(self, **kw):
        from colander import Length
        return Length(**kw)

    def test_success_no_bounds(self):
        validator = self._makeOne()
        self.assertEqual(validator(None, ''), None)

    def test_success_upper_bound_only(self):
        validator = self._makeOne(max=1)
        self.assertEqual(validator(None, 'a'), None)

    def test_success_minimum_bound_only(self):
        validator = self._makeOne(min=0)
        self.assertEqual(validator(None, ''), None)

    def test_success_min_and_max(self):
        validator = self._makeOne(min=1, max=1)
        self.assertEqual(validator(None, 'a'), None)

    def test_min_failure(self):
        validator = self._makeOne(min=1)
        e = invalid_exc(validator, None, '')
        self.assertEqual(e.msg.interpolate(), 'Shorter than minimum length 1')

    def test_max_failure(self):
        validator = self._makeOne(max=1)
        e = invalid_exc(validator, None, 'ab')
        self.assertEqual(e.msg.interpolate(), 'Longer than maximum length 1')

    def test_min_failure_msg_override(self):
        validator = self._makeOne(min=1, min_err='Need at least ${min}, mate')
        e = invalid_exc(validator, None, [])
        self.assertEqual(e.msg.interpolate(), 'Need at least 1, mate')

    def test_max_failure_msg_override(self):
        validator = self._makeOne(max=1, max_err='No more than ${max}, mate')
        e = invalid_exc(validator, None, [1, 2])
        self.assertEqual(e.msg.interpolate(), 'No more than 1, mate')


class TestOneOf(unittest.TestCase):
    def _makeOne(self, values):
        from colander import OneOf
        return OneOf(values)

    def test_success(self):
        validator = self._makeOne([1])
        self.assertEqual(validator(None, 1), None)

    def test_failure(self):
        validator = self._makeOne([1, 2])
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg.interpolate(), '"None" is not one of 1, 2')


class TestNoneOf(unittest.TestCase):
    def _makeOne(self, values):
        from colander import NoneOf
        return NoneOf(values)

    def test_success(self):
        validator = self._makeOne([1, 2])
        self.assertEqual(validator(None, 3), None)

    def test_failure(self):
        validator = self._makeOne([1, 2])
        e = invalid_exc(validator, None, 2)
        self.assertEqual(e.msg.interpolate(), '"2" must not be one of 1, 2')


class TestContainsOnly(unittest.TestCase):
    def _makeOne(self, values):
        from colander import ContainsOnly
        return ContainsOnly(values)

    def test_success(self):
        validator = self._makeOne([1])
        self.assertEqual(validator(None, [1]), None)

    def test_failure(self):
        validator = self._makeOne([1])
        e = invalid_exc(validator, None, [2])
        self.assertEqual(
            e.msg.interpolate(),
            'One or more of the choices you made was not acceptable'
            )

    def test_failure_with_custom_error_template(self):
        validator = self._makeOne([1])
        from colander import _
        validator.err_template = _('${val}: ${choices}')
        e = invalid_exc(validator, None, [2])
        self.assertTrue('[2]' in e.msg.interpolate())

class Test_luhnok(unittest.TestCase):
    def _callFUT(self, node, value):
        from colander import luhnok
        return luhnok(node, value)

    def test_fail(self):
        import colander
        val = '10'
        self.assertRaises(colander.Invalid, self._callFUT, None, val)

    def test_fail2(self):
        import colander
        val = '99999999999999999999999'
        self.assertRaises(colander.Invalid, self._callFUT, None, val)

    def test_fail3(self):
        import colander
        val = 'abcdefghij'
        self.assertRaises(colander.Invalid, self._callFUT, None, val)

    def test_success(self):
        val = '4111111111111111'
        self.assertFalse(self._callFUT(None, val))

class Test_url_validator(unittest.TestCase):
    def _callFUT(self, val):
        from colander import url
        return url(None, val)

    def test_it_success(self):
        val = 'http://example.com'
        result = self._callFUT(val)
        self.assertEqual(result, None)

    def test_it_failure(self):
        val = 'not-a-url'
        from colander import Invalid
        self.assertRaises(Invalid, self._callFUT, val)

class TestUUID(unittest.TestCase):
    def _callFUT(self, val):
        from colander import uuid
        return uuid(None, val)

    def test_success_hexadecimal(self):
        val = '123e4567e89b12d3a456426655440000'
        result = self._callFUT(val)
        self.assertEqual(result, None)

    def test_success_with_dashes(self):
        val = '123e4567-e89b-12d3-a456-426655440000'
        result = self._callFUT(val)
        self.assertEqual(result, None)

    def test_success_upper_case(self):
        val = '123E4567-E89B-12D3-A456-426655440000'
        result = self._callFUT(val)
        self.assertEqual(result, None)

    def test_success_with_braces(self):
        val = '{123e4567-e89b-12d3-a456-426655440000}'
        result = self._callFUT(val)
        self.assertEqual(result, None)

    def test_success_with_urn_ns(self):
        val = 'urn:uuid:{123e4567-e89b-12d3-a456-426655440000}'
        result = self._callFUT(val)
        self.assertEqual(result, None)

    def test_failure_random_string(self):
        val = 'not-a-uuid'
        from colander import Invalid
        self.assertRaises(Invalid, self._callFUT, val)

    def test_failure_not_hexadecimal(self):
        val = '123zzzzz-uuuu-zzzz-uuuu-42665544zzzz'
        from colander import Invalid
        self.assertRaises(Invalid, self._callFUT, val)

    def test_failure_invalid_length(self):
        # Correct UUID: 8-4-4-4-12
        val = '88888888-333-4444-333-cccccccccccc'
        from colander import Invalid
        self.assertRaises(Invalid, self._callFUT, val)

    def test_failure_with_invalid_urn_ns(self):
        val = 'urn:abcd:{123e4567-e89b-12d3-a456-426655440000}'
        from colander import Invalid
        self.assertRaises(Invalid, self._callFUT, val)

class TestSchemaType(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from colander import SchemaType
        return SchemaType(*arg, **kw)

    def test_flatten(self):
        node = DummySchemaNode(None, name='node')
        typ = self._makeOne()
        result = typ.flatten(node, 'appstruct')
        self.assertEqual(result, {'node':'appstruct'})

    def test_flatten_listitem(self):
        node = DummySchemaNode(None, name='node')
        typ = self._makeOne()
        result = typ.flatten(node, 'appstruct', listitem=True)
        self.assertEqual(result, {'':'appstruct'})

    def test_unflatten(self):
        node = DummySchemaNode(None, name='node')
        typ = self._makeOne()
        result = typ.unflatten(node, ['node'], {'node': 'appstruct'})
        self.assertEqual(result, 'appstruct')

    def test_set_value(self):
        typ = self._makeOne()
        self.assertRaises(
            AssertionError, typ.set_value, None, None, None, None)

    def test_get_value(self):
        typ = self._makeOne()
        self.assertRaises(
            AssertionError, typ.get_value, None, None, None)

    def test_cstruct_children(self):
        typ = self._makeOne()
        self.assertEqual(typ.cstruct_children(None, None), [])

class TestMapping(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from colander import Mapping
        return Mapping(*arg, **kw)

    def test_ctor_bad_unknown(self):
        self.assertRaises(ValueError, self._makeOne, 'badarg')

    def test_ctor_good_unknown(self):
        try:
            self._makeOne('ignore')
            self._makeOne('raise')
            self._makeOne('preserve')
        except ValueError as e: # pragma: no cover
            raise AssertionError(e)

    def test_deserialize_not_a_mapping(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()

        # None
        e = invalid_exc(typ.deserialize, node, None)
        self.assertTrue(
            e.msg.interpolate().startswith('"None" is not a mapping type'))

        # list
        e = invalid_exc(typ.deserialize, node, [])
        self.assertTrue(
            e.msg.interpolate().startswith('"[]" is not a mapping type'))

        # str
        e = invalid_exc(typ.deserialize, node, "")
        self.assertTrue(
            e.msg.interpolate().startswith('"" is not a mapping type'))

        # tuple
        e = invalid_exc(typ.deserialize, node, ())
        self.assertTrue(
            e.msg.interpolate().startswith('"()" is not a mapping type'))

    def test_deserialize_null(self):
        import colander
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, colander.null)
        self.assertEqual(result, colander.null)

    def test_deserialize_no_subnodes(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, {})
        self.assertEqual(result, {})

    def test_deserialize_ok(self):
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        result = typ.deserialize(node, {'a':1})
        self.assertEqual(result, {'a':1})

    def test_deserialize_unknown_raise(self):
        import colander
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne(unknown='raise')
        e = invalid_exc(typ.deserialize, node, {'a':1, 'b':2})
        self.assertTrue(isinstance(e, colander.UnsupportedFields))
        self.assertEqual(e.fields, {'b': 2})
        self.assertEqual(e.msg.interpolate(),
                         "Unrecognized keys in mapping: \"{'b': 2}\"")


    def test_deserialize_unknown_preserve(self):
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne(unknown='preserve')
        result = typ.deserialize(node, {'a':1, 'b':2})
        self.assertEqual(result, {'a':1, 'b':2})

    def test_deserialize_subnodes_raise(self):
        node = DummySchemaNode(None)
        node.children = [
            DummySchemaNode(None, name='a', exc='Wrong 2'),
            DummySchemaNode(None, name='b', exc='Wrong 2'),
            ]
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, {'a':1, 'b':2})
        self.assertEqual(e.msg, None)
        self.assertEqual(len(e.children), 2)

    def test_deserialize_subnode_missing_default(self):
        import colander
        node = DummySchemaNode(None)
        node.children = [
            DummySchemaNode(None, name='a'),
            DummySchemaNode(None, name='b', default='abc'),
            ]
        typ = self._makeOne()
        result = typ.deserialize(node, {'a':1})
        self.assertEqual(result, {'a':1, 'b':colander.null})

    def test_serialize_null(self):
        import colander
        val = colander.null
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, {})

    def test_serialize_not_a_mapping(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, node, None)
        self.assertTrue(
            e.msg.interpolate().startswith('"None" is not a mapping type'))

    def test_serialize_no_subnodes(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, {})
        self.assertEqual(result, {})

    def test_serialize_ok(self):
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        result = typ.serialize(node, {'a':1})
        self.assertEqual(result, {'a':1})

    def test_serialize_with_unknown(self):
        node = DummySchemaNode(None)
        node.children = [
            DummySchemaNode(None, name='a'),
            ]
        typ = self._makeOne()
        result = typ.serialize(node, {'a':1, 'b':2})
        self.assertEqual(result, {'a':1})

    def test_serialize_value_is_null(self):
        node = DummySchemaNode(None)
        from colander import null
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        result = typ.serialize(node, null)
        self.assertEqual(result, {'a':null})

    def test_serialize_value_has_drop(self):
        from colander import drop
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        result = typ.serialize(node, {'a':drop})
        self.assertEqual(result, {})

    def test_flatten(self):
        node = DummySchemaNode(None, name='node')
        int1 = DummyType()
        int2 = DummyType()
        node.children = [
            DummySchemaNode(int1, name='a'),
            DummySchemaNode(int2, name='b'),
            ]
        typ = self._makeOne()
        result = typ.flatten(node, {'a':1, 'b':2})
        self.assertEqual(result, {'node.appstruct': 2})

    def test_flatten_listitem(self):
        node = DummySchemaNode(None, name='node')
        int1 = DummyType()
        int2 = DummyType()
        node.children = [
            DummySchemaNode(int1, name='a'),
            DummySchemaNode(int2, name='b'),
            ]
        typ = self._makeOne()
        result = typ.flatten(node, {'a':1, 'b':2}, listitem=True)
        self.assertEqual(result, {'appstruct': 2})

    def test_unflatten(self):
        node = DummySchemaNode(None, name='node')
        int1 = DummyType()
        int2 = DummyType()
        node.children = [
            DummySchemaNode(int1, name='a'),
            DummySchemaNode(int2, name='b'),
            ]
        typ = self._makeOne()
        result = typ.unflatten(node,
            ['node', 'node.a', 'node.b'],
            {'node': {'a':1, 'b':2}, 'node.a':1, 'node.b':2})
        self.assertEqual(result, {'a': 1, 'b': 2})

    def test_unflatten_nested(self):
        node = DummySchemaNode(None, name='node')
        inttype = DummyType()
        one = DummySchemaNode(self._makeOne(), name='one')
        one.children = [
            DummySchemaNode(inttype, name='a'),
            DummySchemaNode(inttype, name='b'),
        ]
        two = DummySchemaNode(self._makeOne(), name='two')
        two.children = [
            DummySchemaNode(inttype, name='c'),
            DummySchemaNode(inttype, name='d'),
        ]
        node.children = [one, two]
        typ = self._makeOne()
        result = typ.unflatten(
            node, ['node', 'node.one', 'node.one.a', 'node.one.b',
                   'node.two', 'node.two.c', 'node.two.d'],
            {'node': {'one': {'a': 1, 'b': 2}, 'two': {'c': 3, 'd': 4}},
             'node.one': {'a': 1, 'b': 2},
             'node.two': {'c': 3, 'd': 4},
             'node.one.a': 1,
             'node.one.b': 2,
             'node.two.c': 3,
             'node.two.d': 4,})
        self.assertEqual(result, {
            'one': {'a': 1, 'b': 2}, 'two': {'c': 3, 'd': 4}})

    def test_set_value(self):
        typ = self._makeOne()
        node1 = DummySchemaNode(typ, name='node1')
        node2 = DummySchemaNode(typ, name='node2')
        node1.children = [node2]
        appstruct = {'node2': {'foo': 'foo', 'baz': 'baz'}}
        typ.set_value(node1, appstruct, 'node2.foo', 'bar')
        self.assertEqual(appstruct, {'node2': {'foo': 'bar', 'baz': 'baz'}})

    def test_get_value(self):
        typ = self._makeOne()
        node1 = DummySchemaNode(typ, name='node1')
        node2 = DummySchemaNode(typ, name='node2')
        node1.children = [node2]
        appstruct = {'node2': {'foo': 'bar', 'baz': 'baz'}}
        self.assertEqual(typ.get_value(node1, appstruct, 'node2'),
                         {'foo': 'bar', 'baz': 'baz'})
        self.assertEqual(typ.get_value(node1, appstruct, 'node2.foo'), 'bar')

    def test_cstruct_children_cstruct_is_null(self):
        from colander import null
        typ = self._makeOne()
        node1 = DummySchemaNode(typ, name='node1')
        node2 = DummySchemaNode(typ, name='node2')
        node1.children = [node2]
        result = typ.cstruct_children(node1, null)
        self.assertEqual(result, [null])

    def test_cstruct_children(self):
        from colander import null
        typ = self._makeOne()
        node1 = DummySchemaNode(typ, name='node1')
        node2 = DummySchemaNode(typ, name='node2')
        node3 = DummySchemaNode(typ, name='node3')
        node1.children = [node2, node3]
        result = typ.cstruct_children(node1, {'node2':'abc'})
        self.assertEqual(result, ['abc', null])

class TestTuple(unittest.TestCase):
    def _makeOne(self):
        from colander import Tuple
        return Tuple()

    def test_deserialize_not_iterable(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, None)
        self.assertEqual(
            e.msg.interpolate(),
            '"None" is not iterable')
        self.assertEqual(e.node, node)

    def test_deserialize_no_subnodes(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, ())
        self.assertEqual(result, ())

    def test_deserialize_null(self):
        import colander
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, colander.null)
        self.assertEqual(result, colander.null)

    def test_deserialize_ok(self):
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        result = typ.deserialize(node, ('a',))
        self.assertEqual(result, ('a',))

    def test_deserialize_toobig(self):
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, ('a','b'))
        self.assertEqual(e.msg.interpolate(),
      "\"('a', 'b')\" has an incorrect number of elements (expected 1, was 2)")

    def test_deserialize_toosmall(self):
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, ())
        self.assertEqual(e.msg.interpolate(),
           '"()" has an incorrect number of elements (expected 1, was 0)')

    def test_deserialize_subnodes_raise(self):
        node = DummySchemaNode(None)
        node.children = [
            DummySchemaNode(None, name='a', exc='Wrong 2'),
            DummySchemaNode(None, name='b', exc='Wrong 2'),
            ]
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, ('1', '2'))
        self.assertEqual(e.msg, None)
        self.assertEqual(len(e.children), 2)

    def test_serialize_null(self):
        import colander
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, colander.null)
        self.assertEqual(result, colander.null)

    def test_serialize_not_iterable(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, node, None)
        self.assertEqual(
            e.msg.interpolate(),
            '"None" is not iterable')
        self.assertEqual(e.node, node)

    def test_serialize_no_subnodes(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, ())
        self.assertEqual(result, ())

    def test_serialize_ok(self):
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        result = typ.serialize(node, ('a',))
        self.assertEqual(result, ('a',))

    def test_serialize_toobig(self):
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, node, ('a','b'))
        self.assertEqual(e.msg.interpolate(),
     "\"('a', 'b')\" has an incorrect number of elements (expected 1, was 2)")

    def test_serialize_toosmall(self):
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, node, ())
        self.assertEqual(e.msg.interpolate(),
           '"()" has an incorrect number of elements (expected 1, was 0)'
           )

    def test_serialize_subnodes_raise(self):
        node = DummySchemaNode(None)
        node.children = [
            DummySchemaNode(None, name='a', exc='Wrong 2'),
            DummySchemaNode(None, name='b', exc='Wrong 2'),
            ]
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, node, ('1', '2'))
        self.assertEqual(e.msg, None)
        self.assertEqual(len(e.children), 2)

    def test_flatten(self):
        node = DummySchemaNode(None, name='node')
        int1 = DummyType()
        int2 = DummyType()
        node.children = [
            DummySchemaNode(int1, name='a'),
            DummySchemaNode(int2, name='b'),
            ]
        typ = self._makeOne()
        result = typ.flatten(node, (1, 2))
        self.assertEqual(result, {'node.appstruct': 2})

    def test_flatten_listitem(self):
        node = DummySchemaNode(None, name='node')
        int1 = DummyType()
        int2 = DummyType()
        node.children = [
            DummySchemaNode(int1, name='a'),
            DummySchemaNode(int2, name='b'),
            ]
        typ = self._makeOne()
        result = typ.flatten(node, (1, 2), listitem=True)
        self.assertEqual(result, {'appstruct': 2})

    def test_unflatten(self):
        node = DummySchemaNode(None, name='node')
        int1 = DummyType()
        int2 = DummyType()
        node.children = [
            DummySchemaNode(int1, name='a'),
            DummySchemaNode(int2, name='b'),
            ]
        typ = self._makeOne()
        result = typ.unflatten(node, ['node', 'node.a', 'node.b'],
                               {'node': (1, 2), 'node.a': 1, 'node.b': 2})
        self.assertEqual(result, (1, 2))

    def test_set_value(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ, name='node')
        node.children = [
            DummySchemaNode(typ, name='foo'),
            DummySchemaNode(typ, name='bar')
        ]
        node['foo'].children = [
            DummySchemaNode(None, name='a'),
            DummySchemaNode(None, name='b'),
        ]
        node['bar'].children = [
            DummySchemaNode(None, name='c'),
            DummySchemaNode(None, name='d'),
        ]
        appstruct = ((1, 2), (3, 4))
        result = typ.set_value(node, appstruct, 'bar.c', 34)
        self.assertEqual(result, ((1, 2), (34, 4)))

    def test_set_value_bad_path(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ, name='node')
        node.children = [
            DummySchemaNode(None, name='foo'),
            DummySchemaNode(None, name='bar')
        ]
        self.assertRaises(
            KeyError, typ.set_value, node, (1, 2), 'foobar', 34)

    def test_get_value(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ, name='node')
        node.children = [
            DummySchemaNode(typ, name='foo'),
            DummySchemaNode(typ, name='bar')
        ]
        node['foo'].children = [
            DummySchemaNode(None, name='a'),
            DummySchemaNode(None, name='b'),
        ]
        node['bar'].children = [
            DummySchemaNode(None, name='c'),
            DummySchemaNode(None, name='d'),
        ]
        appstruct = ((1, 2), (3, 4))
        self.assertEqual(typ.get_value(node, appstruct, 'foo'), (1, 2))
        self.assertEqual(typ.get_value(node, appstruct, 'foo.b'), 2)

    def test_get_value_bad_path(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ, name='node')
        node.children = [
            DummySchemaNode(None, name='foo'),
            DummySchemaNode(None, name='bar')
        ]
        self.assertRaises(
            KeyError, typ.get_value, node, (1, 2), 'foobar')

    def test_cstruct_children_cstruct_is_null(self):
        from colander import null
        typ = self._makeOne()
        node1 = DummySchemaNode(typ, name='node1')
        node2 = DummySchemaNode(typ, name='node2')
        node1.children = [node2]
        result = typ.cstruct_children(node1, null)
        self.assertEqual(result, [null])

    def test_cstruct_children_toomany(self):
        typ = self._makeOne()
        node1 = DummySchemaNode(typ, name='node1')
        node2 = DummySchemaNode(typ, name='node2')
        node3 = DummySchemaNode(typ, name='node3')
        node1.children = [node2, node3]
        result = typ.cstruct_children(node1, ['one', 'two', 'three'])
        self.assertEqual(result, ['one', 'two'])

    def test_cstruct_children_toofew(self):
        from colander import null
        typ = self._makeOne()
        node1 = DummySchemaNode(typ, name='node1')
        node2 = DummySchemaNode(typ, name='node2')
        node3 = DummySchemaNode(typ, name='node3')
        node1.children = [node2, node3]
        result = typ.cstruct_children(node1, ['one'])
        self.assertEqual(result, ['one', null])

    def test_cstruct_children_justright(self):
        typ = self._makeOne()
        node1 = DummySchemaNode(typ, name='node1')
        node2 = DummySchemaNode(typ, name='node2')
        node3 = DummySchemaNode(typ, name='node3')
        node1.children = [node2, node3]
        result = typ.cstruct_children(node1, ['one', 'two'])
        self.assertEqual(result, ['one', 'two'])


class TestSet(unittest.TestCase):
    def _makeOne(self, **kw):
        from colander import Set
        return Set(**kw)

    def test_serialize(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        provided = []
        result = typ.serialize(node, provided)
        self.assertTrue(result is provided)

    def test_serialize_null(self):
        from colander import null
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        result = typ.serialize(node, null)
        self.assertTrue(result is null)

    def test_deserialize_no_iter(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        e = invalid_exc(typ.deserialize, node, 1)
        self.assertEqual(e.msg, '${cstruct} is not iterable')

    def test_deserialize_str_no_iter(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        e = invalid_exc(typ.deserialize, node, "foo")
        self.assertEqual(e.msg, '${cstruct} is not iterable')

    def test_deserialize_null(self):
        from colander import null
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        result = typ.deserialize(node, null)
        self.assertEqual(result, null)

    def test_deserialize_valid(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        result = typ.deserialize(node, ('a',))
        self.assertEqual(result, set(('a',)))

    def test_deserialize_empty_set(self):
        import colander
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        result = typ.deserialize(node, set())
        self.assertEqual(result, set())


class TestList(unittest.TestCase):
    def _makeOne(self, **kw):
        from colander import List
        return List(**kw)

    def test_serialize(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        provided = []
        result = typ.serialize(node, provided)
        self.assertTrue(result is provided)

    def test_serialize_null(self):
        from colander import null
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        result = typ.serialize(node, null)
        self.assertTrue(result is null)

    def test_deserialize_no_iter(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        e = invalid_exc(typ.deserialize, node, 1)
        self.assertEqual(e.msg, '${cstruct} is not iterable')

    def test_deserialize_str_no_iter(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        e = invalid_exc(typ.deserialize, node, "foo")
        self.assertEqual(e.msg, '${cstruct} is not iterable')

    def test_deserialize_null(self):
        from colander import null
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        result = typ.deserialize(node, null)
        self.assertEqual(result, null)

    def test_deserialize_valid(self):
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        result = typ.deserialize(node, ('a', 'z', 'b'))
        self.assertEqual(result, ['a', 'z', 'b'])

    def test_deserialize_empty_set(self):
        import colander
        typ = self._makeOne()
        node = DummySchemaNode(typ)
        result = typ.deserialize(node, ())
        self.assertEqual(result, [])

class TestSequence(unittest.TestCase):
    def _makeOne(self, **kw):
        from colander import Sequence
        return Sequence(**kw)

    def test_alias(self):
        from colander import Seq
        from colander import Sequence
        self.assertEqual(Seq, Sequence)

    def test_deserialize_not_iterable(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        node.children = [node]
        e = invalid_exc(typ.deserialize, node, None)
        self.assertEqual(
            e.msg.interpolate(),
            '"None" is not iterable')
        self.assertEqual(e.node, node)

    def test_deserialize_not_iterable_accept_scalar(self):
        node = DummySchemaNode(None)
        typ = self._makeOne(accept_scalar=True)
        node.children = [node]
        result = typ.deserialize(node, None)
        self.assertEqual(result, [None])

    def test_deserialize_string_accept_scalar(self):
        node = DummySchemaNode(None)
        typ = self._makeOne(accept_scalar=True)
        node.children = [node]
        result = typ.deserialize(node, 'abc')
        self.assertEqual(result, ['abc'])

    def test_deserialize_no_subnodes(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        node.children = [node]
        result = typ.deserialize(node, ())
        self.assertEqual(result, [])

    def test_deserialize_no_null(self):
        import colander
        typ = self._makeOne()
        result = typ.deserialize(None, colander.null)
        self.assertEqual(result, colander.null)

    def test_deserialize_ok(self):
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        node.children = [node]
        result = typ.deserialize(node, ('a',))
        self.assertEqual(result, ['a'])

    def test_deserialize_subnodes_raise(self):
        node = DummySchemaNode(None, exc='Wrong')
        typ = self._makeOne()
        node.children = [node]
        e = invalid_exc(typ.deserialize, node, ('1', '2'))
        self.assertEqual(e.msg, None)
        self.assertEqual(len(e.children), 2)

    def test_serialize_null(self):
        import colander
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, colander.null)
        self.assertEqual(result, colander.null)

    def test_serialize_drop(self):
        from colander import drop
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        result = typ.serialize(node, (drop,))
        self.assertEqual(result, [])

    def test_serialize_not_iterable(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        node.children = [node]
        e = invalid_exc(typ.serialize, node, None)
        self.assertEqual(
            e.msg.interpolate(),
            '"None" is not iterable')
        self.assertEqual(e.node, node)

    def test_serialize_not_iterable_accept_scalar(self):
        node = DummySchemaNode(None)
        typ = self._makeOne(accept_scalar=True)
        node.children = [node]
        result = typ.serialize(node, None)
        self.assertEqual(result, [None])

    def test_serialize_string_accept_scalar(self):
        node = DummySchemaNode(None)
        typ = self._makeOne(accept_scalar=True)
        node.children = [node]
        result = typ.serialize(node, 'abc')
        self.assertEqual(result, ['abc'])

    def test_serialize_no_subnodes(self):
        node = DummySchemaNode(None)
        node.children = [node]
        typ = self._makeOne()
        result = typ.serialize(node, ())
        self.assertEqual(result, [])

    def test_serialize_ok(self):
        node = DummySchemaNode(None)
        node.children = [DummySchemaNode(None, name='a')]
        typ = self._makeOne()
        result = typ.serialize(node, ('a',))
        self.assertEqual(result, ['a'])

    def test_serialize_subnodes_raise(self):
        node = DummySchemaNode(None, exc='Wrong')
        typ = self._makeOne()
        node.children = [node]
        e = invalid_exc(typ.serialize, node, ('1', '2'))
        self.assertEqual(e.msg, None)
        self.assertEqual(len(e.children), 2)

    def test_flatten(self):
        node = DummySchemaNode(None, name='node')
        node.children = [
            DummySchemaNode(DummyType(), name='foo'),
        ]
        typ = self._makeOne()
        result = typ.flatten(node, [1, 2])
        self.assertEqual(result, {'node.0': 1, 'node.1': 2})

    def test_flatten_with_integer(self):
        from colander import Integer
        node = DummySchemaNode(None, name='node')
        node.children = [
            DummySchemaNode(Integer(), name='foo'),
        ]
        typ = self._makeOne()
        result = typ.flatten(node, [1, 2])
        self.assertEqual(result, {'node.0': 1, 'node.1': 2})

    def test_flatten_listitem(self):
        node = DummySchemaNode(None, name='node')
        node.children = [
            DummySchemaNode(DummyType(), name='foo'),
        ]
        typ = self._makeOne()
        result = typ.flatten(node, [1, 2], listitem=True)
        self.assertEqual(result, {'0': 1, '1': 2})

    def test_unflatten(self):
        node = DummySchemaNode(None, name='node')
        node.children = [
            DummySchemaNode(DummyType(), name='foo'),
        ]
        typ = self._makeOne()
        result = typ.unflatten(node,
            ['node.0', 'node.1',],
            {'node.0': 'a', 'node.1': 'b'})
        self.assertEqual(result, ['a', 'b'])

    def test_setvalue(self):
        typ = self._makeOne()
        node1 = DummySchemaNode(typ, name='seq1')
        node2 = DummySchemaNode(typ, name='seq2')
        node1.children = [node2]
        node2.children = DummySchemaNode(None, name='items')
        appstruct = [[1, 2], [3, 4]]
        typ.set_value(node1, appstruct, '1.0', 34)
        self.assertEqual(appstruct, [[1, 2], [34, 4]])

    def test_getvalue(self):
        typ = self._makeOne()
        node1 = DummySchemaNode(typ, name='seq1')
        node2 = DummySchemaNode(typ, name='seq2')
        node1.children = [node2]
        node2.children = DummySchemaNode(None, name='items')
        appstruct = [[1, 2], [3, 4]]
        self.assertEqual(typ.get_value(node1, appstruct, '1'), [3, 4])
        self.assertEqual(typ.get_value(node1, appstruct, '1.0'), 3)

    def test_cstruct_children_cstruct_is_null(self):
        from colander import null
        from colander import SequenceItems
        typ = self._makeOne()
        result = typ.cstruct_children(None, null)
        self.assertEqual(result, SequenceItems([]))

    def test_cstruct_children_cstruct_is_non_null(self):
        from colander import SequenceItems
        typ = self._makeOne()
        result = typ.cstruct_children(None, ['a'])
        self.assertEqual(result, SequenceItems(['a']))

class TestString(unittest.TestCase):
    def _makeOne(self, encoding=None, allow_empty=False):
        from colander import String
        return String(encoding, allow_empty)

    def test_alias(self):
        from colander import Str
        from colander import String
        self.assertEqual(Str, String)

    def test_deserialize_emptystring(self):
        from colander import null
        node = DummySchemaNode(None)
        typ = self._makeOne(None)
        result = typ.deserialize(node, '')
        self.assertEqual(result, null)
        typ = self._makeOne(None, allow_empty=True)
        result = typ.deserialize(node, '')
        self.assertEqual(result, '')

    def test_deserialize_uncooperative(self):
        val = Uncooperative()
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, val)
        self.assertTrue(e.msg)

    def test_deserialize_unicode_from_None(self):
        uni = text_(b'\xe3\x81\x82', 'utf-8')
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, uni)
        self.assertEqual(result, uni)

    def test_deserialize_nonunicode_from_None(self):
        import colander
        value = object()
        node = DummySchemaNode(None)
        typ = self._makeOne()
        self.assertRaises(colander.Invalid, typ.deserialize, node, value)

    def test_deserialize_from_utf8(self):
        uni = text_(b'\xe3\x81\x82', encoding='utf-8')
        utf8 = uni.encode('utf-8')
        node = DummySchemaNode(None)
        typ = self._makeOne('utf-8')
        result = typ.deserialize(node, utf8)
        self.assertEqual(result, uni)

    def test_deserialize_from_utf16(self):
        uni = text_(b'\xe3\x81\x82', encoding='utf-8')
        utf16 = uni.encode('utf-16')
        node = DummySchemaNode(None)
        typ = self._makeOne('utf-16')
        result = typ.deserialize(node, utf16)
        self.assertEqual(result, uni)

    def test_deserialize_from_nonstring_obj(self):
        import colander
        value = object()
        node = DummySchemaNode(None)
        typ = self._makeOne()
        self.assertRaises(colander.Invalid, typ.deserialize, node, value)

    def test_serialize_null(self):
        from colander import null
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, null)
        self.assertEqual(result, null)

    def test_serialize_emptystring(self):
        val = ''
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, val)

    def test_serialize_uncooperative(self):
        val = Uncooperative()
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, node, val)
        self.assertTrue(e.msg)

    def test_serialize_nonunicode_to_None(self):
        value = object()
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, value)
        self.assertEqual(result, text_type(value))

    def test_serialize_unicode_to_None(self):
        value = text_('abc')
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, value)
        self.assertEqual(result, value)

    def test_serialize_to_utf8(self):
        uni = text_(b'\xe3\x81\x82', encoding='utf-8')
        utf8 = uni.encode('utf-8')
        node = DummySchemaNode(None)
        typ = self._makeOne('utf-8')
        result = typ.serialize(node, uni)
        self.assertEqual(result, utf8)

    def test_serialize_to_utf16(self):
        uni = text_(b'\xe3\x81\x82', encoding='utf-8')
        utf16 = uni.encode('utf-16')
        node = DummySchemaNode(None)
        typ = self._makeOne('utf-16')
        result = typ.serialize(node, uni)
        self.assertEqual(result, utf16)

    def test_serialize_string_with_high_unresolveable_high_order_chars(self):
        not_utf8 = b'\xff\xfe\xf8\x00'
        node = DummySchemaNode(None)
        typ = self._makeOne('utf-8')
        e = invalid_exc(typ.serialize, node, not_utf8)
        self.assertTrue('cannot be serialized' in e.msg)

    def test_serialize_encoding_with_non_string_type(self):
        utf8 = text_type('123').encode('utf-8')
        node = DummySchemaNode(None)
        typ = self._makeOne('utf-8')
        result = typ.serialize(node, 123)
        self.assertEqual(result, utf8)

class TestInteger(unittest.TestCase):
    def _makeOne(self):
        from colander import Integer
        return Integer()

    def test_alias(self):
        from colander import Int
        from colander import Integer
        self.assertEqual(Int, Integer)

    def test_serialize_null(self):
        import colander
        val = colander.null
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, colander.null)

    def test_deserialize_emptystring(self):
        import colander
        val = ''
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, val)
        self.assertEqual(result, colander.null)

    def test_deserialize_fails(self):
        val = 'P'
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, val)
        self.assertTrue(e.msg)

    def test_deserialize_ok(self):
        val = '1'
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, val)
        self.assertEqual(result, 1)

    def test_serialize_fails(self):
        val = 'P'
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, node, val)
        self.assertTrue(e.msg)

    def test_serialize_ok(self):
        val = 1
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, '1')

    def test_serialize_zero(self):
        val = 0
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, '0')

class TestFloat(unittest.TestCase):
    def _makeOne(self):
        from colander import Float
        return Float()

    def test_serialize_null(self):
        import colander
        val = colander.null
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, colander.null)

    def test_serialize_emptystring(self):
        import colander
        val = ''
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, val)
        self.assertEqual(result, colander.null)

    def test_deserialize_fails(self):
        val = 'P'
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, val)
        self.assertTrue(e.msg)

    def test_deserialize_ok(self):
        val = '1.0'
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, val)
        self.assertEqual(result, 1.0)

    def test_serialize_fails(self):
        val = 'P'
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, node, val)
        self.assertTrue(e.msg)

    def test_serialize_ok(self):
        val = 1.0
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, '1.0')

class TestDecimal(unittest.TestCase):
    def _makeOne(self, quant=None, rounding=None, normalize=False):
        from colander import Decimal
        return Decimal(quant, rounding, normalize)

    def test_serialize_null(self):
        import colander
        val = colander.null
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, colander.null)

    def test_serialize_emptystring(self):
        import colander
        val = ''
        node = DummySchemaNode(None)
        typ = self._makeOne()
        self.assertRaises(colander.Invalid, typ.serialize, node, val)

    def test_serialize_quantize_no_rounding(self):
        val = '.000001'
        node = DummySchemaNode(None)
        typ = self._makeOne('.01')
        result = typ.serialize(node, val)
        self.assertEqual(result, '0.00')

    def test_serialize_quantize_with_rounding_up(self):
        import decimal
        val = '.000001'
        node = DummySchemaNode(None)
        typ = self._makeOne('.01', decimal.ROUND_UP)
        result = typ.serialize(node, val)
        self.assertEqual(result, '0.01')

    def test_serialize_normalize(self):
        from decimal import Decimal
        val = Decimal('1.00')
        node = DummySchemaNode(None)
        typ = self._makeOne(normalize=True)
        result = typ.serialize(node, val)
        self.assertEqual(result, '1')

    def test_deserialize_fails(self):
        val = 'P'
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, val)
        self.assertTrue(e.msg)

    def test_deserialize_ok(self):
        import decimal
        val = '1.0'
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, val)
        self.assertEqual(result, decimal.Decimal('1.0'))

    def test_deserialize_with_quantize(self):
        import decimal
        val = '1.00000001'
        node = DummySchemaNode(None)
        typ = self._makeOne('.01', decimal.ROUND_UP)
        result = typ.deserialize(node, val)
        self.assertEqual(result, decimal.Decimal('1.01'))

    def test_deserialize_with_normalize(self):
        from decimal import Decimal
        val = '1.00'
        node = DummySchemaNode(None)
        typ = self._makeOne(normalize=True)
        result = typ.deserialize(node, val)
        self.assertEqual(result, Decimal('1'))
        self.assertEqual(str(result), '1')

    def test_serialize_fails(self):
        val = 'P'
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, node, val)
        self.assertTrue(e.msg)

    def test_serialize_ok(self):
        val = 1.0
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, '1.0')

class TestMoney(unittest.TestCase):
    def _makeOne(self):
        from colander import Money
        return Money()

    def test_serialize_rounds_up(self):
        val = '1.000001'
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, '1.01')

    def test_deserialize_rounds_up(self):
        import decimal
        val = '1.00000001'
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, val)
        self.assertEqual(result, decimal.Decimal('1.01'))

class TestBoolean(unittest.TestCase):
    def _makeOne(self):
        from colander import Boolean
        return Boolean()

    def test_alias(self):
        from colander import Bool
        from colander import Boolean
        self.assertEqual(Bool, Boolean)

    def test_serialize_null(self):
        import colander
        val = colander.null
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, colander.null)

    def test_deserialize(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        self.assertEqual(typ.deserialize(node, 'false'), False)
        self.assertEqual(typ.deserialize(node, 'FALSE'), False)
        self.assertEqual(typ.deserialize(node, '0'), False)
        self.assertEqual(typ.deserialize(node, 'true'), True)
        self.assertEqual(typ.deserialize(node, 'other'), True)

    def test_deserialize_unstringable(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        e = invalid_exc(typ.deserialize, node, Uncooperative())
        self.assertTrue(e.msg.endswith('not a string'))

    def test_deserialize_null(self):
        import colander
        typ = self._makeOne()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, colander.null)
        self.assertEqual(result, colander.null)

    def test_serialize(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        self.assertEqual(typ.serialize(node, 1), 'true')
        self.assertEqual(typ.serialize(node, True), 'true')
        self.assertEqual(typ.serialize(node, None), 'false')
        self.assertEqual(typ.serialize(node, False), 'false')

class TestBooleanCustomFalseReprs(unittest.TestCase):
    def _makeOne(self):
        from colander import Boolean
        return Boolean(false_choices=('n','f'))

    def test_deserialize(self):
        import colander
        typ = self._makeOne()
        node = DummySchemaNode(None)
        self.assertEqual(typ.deserialize(node, 'f'), False)
        self.assertEqual(typ.deserialize(node, 'N'), False)
        self.assertEqual(typ.deserialize(node, 'other'), True)

class TestBooleanCustomFalseAndTrueReprs(unittest.TestCase):
    def _makeOne(self):
        from colander import Boolean
        return Boolean(false_choices=('n','f'), true_choices=('y','t'))

    def test_deserialize(self):
        import colander
        typ = self._makeOne()
        node = DummySchemaNode(None)
        self.assertEqual(typ.deserialize(node, 'f'), False)
        self.assertEqual(typ.deserialize(node, 'N'), False)
        self.assertEqual(typ.deserialize(node, 'T'), True)
        self.assertEqual(typ.deserialize(node, 'y'), True)
        self.assertRaises(colander.Invalid, typ.deserialize, node, 'other')
        try:
            _val = typ.deserialize(node, 'other')
        except colander.Invalid as exc:
            self.assertEqual(exc.msg.mapping['false_choices'], "'n', 'f'")
            self.assertEqual(exc.msg.mapping['true_choices'], "'y', 't'")

class TestBooleanCustomSerializations(unittest.TestCase):
    def _makeOne(self):
        from colander import Boolean
        return Boolean(false_val='no', true_val='yes')

    def test_serialize(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        self.assertEqual(typ.serialize(node, 1), 'yes')
        self.assertEqual(typ.serialize(node, True), 'yes')
        self.assertEqual(typ.serialize(node, None), 'no')
        self.assertEqual(typ.serialize(node, False), 'no')

class TestGlobalObject(unittest.TestCase):
    def _makeOne(self, package=None):
        from colander import GlobalObject
        return GlobalObject(package)

    def test_zope_dottedname_style_resolve_absolute(self):
        typ = self._makeOne()
        result = typ._zope_dottedname_style(None,
            'colander.tests.test_colander.TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test_zope_dottedname_style_irrresolveable_absolute(self):
        typ = self._makeOne()
        self.assertRaises(ImportError, typ._zope_dottedname_style, None,
            'colander.tests.nonexisting')

    def test__zope_dottedname_style_resolve_relative(self):
        import colander
        typ = self._makeOne(package=colander)
        node = DummySchemaNode(None)
        result = typ._zope_dottedname_style(
            node,
            '.tests.test_colander.TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test__zope_dottedname_style_resolve_relative_leading_dots(self):
        import colander
        typ = self._makeOne(package=colander.tests)
        node = DummySchemaNode(None)
        result = typ._zope_dottedname_style(
            node,
            '..tests.test_colander.TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test__zope_dottedname_style_resolve_relative_is_dot(self):
        import colander.tests
        typ = self._makeOne(package=colander.tests)
        result = typ._zope_dottedname_style(None, '.')
        self.assertEqual(result, colander.tests)

    def test__zope_dottedname_style_irresolveable_relative_is_dot(self):
        typ = self._makeOne()
        e = invalid_exc(typ._zope_dottedname_style, None, '.')
        self.assertEqual(
            e.msg.interpolate(),
            'relative name "." irresolveable without package')

    def test_zope_dottedname_style_resolve_relative_nocurrentpackage(self):
        typ = self._makeOne()
        e = invalid_exc(typ._zope_dottedname_style, None, '.whatever')
        self.assertEqual(
            e.msg.interpolate(),
            'relative name ".whatever" irresolveable without package')

    def test_zope_dottedname_style_irrresolveable_relative(self):
        import colander.tests
        typ = self._makeOne(package=colander)
        self.assertRaises(ImportError, typ._zope_dottedname_style, None,
                          '.notexisting')

    def test__zope_dottedname_style_resolveable_relative(self):
        import colander
        typ = self._makeOne(package=colander)
        result = typ._zope_dottedname_style(None, '.tests')
        from colander import tests
        self.assertEqual(result, tests)

    def test__zope_dottedname_style_irresolveable_absolute(self):
        typ = self._makeOne()
        self.assertRaises(
            ImportError,
            typ._zope_dottedname_style, None, 'colander.fudge.bar')

    def test__zope_dottedname_style_resolveable_absolute(self):
        typ = self._makeOne()
        result = typ._zope_dottedname_style(
            None,
            'colander.tests.test_colander.TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test__pkg_resources_style_resolve_absolute(self):
        typ = self._makeOne()
        result = typ._pkg_resources_style(None,
            'colander.tests.test_colander:TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test__pkg_resources_style_irrresolveable_absolute(self):
        typ = self._makeOne()
        self.assertRaises(ImportError, typ._pkg_resources_style, None,
            'colander.tests.test_colander:nonexisting')

    def test__pkg_resources_style_resolve_relative_startswith_colon(self):
        import colander.tests
        typ = self._makeOne(package=colander.tests)
        result = typ._pkg_resources_style(None, ':fixture')
        self.assertEqual(result, 1)

    def test__pkg_resources_style_resolve_relative_startswith_dot(self):
        import colander
        typ = self._makeOne(package=colander)
        result = typ._pkg_resources_style(
            None,
            '.tests.test_colander:TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test__pkg_resources_style_resolve_relative_is_dot(self):
        import colander.tests
        typ = self._makeOne(package=colander.tests)
        result = typ._pkg_resources_style(None, '.')
        self.assertEqual(result, colander.tests)

    def test__pkg_resources_style_resolve_relative_nocurrentpackage(self):
        typ = self._makeOne()
        import colander
        self.assertRaises(colander.Invalid, typ._pkg_resources_style, None,
                          '.whatever')

    def test__pkg_resources_style_irrresolveable_relative(self):
        import colander.tests
        typ = self._makeOne(package=colander)
        self.assertRaises(ImportError, typ._pkg_resources_style, None,
                          ':notexisting')

    def test_deserialize_None(self):
        import colander
        typ = self._makeOne()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, None)
        self.assertEqual(result, colander.null)

    def test_deserialize_null(self):
        import colander
        typ = self._makeOne()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, colander.null)
        self.assertEqual(result, colander.null)

    def test_deserialize_notastring(self):
        import colander
        typ = self._makeOne()
        node = DummySchemaNode(None)
        self.assertRaises(colander.Invalid, typ.deserialize, node, True)

    def test_deserialize_using_pkgresources_style(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        result = typ.deserialize(
            node,
            'colander.tests.test_colander:TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test_deserialize_using_zope_dottedname_style(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        result = typ.deserialize(
            node,
            'colander.tests.test_colander.TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test_deserialize_style_raises(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        e = invalid_exc(typ.deserialize, node, 'cant.be.found')
        self.assertEqual(e.msg.interpolate(),
                         'The dotted name "cant.be.found" cannot be imported')

    def test_serialize_null(self):
        import colander
        val = colander.null
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, colander.null)

    def test_serialize_ok(self):
        import colander.tests
        typ = self._makeOne()
        node = DummySchemaNode(None)
        result = typ.serialize(node, colander.tests)
        self.assertEqual(result, 'colander.tests')

    def test_serialize_fail(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        e = invalid_exc(typ.serialize, node, None)
        self.assertEqual(e.msg.interpolate(), '"None" has no __name__')

class TestDateTime(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from colander import DateTime
        return DateTime(*arg, **kw)

    def _dt(self):
        import datetime
        return datetime.datetime(2010, 4, 26, 10, 48)

    def _today(self):
        import datetime
        return datetime.date.today()

    def test_ctor_default_tzinfo_not_specified(self):
        from .. import iso8601
        typ = self._makeOne()
        self.assertEqual(typ.default_tzinfo.__class__, iso8601.Utc)

    def test_ctor_default_tzinfo_None(self):
        typ = self._makeOne(default_tzinfo=None)
        self.assertEqual(typ.default_tzinfo, None)

    def test_ctor_default_tzinfo_non_None(self):
        from .. import iso8601
        tzinfo = iso8601.FixedOffset(1, 0, 'myname')
        typ = self._makeOne(default_tzinfo=tzinfo)
        self.assertEqual(typ.default_tzinfo, tzinfo)

    def test_serialize_null(self):
        import colander
        val = colander.null
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, colander.null)

    def test_serialize_none(self):
        import colander
        val = None
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, colander.null)

    def test_serialize_with_garbage(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        e = invalid_exc(typ.serialize, node, 'garbage')
        self.assertEqual(e.msg.interpolate(),
                         '"garbage" is not a datetime object')

    def test_serialize_with_date(self):
        import datetime
        typ = self._makeOne()
        date = self._today()
        node = DummySchemaNode(None)
        result = typ.serialize(node, date)
        expected = datetime.datetime.combine(date, datetime.time())
        expected = expected.replace(tzinfo=typ.default_tzinfo).isoformat()
        self.assertEqual(result, expected)

    def test_serialize_with_naive_datetime(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        dt = self._dt()
        result = typ.serialize(node, dt)
        expected = dt.replace(tzinfo=typ.default_tzinfo).isoformat()
        self.assertEqual(result, expected)

    def test_serialize_with_none_tzinfo_naive_datetime(self):
        typ = self._makeOne(default_tzinfo=None)
        node = DummySchemaNode(None)
        dt = self._dt()
        result = typ.serialize(node, dt)
        self.assertEqual(result, dt.isoformat())

    def test_serialize_with_tzware_datetime(self):
        from .. import iso8601
        typ = self._makeOne()
        dt = self._dt()
        tzinfo = iso8601.FixedOffset(1, 0, 'myname')
        dt = dt.replace(tzinfo=tzinfo)
        node = DummySchemaNode(None)
        result = typ.serialize(node, dt)
        expected = dt.isoformat()
        self.assertEqual(result, expected)

    def test_deserialize_date(self):
        import datetime
        from .. import iso8601
        date = self._today()
        typ = self._makeOne()
        formatted = date.isoformat()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, formatted)
        expected = datetime.datetime.combine(result, datetime.time())
        tzinfo = iso8601.Utc()
        expected = expected.replace(tzinfo=tzinfo)
        self.assertEqual(result.isoformat(), expected.isoformat())

    def test_deserialize_invalid_ParseError(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, 'garbage')
        self.assertTrue('Invalid' in e.msg)

    def test_deserialize_slashes_invalid(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, '2013/05/31')
        self.assertTrue('Invalid' in e.msg)

    def test_deserialize_null(self):
        import colander
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, colander.null)
        self.assertEqual(result, colander.null)

    def test_deserialize_empty(self):
        import colander
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, '')
        self.assertEqual(result, colander.null)

    def test_deserialize_success(self):
        from .. import iso8601
        typ = self._makeOne()
        dt = self._dt()
        tzinfo = iso8601.FixedOffset(1, 0, 'myname')
        dt = dt.replace(tzinfo=tzinfo)
        iso = dt.isoformat()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, iso)
        self.assertEqual(result.isoformat(), iso)

    def test_deserialize_naive_with_default_tzinfo(self):
        from .. import iso8601
        tzinfo = iso8601.FixedOffset(1, 0, 'myname')
        typ = self._makeOne(default_tzinfo=tzinfo)
        dt = self._dt()
        dt_with_tz = dt.replace(tzinfo=tzinfo)
        iso = dt.isoformat()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, iso)
        self.assertEqual(result.isoformat(), dt_with_tz.isoformat())

    def test_deserialize_none_tzinfo(self):
        typ = self._makeOne(default_tzinfo=None)
        dt = self._dt()
        iso = dt.isoformat()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, iso)
        self.assertEqual(result.isoformat(), dt.isoformat())
        self.assertEqual(result.tzinfo, None)

class TestDate(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from colander import Date
        return Date(*arg, **kw)

    def _dt(self):
        import datetime
        return datetime.datetime(2010, 4, 26, 10, 48)

    def _today(self):
        import datetime
        return datetime.date.today()

    def test_serialize_null(self):
        import colander
        val = colander.null
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, colander.null)

    def test_serialize_none(self):
        import colander
        val = None
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, colander.null)

    def test_serialize_with_garbage(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        e = invalid_exc(typ.serialize, node, 'garbage')
        self.assertEqual(e.msg.interpolate(), '"garbage" is not a date object')

    def test_serialize_with_date(self):
        typ = self._makeOne()
        date = self._today()
        node = DummySchemaNode(None)
        result = typ.serialize(node, date)
        expected = date.isoformat()
        self.assertEqual(result, expected)

    def test_serialize_with_datetime(self):
        typ = self._makeOne()
        dt = self._dt()
        node = DummySchemaNode(None)
        result = typ.serialize(node, dt)
        expected = dt.date().isoformat()
        self.assertEqual(result, expected)

    def test_deserialize_invalid_ParseError(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, 'garbage')
        self.assertTrue('Invalid' in e.msg)

    def test_deserialize_invalid_weird(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, '10-10-10-10')
        self.assertTrue('Invalid' in e.msg)

    def test_deserialize_null(self):
        import colander
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, colander.null)
        self.assertEqual(result, colander.null)

    def test_deserialize_empty(self):
        import colander
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, '')
        self.assertEqual(result, colander.null)

    def test_deserialize_success_date(self):
        typ = self._makeOne()
        date = self._today()
        iso = date.isoformat()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, iso)
        self.assertEqual(result.isoformat(), iso)

    def test_deserialize_success_datetime(self):
        dt = self._dt()
        typ = self._makeOne()
        iso = dt.isoformat()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, iso)
        self.assertEqual(result.isoformat(), dt.date().isoformat())

class TestTime(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from colander import Time
        return Time(*arg, **kw)

    def _dt(self):
        import datetime
        return datetime.datetime(2010, 4, 26, 10, 48)

    def _now(self):
        import datetime
        return datetime.datetime.now().time()

    def test_serialize_null(self):
        import colander
        val = colander.null
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, colander.null)

    def test_serialize_none(self):
        import colander
        val = None
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.serialize(node, val)
        self.assertEqual(result, colander.null)

    def test_serialize_with_garbage(self):
        typ = self._makeOne()
        node = DummySchemaNode(None)
        e = invalid_exc(typ.serialize, node, 'garbage')
        self.assertEqual(e.msg.interpolate(), '"garbage" is not a time object')

    def test_serialize_with_time(self):
        typ = self._makeOne()
        time = self._now()
        node = DummySchemaNode(None)
        result = typ.serialize(node, time)
        expected = time.isoformat().split('.')[0]
        self.assertEqual(result, expected)

    def test_serialize_with_zero_time(self):
        import datetime
        typ = self._makeOne()
        time = datetime.time(0)
        node = DummySchemaNode(None)
        result = typ.serialize(node, time)
        expected = time.isoformat().split('.')[0]
        self.assertEqual(result, expected)

    def test_serialize_with_datetime(self):
        typ = self._makeOne()
        dt = self._dt()
        node = DummySchemaNode(None)
        result = typ.serialize(node, dt)
        expected = dt.time().isoformat().split('.')[0]
        self.assertEqual(result, expected)

    def test_deserialize_invalid_ParseError(self):
        node = DummySchemaNode(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, node, 'garbage')
        self.assertTrue('Invalid' in e.msg)

    def test_deserialize_three_digit_string(self):
        import datetime
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, '11:00:11')
        self.assertEqual(result, datetime.time(11, 0, 11))

    def test_deserialize_two_digit_string(self):
        import datetime
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, '11:00')
        self.assertEqual(result, datetime.time(11, 0))

    def test_deserialize_null(self):
        import colander
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, colander.null)
        self.assertEqual(result, colander.null)

    def test_deserialize_empty(self):
        import colander
        node = DummySchemaNode(None)
        typ = self._makeOne()
        result = typ.deserialize(node, '')
        self.assertEqual(result, colander.null)

    def test_deserialize_missing_seconds(self):
        import datetime
        typ = self._makeOne()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, '10:12')
        self.assertEqual(result, datetime.time(10, 12))

    def test_deserialize_success_time(self):
        import datetime
        typ = self._makeOne()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, '10:12:13')
        self.assertEqual(result, datetime.time(10, 12, 13))

    def test_deserialize_success_datetime(self):
        dt = self._dt()
        typ = self._makeOne()
        iso = dt.isoformat()
        node = DummySchemaNode(None)
        result = typ.deserialize(node, iso)
        self.assertEqual(result.isoformat(),
                dt.time().isoformat().split('.')[0])

class TestSchemaNode(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from colander import SchemaNode
        return SchemaNode(*arg, **kw)

    def test_new_sets_order(self):
        node = self._makeOne(None)
        self.assertTrue(hasattr(node, '_order'))

    def test_ctor_no_title(self):
        child = DummySchemaNode(None, name='fred')
        node = self._makeOne(
            None, child, validator=1, default=2,
            name='name_a', missing='missing')
        self.assertEqual(node.typ, None)
        self.assertEqual(node.children, [child])
        self.assertEqual(node.validator, 1)
        self.assertEqual(node.default, 2)
        self.assertEqual(node.missing, 'missing')
        self.assertEqual(node.name, 'name_a')
        self.assertEqual(node.title, 'Name A')

    def test_ctor_with_title(self):
        child = DummySchemaNode(None, name='fred')
        node = self._makeOne(None, child, validator=1, default=2, name='name',
                             title='title')
        self.assertEqual(node.typ, None)
        self.assertEqual(node.children, [child])
        self.assertEqual(node.validator, 1)
        self.assertEqual(node.default, 2)
        self.assertEqual(node.name, 'name')
        self.assertEqual(node.title, 'title')

    def test_ctor_with_description(self):
        node = self._makeOne(None, validator=1, default=2, name='name',
                             title='title', description='desc')
        self.assertEqual(node.description, 'desc')

    def test_ctor_with_widget(self):
        node = self._makeOne(None, widget='abc')
        self.assertEqual(node.widget, 'abc')

    def test_ctor_with_preparer(self):
        node = self._makeOne(None, preparer='abc')
        self.assertEqual(node.preparer, 'abc')

    def test_ctor_without_preparer(self):
        node = self._makeOne(None)
        self.assertEqual(node.preparer, None)

    def test_ctor_with_unknown_kwarg(self):
        node = self._makeOne(None, foo=1)
        self.assertEqual(node.foo, 1)

    def test_ctor_with_kwarg_typ(self):
        node = self._makeOne(typ='foo')
        self.assertEqual(node.typ, 'foo')

    def test_ctor_children_kwarg_typ(self):
        subnode1 = DummySchemaNode(None, name='sub1')
        subnode2 = DummySchemaNode(None, name='sub2')
        node = self._makeOne(subnode1, subnode2, typ='foo')
        self.assertEqual(node.children, [subnode1, subnode2])

    def test_ctor_without_type(self):
        self.assertRaises(NotImplementedError, self._makeOne)

    def test_required_true(self):
        node = self._makeOne(None)
        self.assertEqual(node.required, True)

    def test_required_false(self):
        node = self._makeOne(None, missing=1)
        self.assertEqual(node.required, False)

    def test_required_deferred(self):
        from colander import deferred
        node = self._makeOne(None, missing=deferred(lambda: '123'))
        self.assertEqual(node.required, True)

    def test_deserialize_no_validator(self):
        typ = DummyType()
        node = self._makeOne(typ)
        result = node.deserialize(1)
        self.assertEqual(result, 1)

    def test_deserialize_with_preparer(self):
        from colander import Invalid
        typ = DummyType()
        def preparer(value):
            return 'prepared_'+value
        def validator(node, value):
            if not value.startswith('prepared'):
                raise Invalid(node, 'not prepared') # pragma: no cover
        node = self._makeOne(typ,
                             preparer=preparer,
                             validator=validator)
        self.assertEqual(node.deserialize('value'),
                         'prepared_value')

    def test_deserialize_with_multiple_preparers(self):
        from colander import Invalid
        typ = DummyType()
        def preparer1(value):
            return 'prepared1_'+value
        def preparer2(value):
            return 'prepared2_'+value
        def validator(node, value):
            if not value.startswith('prepared2_prepared1'):
                raise Invalid(node, 'not prepared') # pragma: no cover
        node = self._makeOne(typ,
                             preparer=[preparer1, preparer2],
                             validator=validator)
        self.assertEqual(node.deserialize('value'),
                         'prepared2_prepared1_value')

    def test_deserialize_preparer_before_missing_check(self):
        from colander import null
        typ = DummyType()
        def preparer(value):
            return null
        node = self._makeOne(typ,preparer=preparer)
        e = invalid_exc(node.deserialize, 1)
        self.assertEqual(e.msg, 'Required')

    def test_deserialize_with_validator(self):
        typ = DummyType()
        validator = DummyValidator(msg='Wrong')
        node = self._makeOne(typ, validator=validator)
        e = invalid_exc(node.deserialize, 1)
        self.assertEqual(e.msg, 'Wrong')

    def test_deserialize_with_unbound_validator(self):
        from colander import Invalid
        from colander import deferred
        from colander import UnboundDeferredError
        typ = DummyType()
        def validator(node, kw):
            def _validate(node, value):
                node.raise_invalid('Invalid')
            return _validate
        node = self._makeOne(typ, validator=deferred(validator))
        self.assertRaises(UnboundDeferredError, node.deserialize, None)
        self.assertRaises(Invalid, node.bind(foo='foo').deserialize, None)

    def test_deserialize_value_is_null_no_missing(self):
        from colander import null
        from colander import Invalid
        typ = DummyType()
        node = self._makeOne(typ)
        self.assertRaises(Invalid, node.deserialize, null)

    def test_deserialize_value_is_null_with_missing(self):
        from colander import null
        typ = DummyType()
        node = self._makeOne(typ)
        node.missing = 'abc'
        self.assertEqual(node.deserialize(null), 'abc')

    def test_deserialize_value_is_null_with_missing_msg(self):
        from colander import null
        typ = DummyType()
        node = self._makeOne(typ, missing_msg='Missing')
        e = invalid_exc(node.deserialize, null)
        self.assertEqual(e.msg, 'Missing')

    def test_deserialize_value_with_interpolated_missing_msg(self):
        from colander import null
        typ = DummyType()
        node = self._makeOne(typ, missing_msg='Missing attribute ${title}',
                             name='name_a')
        e = invalid_exc(node.deserialize, null)
        self.assertEqual(e.msg.interpolate(), 'Missing attribute Name A')

    def test_deserialize_noargs_uses_default(self):
        typ = DummyType()
        node = self._makeOne(typ)
        node.missing = 'abc'
        self.assertEqual(node.deserialize(), 'abc')

    def test_deserialize_null_can_be_used_as_missing(self):
        from colander import null
        typ = DummyType()
        node = self._makeOne(typ)
        node.missing = null
        self.assertEqual(node.deserialize(null), null)

    def test_deserialize_appstruct_deferred(self):
        from colander import null
        from colander import deferred
        from colander import Invalid
        typ = DummyType()
        node = self._makeOne(typ)
        node.missing = deferred(lambda: '123')
        self.assertRaises(Invalid, node.deserialize, null)

    def test_serialize(self):
        typ = DummyType()
        node = self._makeOne(typ)
        result = node.serialize(1)
        self.assertEqual(result, 1)

    def test_serialize_value_is_null_no_default(self):
        from colander import null
        typ = DummyType()
        node = self._makeOne(typ)
        result = node.serialize(null)
        self.assertEqual(result, null)

    def test_serialize_value_is_null_with_default(self):
        from colander import null
        typ = DummyType()
        node = self._makeOne(typ)
        node.default = 1
        result = node.serialize(null)
        self.assertEqual(result, 1)

    def test_serialize_noargs_uses_default(self):
        typ = DummyType()
        node = self._makeOne(typ)
        node.default = 'abc'
        self.assertEqual(node.serialize(), 'abc')

    def test_serialize_default_deferred(self):
        from colander import deferred
        from colander import null
        typ = DummyType()
        node = self._makeOne(typ)
        node.default = deferred(lambda: 'abc')
        self.assertEqual(node.serialize(), null)

    def test_add(self):
        node = self._makeOne(None)
        node.add(1)
        self.assertEqual(node.children, [1])

    def test_insert(self):
        node = self._makeOne(None)
        node.children = [99, 99]
        node.insert(1, 'foo')
        self.assertEqual(node.children, [99, 'foo', 99])

    def test_repr(self):
        node = self._makeOne(None, name='flub')
        result = repr(node)
        self.assertTrue(result.startswith('<colander.SchemaNode object at '))
        self.assertTrue(result.endswith("(named flub)>"))

    def test___getitem__success(self):
        node = self._makeOne(None)
        another = self._makeOne(None, name='another')
        node.add(another)
        self.assertEqual(node['another'], another)

    def test___getitem__failure(self):
        node = self._makeOne(None)
        self.assertRaises(KeyError, node.__getitem__, 'another')

    def test___delitem__success(self):
        node = self._makeOne(None)
        another = self._makeOne(None, name='another')
        node.add(another)
        del node['another']
        self.assertEqual(node.children, [])

    def test___delitem__failure(self):
        node = self._makeOne(None)
        self.assertRaises(KeyError, node.__delitem__, 'another')

    def test___setitem__override(self):
        node = self._makeOne(None)
        another = self._makeOne(None, name='another')
        node.add(another)
        andanother = self._makeOne(None, name='andanother')
        node['another'] = andanother
        self.assertEqual(node['another'], andanother)
        self.assertEqual(andanother.name, 'another')

    def test___setitem__no_override(self):
        another = self._makeOne(None, name='another')
        node = self._makeOne(None)
        node['another'] = another
        self.assertEqual(node['another'], another)
        self.assertEqual(node.children[0], another)

    def test___iter__(self):
        node = self._makeOne(None)
        node.children = ['a', 'b', 'c']
        it = node.__iter__()
        self.assertEqual(list(it), ['a', 'b', 'c'])

    def test___contains__(self):
        node = self._makeOne(None)
        another = self._makeOne(None, name='another')
        node.add(another)
        self.assertEqual('another' in node, True)
        self.assertEqual('b' in node, False)

    def test_clone(self):
        inner_typ = DummyType()
        outer_typ = DummyType()
        outer_node = self._makeOne(outer_typ, name='outer')
        inner_node = self._makeOne(inner_typ, name='inner')
        outer_node.foo = 1
        inner_node.foo = 2
        outer_node.children = [inner_node]
        outer_clone = outer_node.clone()
        self.assertFalse(outer_clone is outer_node)
        self.assertEqual(outer_clone.typ, outer_typ)
        self.assertEqual(outer_clone.name, 'outer')
        self.assertEqual(outer_node.foo, 1)
        self.assertEqual(len(outer_clone.children), 1)
        inner_clone = outer_clone.children[0]
        self.assertFalse(inner_clone is inner_node)
        self.assertEqual(inner_clone.typ, inner_typ)
        self.assertEqual(inner_clone.name, 'inner')
        self.assertEqual(inner_clone.foo, 2)

    def test_bind(self):
        from colander import deferred
        inner_typ = DummyType()
        outer_typ = DummyType()
        def dv(node, kw):
            self.assertTrue(node.name in ['outer', 'inner'])
            self.assertTrue('a' in kw)
            return '123'
        dv = deferred(dv)
        outer_node = self._makeOne(outer_typ, name='outer', missing=dv)
        inner_node = self._makeOne(inner_typ, name='inner', validator=dv,
                                   missing=dv)
        outer_node.children = [inner_node]
        outer_clone = outer_node.bind(a=1)
        self.assertFalse(outer_clone is outer_node)
        self.assertEqual(outer_clone.missing, '123')
        inner_clone = outer_clone.children[0]
        self.assertFalse(inner_clone is inner_node)
        self.assertEqual(inner_clone.missing, '123')
        self.assertEqual(inner_clone.validator, '123')

    def test_bind_with_after_bind(self):
        from colander import deferred
        inner_typ = DummyType()
        outer_typ = DummyType()
        def dv(node, kw):
            self.assertTrue(node.name in ['outer', 'inner'])
            self.assertTrue('a' in kw)
            return '123'
        dv = deferred(dv)
        def remove_inner(node, kw):
            self.assertEqual(kw, {'a':1})
            del node['inner']
        outer_node = self._makeOne(outer_typ, name='outer', missing=dv,
                                   after_bind=remove_inner)
        inner_node = self._makeOne(inner_typ, name='inner', validator=dv,
                                   missing=dv)
        outer_node.children = [inner_node]
        outer_clone = outer_node.bind(a=1)
        self.assertFalse(outer_clone is outer_node)
        self.assertEqual(outer_clone.missing, '123')
        self.assertEqual(len(outer_clone.children), 0)
        self.assertEqual(len(outer_node.children), 1)

    def test_declarative_name_reassignment(self):
        # see https://github.com/Pylons/colander/issues/39
        import colander
        class FnordSchema(colander.Schema):
            fnord = colander.SchemaNode(
                colander.Sequence(),
                colander.SchemaNode(colander.Integer(), name=''),
                name="fnord[]"
                )
        schema = FnordSchema()
        self.assertEqual(schema['fnord[]'].name, 'fnord[]')

    def test_cstruct_children(self):
        typ = DummyType()
        typ.cstruct_children = lambda *arg: ['foo']
        node = self._makeOne(typ)
        self.assertEqual(node.cstruct_children(None), ['foo'])

    def test_cstruct_children_warning(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            typ = None
            node = self._makeOne(typ)
            self.assertEqual(node.cstruct_children(None), [])
            self.assertEqual(len(w), 1)

    def test_raise_invalid(self):
        import colander
        typ = DummyType()
        node = self._makeOne(typ)
        self.assertRaises(colander.Invalid, node.raise_invalid, 'Wrong')

class TestSchemaNodeSubclassing(unittest.TestCase):
    def test_subclass_uses_validator_method(self):
        import colander
        class MyNode(colander.SchemaNode):
            schema_type = colander.Int
            name = 'my'
            def validator(self, node, cstruct):
                if cstruct > 10:
                    self.raise_invalid('Wrong')
        node = MyNode()
        self.assertRaises(colander.Invalid, node.deserialize, 20)

    def test_subclass_uses_missing(self):
        import colander
        class MyNode(colander.SchemaNode):
            schema_type = colander.Int
            name = 'my'
            missing = 10
        node = MyNode()
        result = node.deserialize(colander.null)
        self.assertEqual(result, 10)

    def test_subclass_uses_title(self):
        import colander
        class MyNode(colander.SchemaNode):
            schema_type = colander.Int
            title = 'some title'
        node = MyNode(name='my')
        self.assertEqual(node.title, 'some title')

    def test_subclass_title_overwritten_by_constructor(self):
        import colander
        class MyNode(colander.SchemaNode):
            schema_type = colander.Int
            title = 'some title'
        node = MyNode(name='my', title='other title')
        self.assertEqual(node.title, 'other title')

    def test_subelement_title_not_overwritten(self):
        import colander
        class SampleNode(colander.SchemaNode):
            schema_type = colander.String
            title = 'Some Title'
        class SampleSchema(colander.Schema):
            node = SampleNode()
        schema = SampleSchema()
        self.assertEqual('Some Title', schema.children[0].title)

    def test_subclass_value_overridden_by_constructor(self):
        import colander
        class MyNode(colander.SchemaNode):
            schema_type = colander.Int
            name = 'my'
            missing = 10
        node = MyNode(missing=5)
        result = node.deserialize(colander.null)
        self.assertEqual(result, 5)

    def test_method_values_can_rely_on_binding(self):
        import colander
        class MyNode(colander.SchemaNode):
            schema_type = colander.Int
            def amethod(self):
                return self.bindings['request']

        node = MyNode()
        newnode = node.bind(request=True)
        self.assertEqual(newnode.amethod(), True)

    def test_nonmethod_values_can_rely_on_after_bind(self):
        import colander
        class MyNode(colander.SchemaNode):
            schema_type = colander.Int
            def after_bind(self, node, kw):
                self.missing = kw['missing']

        node = MyNode()
        newnode = node.bind(missing=10)
        self.assertEqual(newnode.deserialize(colander.null), 10)

    def test_deferred_methods_dont_quite_work_yet(self):
        import colander
        class MyNode(colander.SchemaNode):
            schema_type = colander.Int
            @colander.deferred
            def avalidator(self, node, kw): # pragma: no cover
                def _avalidator(node, cstruct):
                    self.raise_invalid('Foo')
                return _avalidator

        node = MyNode()
        self.assertRaises(TypeError, node.bind)

    def test_nonmethod_values_can_be_deferred_though(self):
        import colander
        def _missing(node, kw):
            return 10
        class MyNode(colander.SchemaNode):
            schema_type = colander.Int
            missing = colander.deferred(_missing)

        node = MyNode()
        bound_node = node.bind()
        self.assertEqual(bound_node.deserialize(colander.null), 10)

    def test_functions_can_be_deferred(self):
        import colander
        class MyNode(colander.SchemaNode):
            schema_type = colander.Int
            @colander.deferred
            def missing(node, kw):
                return 10

        node = MyNode()
        bound_node = node.bind()
        self.assertEqual(bound_node.deserialize(colander.null), 10)

    def test_schema_child_names_conflict_with_value_names_notused(self):
        import colander
        class MyNode(colander.SchemaNode):
            schema_type = colander.Mapping
            title = colander.SchemaNode(
                colander.String(),
                )
        node = MyNode()
        self.assertEqual(node.title, '')

    def test_schema_child_names_conflict_with_value_names_used(self):
        import colander
        doesntmatter = colander.SchemaNode(
            colander.String(),
            name='name',
            )
        class MyNode(colander.SchemaNode):
            schema_type = colander.Mapping
            name = 'fred'
            wontmatter = doesntmatter
        node = MyNode()
        self.assertEqual(node.name, 'fred')
        self.assertEqual(node['name'], doesntmatter)

    def test_schema_child_names_conflict_with_value_names_in_superclass(self):
        import colander
        doesntmatter = colander.SchemaNode(
            colander.String(),
            name='name',
            )
        _name = colander.SchemaNode(
            colander.String(),
            )
        class MyNode(colander.SchemaNode):
            schema_type = colander.Mapping
            name = 'fred'
            wontmatter = doesntmatter
        class AnotherNode(MyNode):
            name = _name
        node = AnotherNode()
        self.assertEqual(node.name, 'fred')
        self.assertEqual(node['name'], _name)

    def test_schema_child_names_conflict_with_value_names_in_subclass(self):
        import colander
        class MyNode(colander.SchemaNode):
            name = colander.SchemaNode(
                colander.String(),
                id='name',
                )
        class AnotherNode(MyNode):
            schema_type = colander.Mapping
            name = 'fred'
            doesntmatter = colander.SchemaNode(
                colander.String(),
                name='name',
                id='doesntmatter',
                )
        node = AnotherNode()
        self.assertEqual(node.name, 'fred')
        self.assertEqual(node['name'].id, 'doesntmatter')

class TestMappingSchemaInheritance(unittest.TestCase):
    def test_single_inheritance(self):
        import colander
        class Friend(colander.Schema):
            rank = colander.SchemaNode(
                colander.Int(),
                id='rank',
                )
            name = colander.SchemaNode(
                colander.String(),
                id='name'
                )
            serial = colander.SchemaNode(
                colander.Bool(),
                id='serial2',
                )

        class SpecialFriend(Friend):
            iwannacomefirst = colander.SchemaNode(
                colander.Int(),
                id='iwannacomefirst2',
                )

        class SuperSpecialFriend(SpecialFriend):
            iwannacomefirst = colander.SchemaNode(
                colander.String(),
                id='iwannacomefirst1',
                )
            another = colander.SchemaNode(
                colander.String(),
                id='another',
                )
            serial = colander.SchemaNode(
                colander.Int(),
                id='serial1',
                )

        inst = SuperSpecialFriend()
        self.assertEqual(
            [ x.id for x in inst.children],
            [
                'rank',
                'name',
                'serial1',
                'iwannacomefirst1',
                'another',
             ]
            )

    def test_single_inheritance_with_insert_before(self):
        import colander
        class Friend(colander.Schema):
            rank = colander.SchemaNode(
                colander.Int(),
                id='rank',
                )
            name = colander.SchemaNode(
                colander.String(),
                id='name'
                )
            serial = colander.SchemaNode(
                colander.Bool(),
                insert_before='name',
                id='serial2',
                )

        class SpecialFriend(Friend):
            iwannacomefirst = colander.SchemaNode(
                colander.Int(),
                id='iwannacomefirst2',
                )

        class SuperSpecialFriend(SpecialFriend):
            iwannacomefirst = colander.SchemaNode(
                colander.String(),
                insert_before='rank',
                id='iwannacomefirst1',
                )
            another = colander.SchemaNode(
                colander.String(),
                id='another',
                )
            serial = colander.SchemaNode(
                colander.Int(),
                id='serial1',
                )

        inst = SuperSpecialFriend()
        self.assertEqual(
            [ x.id for x in inst.children],
            [
                'iwannacomefirst1',
                'rank',
                'serial1',
                'name',
                'another',
             ]
            )

    def test_single_inheritance2(self):
        import colander
        class One(colander.Schema):
            a = colander.SchemaNode(
                colander.Int(),
                id='a1',
                )
            b = colander.SchemaNode(
                colander.Int(),
                id='b1',
                )
            d = colander.SchemaNode(
                colander.Int(),
                id='d1',
                )

        class Two(One):
            a = colander.SchemaNode(
                colander.String(),
                id='a2',
                )
            c = colander.SchemaNode(
                colander.String(),
                id='c2',
                )
            e = colander.SchemaNode(
                colander.String(),
                id='e2',
                )

        class Three(Two):
            b = colander.SchemaNode(
                colander.Bool(),
                id='b3',
                )
            d = colander.SchemaNode(
                colander.Bool(),
                id='d3',
                )
            f = colander.SchemaNode(
                colander.Bool(),
                id='f3',
                )

        inst = Three()
        c = inst.children
        self.assertEqual(len(c), 6)
        result = [ x.id for x in c ]
        self.assertEqual(result, ['a2', 'b3', 'd3', 'c2', 'e2', 'f3'])

    def test_multiple_inheritance(self):
        import colander
        class One(colander.Schema):
            a = colander.SchemaNode(
                colander.Int(),
                id='a1',
                )
            b = colander.SchemaNode(
                colander.Int(),
                id='b1',
                )
            d = colander.SchemaNode(
                colander.Int(),
                id='d1',
                )

        class Two(colander.Schema):
            a = colander.SchemaNode(
                colander.String(),
                id='a2',
                )
            c = colander.SchemaNode(
                colander.String(),
                id='c2',
                )
            e = colander.SchemaNode(
                colander.String(),
                id='e2',
                )

        class Three(Two, One):
            b = colander.SchemaNode(
                colander.Bool(),
                id='b3',
                )
            d = colander.SchemaNode(
                colander.Bool(),
                id='d3',
                )
            f = colander.SchemaNode(
                colander.Bool(),
                id='f3',
                )

        inst = Three()
        c = inst.children
        self.assertEqual(len(c), 6)
        result = [ x.id for x in c ]
        self.assertEqual(result, ['a2', 'b3', 'd3', 'c2', 'e2', 'f3'])

    def test_insert_before_failure(self):
        import colander
        class One(colander.Schema):
            a = colander.SchemaNode(
                colander.Int(),
                )
            b = colander.SchemaNode(
                colander.Int(),
                insert_before='c'
                )
        self.assertRaises(KeyError, One)

class TestDeferred(unittest.TestCase):
    def _makeOne(self, wrapped):
        from colander import deferred
        return deferred(wrapped)

    def test_ctor(self):
        wrapped = lambda: 'foo'
        inst = self._makeOne(wrapped)
        self.assertEqual(inst.wrapped, wrapped)

    def test___call__(self):
        n = object()
        k = object()
        def wrapped(node, kw):
            self.assertEqual(node, n)
            self.assertEqual(kw, k)
            return 'abc'
        inst = self._makeOne(wrapped)
        result= inst(n, k)
        self.assertEqual(result, 'abc')

    def test_retain_func_details(self):
        def wrapped_func(node, kw):
            """Can you hear me now?"""
            pass  # pragma: no cover
        inst = self._makeOne(wrapped_func)
        self.assertEqual(inst.__doc__, 'Can you hear me now?')
        self.assertEqual(inst.__name__, 'wrapped_func')

    def test_w_callable_instance_no_name(self):
        from colander import deferred
        class Wrapped(object):
            """CLASS"""
            def __call__(self, node, kw):
                """METHOD"""
                pass # pragma: no cover
        wrapped = Wrapped()
        inst = self._makeOne(wrapped)
        self.assertEqual(inst.__doc__, wrapped.__doc__)
        self.assertFalse('__name__' in inst.__dict__)

    def test_w_callable_instance_no_name_or_doc(self):
        from colander import deferred
        class Wrapped(object):
            def __call__(self, node, kw):
                pass # pragma: no cover
        wrapped = Wrapped()
        inst = self._makeOne(wrapped)
        self.assertEqual(inst.__doc__, None)
        self.assertFalse('__name__' in inst.__dict__)

class TestSchema(unittest.TestCase):
    def test_alias(self):
        from colander import Schema
        from colander import MappingSchema
        self.assertEqual(Schema, MappingSchema)

    def test_it(self):
        import colander
        class MySchema(colander.Schema):
            thing_a = colander.SchemaNode(colander.String())
            thing2 = colander.SchemaNode(colander.String(), title='bar')
        node = MySchema(default='abc')
        self.assertTrue(hasattr(node, '_order'))
        self.assertEqual(node.default, 'abc')
        self.assertTrue(isinstance(node, colander.SchemaNode))
        self.assertEqual(node.typ.__class__, colander.Mapping)
        self.assertEqual(node.children[0].typ.__class__, colander.String)
        self.assertEqual(node.children[0].title, 'Thing A')
        self.assertEqual(node.children[1].title, 'bar')

    def test_title_munging(self):
        import colander
        class MySchema(colander.Schema):
            thing1 = colander.SchemaNode(colander.String())
            thing2 = colander.SchemaNode(colander.String(), title=None)
            thing3 = colander.SchemaNode(colander.String(), title='')
            thing4 = colander.SchemaNode(colander.String(), title='thing2')
        node = MySchema()
        self.assertEqual(node.children[0].title, 'Thing1')
        self.assertEqual(node.children[1].title, None)
        self.assertEqual(node.children[2].title, '')
        self.assertEqual(node.children[3].title, 'thing2')

    def test_deserialize_drop(self):
        import colander
        class MySchema(colander.Schema):
            a = colander.SchemaNode(colander.String())
            b = colander.SchemaNode(colander.String(), missing=colander.drop)
        node = MySchema()
        expected = {'a': 'test'}
        result = node.deserialize(expected)
        self.assertEqual(result, expected)

    def test_serialize_drop_default(self):
        import colander
        class MySchema(colander.Schema):
            a = colander.SchemaNode(colander.String())
            b = colander.SchemaNode(colander.String(), default=colander.drop)
        node = MySchema()
        expected = {'a': 'foo'}
        result = node.serialize(expected)
        self.assertEqual(result, expected)

    def test_imperative_with_implicit_schema_type(self):
        import colander
        node = colander.SchemaNode(colander.String())
        schema = colander.Schema(node)
        self.assertEqual(schema.schema_type, colander.Mapping)
        self.assertEqual(schema.children[0], node)

class TestSequenceSchema(unittest.TestCase):
    def test_succeed(self):
        import colander
        _inner = colander.SchemaNode(colander.String())
        class MySchema(colander.SequenceSchema):
            inner = _inner
        node = MySchema()
        self.assertTrue(hasattr(node, '_order'))
        self.assertTrue(isinstance(node, colander.SchemaNode))
        self.assertEqual(node.typ.__class__, colander.Sequence)
        self.assertEqual(node.children[0], _inner)

    def test_fail_toomany(self):
        import colander
        thingnode = colander.SchemaNode(colander.String())
        thingnode2 = colander.SchemaNode(colander.String())
        class MySchema(colander.SequenceSchema):
            thing = thingnode
            thing2 = thingnode2
        e = invalid_exc(MySchema)
        self.assertEqual(
            e.msg,
            'Sequence schemas must have exactly one child node')

    def test_fail_toofew(self):
        import colander
        class MySchema(colander.SequenceSchema):
            pass
        e = invalid_exc(MySchema)
        self.assertEqual(
            e.msg,
            'Sequence schemas must have exactly one child node')

    def test_imperative_with_implicit_schema_type(self):
        import colander
        node = colander.SchemaNode(colander.String())
        schema = colander.SequenceSchema(node)
        self.assertEqual(schema.schema_type, colander.Sequence)
        self.assertEqual(schema.children[0], node)

    def test_deserialize_drop(self):
        import colander
        class MySchema(colander.SequenceSchema):
            a = colander.SchemaNode(colander.String(), missing=colander.drop)
        node = MySchema()
        result = node.deserialize([None])
        self.assertEqual(result, [])
        result = node.deserialize([colander.null])
        self.assertEqual(result, [])

    def test_serialize_drop_default(self):
        import colander
        class MySchema(colander.SequenceSchema):
            a = colander.SchemaNode(colander.String(), default=colander.drop)
        node = MySchema()
        result = node.serialize([colander.null])
        self.assertEqual(result, [])

    def test_clone_with_sequence_schema(self):
        import colander
        thingnode = colander.SchemaNode(colander.String(), name='foo')
        schema = colander.SequenceSchema(colander.Sequence(), thingnode)
        result = schema.clone()
        self.assertEqual(result.children[0].name, 'foo')

class TestTupleSchema(unittest.TestCase):
    def test_it(self):
        import colander
        class MySchema(colander.TupleSchema):
            thing = colander.SchemaNode(colander.String())
        node = MySchema()
        self.assertTrue(hasattr(node, '_order'))
        self.assertTrue(isinstance(node, colander.SchemaNode))
        self.assertEqual(node.typ.__class__, colander.Tuple)
        self.assertEqual(node.children[0].typ.__class__, colander.String)

    def test_imperative_with_implicit_schema_type(self):
        import colander
        node = colander.SchemaNode(colander.String())
        schema = colander.TupleSchema(node)
        self.assertEqual(schema.schema_type, colander.Tuple)
        self.assertEqual(schema.children[0], node)

class TestFunctional(object):
    def test_deserialize_ok(self):
        import colander.tests
        data = {
            'int':'10',
            'ob':'colander.tests',
            'seq':[('1', 's'),('2', 's'), ('3', 's'), ('4', 's')],
            'seq2':[{'key':'1', 'key2':'2'}, {'key':'3', 'key2':'4'}],
            'tup':('1', 's'),
            }
        schema = self._makeSchema()
        result = schema.deserialize(data)
        self.assertEqual(result['int'], 10)
        self.assertEqual(result['ob'], colander.tests)
        self.assertEqual(result['seq'],
                         [(1, 's'), (2, 's'), (3, 's'), (4, 's')])
        self.assertEqual(result['seq2'],
                         [{'key':1, 'key2':2}, {'key':3, 'key2':4}])
        self.assertEqual(result['tup'], (1, 's'))

    def test_flatten_ok(self):
        import colander
        appstruct = {
            'int':10,
            'ob':colander.tests,
            'seq':[(1, 's'),(2, 's'), (3, 's'), (4, 's')],
            'seq2':[{'key':1, 'key2':2}, {'key':3, 'key2':4}],
            'tup':(1, 's'),
            }
        schema = self._makeSchema()
        result = schema.flatten(appstruct)

        expected = {
            'schema.seq.2.tupstring': 's',
            'schema.seq2.0.key2': 2,
            'schema.ob': colander.tests,
            'schema.seq2.1.key2': 4,
            'schema.seq.1.tupstring': 's',
            'schema.seq2.0.key': 1,
            'schema.seq.1.tupint': 2,
            'schema.seq.0.tupstring': 's',
            'schema.seq.3.tupstring': 's',
            'schema.seq.3.tupint': 4,
            'schema.seq2.1.key': 3,
            'schema.int': 10,
            'schema.seq.0.tupint': 1,
            'schema.tup.tupint': 1,
            'schema.tup.tupstring': 's',
            'schema.seq.2.tupint': 3,
        }

        for k, v in expected.items():
            self.assertEqual(result[k], v)
        for k, v in result.items():
            self.assertEqual(expected[k], v)

    def test_flatten_mapping_has_no_name(self):
        import colander
        appstruct = {
            'int':10,
            'ob':colander.tests,
            'seq':[(1, 's'),(2, 's'), (3, 's'), (4, 's')],
            'seq2':[{'key':1, 'key2':2}, {'key':3, 'key2':4}],
            'tup':(1, 's'),
            }
        schema = self._makeSchema(name='')
        result = schema.flatten(appstruct)

        expected = {
            'seq.2.tupstring': 's',
            'seq2.0.key2': 2,
            'ob': colander.tests,
            'seq2.1.key2': 4,
            'seq.1.tupstring': 's',
            'seq2.0.key': 1,
            'seq.1.tupint': 2,
            'seq.0.tupstring': 's',
            'seq.3.tupstring': 's',
            'seq.3.tupint': 4,
            'seq2.1.key': 3,
            'int': 10,
            'seq.0.tupint': 1,
            'tup.tupint': 1,
            'tup.tupstring': 's',
            'seq.2.tupint': 3,
        }

        for k, v in expected.items():
            self.assertEqual(result[k], v)
        for k, v in result.items():
            self.assertEqual(expected[k], v)

    def test_unflatten_ok(self):
        import colander
        fstruct = {
            'schema.seq.2.tupstring': 's',
            'schema.seq2.0.key2': 2,
            'schema.ob': colander.tests,
            'schema.seq2.1.key2': 4,
            'schema.seq.1.tupstring': 's',
            'schema.seq2.0.key': 1,
            'schema.seq.1.tupint': 2,
            'schema.seq.0.tupstring': 's',
            'schema.seq.3.tupstring': 's',
            'schema.seq.3.tupint': 4,
            'schema.seq2.1.key': 3,
            'schema.int': 10,
            'schema.seq.0.tupint': 1,
            'schema.tup.tupint': 1,
            'schema.tup.tupstring': 's',
            'schema.seq.2.tupint': 3,
        }
        schema = self._makeSchema()
        result = schema.unflatten(fstruct)

        expected = {
            'int':10,
            'ob':colander.tests,
            'seq':[(1, 's'),(2, 's'), (3, 's'), (4, 's')],
            'seq2':[{'key':1, 'key2':2}, {'key':3, 'key2':4}],
            'tup':(1, 's'),
            }

        for k, v in expected.items():
            self.assertEqual(result[k], v)
        for k, v in result.items():
            self.assertEqual(expected[k], v)

    def test_unflatten_mapping_no_name(self):
        import colander
        fstruct = {
            'seq.2.tupstring': 's',
            'seq2.0.key2': 2,
            'ob': colander.tests,
            'seq2.1.key2': 4,
            'seq.1.tupstring': 's',
            'seq2.0.key': 1,
            'seq.1.tupint': 2,
            'seq.0.tupstring': 's',
            'seq.3.tupstring': 's',
            'seq.3.tupint': 4,
            'seq2.1.key': 3,
            'int': 10,
            'seq.0.tupint': 1,
            'tup.tupint': 1,
            'tup.tupstring': 's',
            'seq.2.tupint': 3,
        }
        schema = self._makeSchema(name='')
        result = schema.unflatten(fstruct)

        expected = {
            'int':10,
            'ob':colander.tests,
            'seq':[(1, 's'),(2, 's'), (3, 's'), (4, 's')],
            'seq2':[{'key':1, 'key2':2}, {'key':3, 'key2':4}],
            'tup':(1, 's'),
            }

        for k, v in expected.items():
            self.assertEqual(result[k], v)
        for k, v in result.items():
            self.assertEqual(expected[k], v)

    def test_flatten_unflatten_roundtrip(self):
        import colander
        appstruct = {
            'int':10,
            'ob':colander.tests,
            'seq':[(1, 's'),(2, 's'), (3, 's'), (4, 's')],
            'seq2':[{'key':1, 'key2':2}, {'key':3, 'key2':4}],
            'tup':(1, 's'),
            }
        schema = self._makeSchema(name='')
        self.assertEqual(
            schema.unflatten(schema.flatten(appstruct)),
            appstruct)

    def test_set_value(self):
        import colander
        appstruct = {
            'int':10,
            'ob':colander.tests,
            'seq':[(1, 's'),(2, 's'), (3, 's'), (4, 's')],
            'seq2':[{'key':1, 'key2':2}, {'key':3, 'key2':4}],
            'tup':(1, 's'),
            }
        schema = self._makeSchema()
        schema.set_value(appstruct, 'seq2.1.key', 6)
        self.assertEqual(appstruct['seq2'][1], {'key':6, 'key2':4})

    def test_get_value(self):
        import colander
        appstruct = {
            'int':10,
            'ob':colander.tests,
            'seq':[(1, 's'),(2, 's'), (3, 's'), (4, 's')],
            'seq2':[{'key':1, 'key2':2}, {'key':3, 'key2':4}],
            'tup':(1, 's'),
            }
        schema = self._makeSchema()
        self.assertEqual(schema.get_value(appstruct, 'seq'),
                         [(1, 's'),(2, 's'), (3, 's'), (4, 's')])
        self.assertEqual(schema.get_value(appstruct, 'seq2.1.key'), 3)

    def test_invalid_asdict(self):
        expected = {
            'schema.int': '20 is greater than maximum value 10',
            'schema.ob': 'The dotted name "no.way.this.exists" '
                         'cannot be imported',
            'schema.seq.0.0': '"q" is not a number',
            'schema.seq.1.0': '"w" is not a number',
            'schema.seq.2.0': '"e" is not a number',
            'schema.seq.3.0': '"r" is not a number',
            'schema.seq2.0.key': '"t" is not a number',
            'schema.seq2.0.key2': '"y" is not a number',
            'schema.seq2.1.key': '"u" is not a number',
            'schema.seq2.1.key2': '"i" is not a number',
            'schema.tup.0': '"s" is not a number'}
        data = {
            'int':'20',
            'ob':'no.way.this.exists',
            'seq':[('q', 's'),('w', 's'), ('e', 's'), ('r', 's')],
            'seq2':[{'key':'t', 'key2':'y'}, {'key':'u', 'key2':'i'}],
            'tup':('s', 's'),
            }
        schema = self._makeSchema()
        e = invalid_exc(schema.deserialize, data)
        errors = e.asdict()
        self.assertEqual(errors, expected)

    def test_invalid_asdict_translation_callback(self):
        from translationstring import TranslationString

        expected = {
            'schema.int': 'translated',
            'schema.ob': 'translated',
            'schema.seq.0.0': 'translated',
            'schema.seq.1.0': 'translated',
            'schema.seq.2.0': 'translated',
            'schema.seq.3.0': 'translated',
            'schema.seq2.0.key': 'translated',
            'schema.seq2.0.key2': 'translated',
            'schema.seq2.1.key': 'translated',
            'schema.seq2.1.key2': 'translated',
            'schema.tup.0': 'translated',
        }
        data = {
            'int': '20',
            'ob': 'no.way.this.exists',
            'seq': [('q', 's'), ('w', 's'), ('e', 's'), ('r', 's')],
            'seq2': [{'key': 't', 'key2': 'y'}, {'key':'u', 'key2':'i'}],
            'tup': ('s', 's'),
        }
        schema = self._makeSchema()
        e = invalid_exc(schema.deserialize, data)

        def translation_function(string):
            return TranslationString('translated')

        errors = e.asdict(translate=translation_function)
        self.assertEqual(errors, expected)


class TestImperative(unittest.TestCase, TestFunctional):

    def _makeSchema(self, name='schema'):
        import colander

        integer = colander.SchemaNode(
            colander.Integer(),
            name='int',
            validator=colander.Range(0, 10)
            )

        ob = colander.SchemaNode(
            colander.GlobalObject(package=colander),
            name='ob',
            )

        tup = colander.SchemaNode(
            colander.Tuple(),
            colander.SchemaNode(
                colander.Integer(),
                name='tupint',
                ),
            colander.SchemaNode(
                colander.String(),
                name='tupstring',
                ),
            name='tup',
            )

        seq = colander.SchemaNode(
            colander.Sequence(),
            tup,
            name='seq',
            )

        seq2 = colander.SchemaNode(
            colander.Sequence(),
            colander.SchemaNode(
                colander.Mapping(),
                colander.SchemaNode(
                    colander.Integer(),
                    name='key',
                    ),
                colander.SchemaNode(
                    colander.Integer(),
                    name='key2',
                    ),
                name='mapping',
                ),
            name='seq2',
            )

        schema = colander.SchemaNode(
            colander.Mapping(),
            integer,
            ob,
            tup,
            seq,
            seq2,
            name=name)

        return schema

class TestDeclarative(unittest.TestCase, TestFunctional):

    def _makeSchema(self, name='schema'):

        import colander

        class TupleSchema(colander.TupleSchema):
            tupint = colander.SchemaNode(colander.Int())
            tupstring = colander.SchemaNode(colander.String())

        class MappingSchema(colander.MappingSchema):
            key = colander.SchemaNode(colander.Int())
            key2 = colander.SchemaNode(colander.Int())

        class SequenceOne(colander.SequenceSchema):
            tup = TupleSchema()

        class SequenceTwo(colander.SequenceSchema):
            mapping = MappingSchema()

        class MainSchema(colander.MappingSchema):
            int = colander.SchemaNode(colander.Int(),
                                     validator=colander.Range(0, 10))
            ob = colander.SchemaNode(colander.GlobalObject(package=colander))
            seq = SequenceOne()
            tup = TupleSchema()
            seq2 = SequenceTwo()

        schema = MainSchema(name=name)
        return schema

class TestUltraDeclarative(unittest.TestCase, TestFunctional):

    def _makeSchema(self, name='schema'):

        import colander

        class IntSchema(colander.SchemaNode):
            schema_type = colander.Int

        class StringSchema(colander.SchemaNode):
            schema_type = colander.String

        class TupleSchema(colander.TupleSchema):
            tupint = IntSchema()
            tupstring = StringSchema()

        class MappingSchema(colander.MappingSchema):
            key = IntSchema()
            key2 = IntSchema()

        class SequenceOne(colander.SequenceSchema):
            tup = TupleSchema()

        class SequenceTwo(colander.SequenceSchema):
            mapping = MappingSchema()

        class IntSchemaRanged(IntSchema):
            validator = colander.Range(0, 10)

        class GlobalObjectSchema(colander.SchemaNode):
            def schema_type(self):
                return colander.GlobalObject(package=colander)

        class MainSchema(colander.MappingSchema):
            int = IntSchemaRanged()
            ob = GlobalObjectSchema()
            seq = SequenceOne()
            tup = TupleSchema()
            seq2 = SequenceTwo()

        MainSchema.name = name

        schema = MainSchema()
        return schema

class TestDeclarativeWithInstantiate(unittest.TestCase, TestFunctional):

    def _makeSchema(self, name='schema'):

        import colander

        # an unlikely usage, but goos to test passing
        # parameters to instantiation works
        @colander.instantiate(name=name)
        class schema(colander.MappingSchema):
            int = colander.SchemaNode(colander.Int(),
                                     validator=colander.Range(0, 10))
            ob = colander.SchemaNode(colander.GlobalObject(package=colander))
            @colander.instantiate()
            class seq(colander.SequenceSchema):

                @colander.instantiate()
                class tup(colander.TupleSchema):
                    tupint = colander.SchemaNode(colander.Int())
                    tupstring = colander.SchemaNode(colander.String())

            @colander.instantiate()
            class tup(colander.TupleSchema):
                tupint = colander.SchemaNode(colander.Int())
                tupstring = colander.SchemaNode(colander.String())

            @colander.instantiate()
            class seq2(colander.SequenceSchema):

                @colander.instantiate()
                class mapping(colander.MappingSchema):
                    key = colander.SchemaNode(colander.Int())
                    key2 = colander.SchemaNode(colander.Int())

        return schema

class Test_null(unittest.TestCase):
    def test___nonzero__(self):
        from colander import null
        self.assertFalse(null)

    def test___repr__(self):
        from colander import null
        self.assertEqual(repr(null), '<colander.null>')

    def test_pickling(self):
        from colander import null
        import pickle
        self.assertTrue(pickle.loads(pickle.dumps(null)) is null)

class Test_required(unittest.TestCase):
    def test___repr__(self):
        from colander import required
        self.assertEqual(repr(required), '<colander.required>')

class Test_drop(unittest.TestCase):
    def test___repr__(self):
        from colander import drop
        self.assertEqual(repr(drop), '<colander.drop>')

class Dummy(object):
    pass

class DummySchemaNode(object):
    def __init__(self, typ, name='', exc=None, default=None):
        self.typ = typ
        self.name = name
        self.exc = exc
        self.required = default is None
        self.default = default
        self.children = []

    def deserialize(self, val):
        from colander import Invalid
        if self.exc:
            raise Invalid(self, self.exc)
        return val

    def serialize(self, val):
        from colander import Invalid
        if self.exc:
            raise Invalid(self, self.exc)
        return val

    def __getitem__(self, name):
        for child in self.children:
            if child.name == name:
                return child

class DummyValidator(object):
    def __init__(self, msg=None, children=None):
        self.msg = msg
        self.children = children

    def __call__(self, node, value):
        from colander import Invalid
        if self.msg:
            e = Invalid(node, self.msg)
            self.children and e.children.extend(self.children)
            raise e

class Uncooperative(object):
    def __str__(self):
        raise ValueError('I wont cooperate')

    __unicode__ = __str__

class DummyType(object):
    def serialize(self, node, value):
        return value

    def deserialize(self, node, value):
        return value

    def flatten(self, node, appstruct, prefix='', listitem=False):
        if listitem:
            key = prefix.rstrip('.')
        else:
            key = prefix + 'appstruct'
        return {key:appstruct}

    def unflatten(self, node, paths, fstruct):
        assert paths == [node.name]
        return fstruct[node.name]
