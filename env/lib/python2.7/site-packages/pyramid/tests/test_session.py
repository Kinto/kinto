import base64
import json
import unittest
from pyramid import testing

class SharedCookieSessionTests(object):

    def test_ctor_no_cookie(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        self.assertEqual(dict(session), {})

    def test_instance_conforms(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import ISession
        request = testing.DummyRequest()
        session = self._makeOne(request)
        verifyObject(ISession, session)

    def test_ctor_with_cookie_still_valid(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time(), 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request)
        self.assertEqual(dict(session), {'state':1})

    def test_ctor_with_cookie_expired(self):
        request = testing.DummyRequest()
        cookieval = self._serialize((0, 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request)
        self.assertEqual(dict(session), {})

    def test_ctor_with_bad_cookie_cannot_deserialize(self):
        request = testing.DummyRequest()
        request.cookies['session'] = 'abc'
        session = self._makeOne(request)
        self.assertEqual(dict(session), {})

    def test_ctor_with_bad_cookie_not_tuple(self):
        request = testing.DummyRequest()
        cookieval = self._serialize('abc')
        request.cookies['session'] = cookieval
        session = self._makeOne(request)
        self.assertEqual(dict(session), {})

    def test_timeout(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time() - 5, 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request, timeout=1)
        self.assertEqual(dict(session), {})

    def test_timeout_never(self):
        import time
        request = testing.DummyRequest()
        LONG_TIME = 31536000
        cookieval = self._serialize((time.time() + LONG_TIME, 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request, timeout=None)
        self.assertEqual(dict(session), {'state': 1})

    def test_timeout_str(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time() - 5, 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request, timeout='1')
        self.assertEqual(dict(session), {})

    def test_timeout_invalid(self):
        request = testing.DummyRequest()
        self.assertRaises(ValueError, self._makeOne, request, timeout='Invalid value')

    def test_changed(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        self.assertEqual(session.changed(), None)
        self.assertTrue(session._dirty)

    def test_invalidate(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        session['a'] = 1
        self.assertEqual(session.invalidate(), None)
        self.assertFalse('a' in session)

    def test_reissue_triggered(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time() - 2, 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request)
        self.assertEqual(session['state'], 1)
        self.assertTrue(session._dirty)

    def test__set_cookie_on_exception(self):
        request = testing.DummyRequest()
        request.exception = True
        session = self._makeOne(request)
        session._cookie_on_exception = False
        response = DummyResponse()
        self.assertEqual(session._set_cookie(response), False)

    def test__set_cookie_on_exception_no_request_exception(self):
        import webob
        request = testing.DummyRequest()
        request.exception = None
        session = self._makeOne(request)
        session._cookie_on_exception = False
        response = webob.Response()
        self.assertEqual(session._set_cookie(response), True)
        self.assertEqual(response.headerlist[-1][0], 'Set-Cookie')

    def test__set_cookie_cookieval_too_long(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        session['abc'] = 'x'*100000
        response = DummyResponse()
        self.assertRaises(ValueError, session._set_cookie, response)

    def test__set_cookie_real_webob_response(self):
        import webob
        request = testing.DummyRequest()
        session = self._makeOne(request)
        session['abc'] = 'x'
        response = webob.Response()
        self.assertEqual(session._set_cookie(response), True)
        self.assertEqual(response.headerlist[-1][0], 'Set-Cookie')

    def test__set_cookie_options(self):
        from pyramid.response import Response
        request = testing.DummyRequest()
        request.exception = None
        session = self._makeOne(request,
                                cookie_name='abc',
                                path='/foo',
                                domain='localhost',
                                secure=True,
                                httponly=True,
                                )
        session['abc'] = 'x'
        response = Response()
        self.assertEqual(session._set_cookie(response), True)
        cookieval = response.headerlist[-1][1]
        val, domain, path, secure, httponly = [x.strip() for x in
                                               cookieval.split(';')]
        self.assertTrue(val.startswith('abc='))
        self.assertEqual(domain, 'Domain=localhost')
        self.assertEqual(path, 'Path=/foo')
        self.assertEqual(secure, 'secure')
        self.assertEqual(httponly, 'HttpOnly')

    def test_flash_default(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        session.flash('msg1')
        session.flash('msg2')
        self.assertEqual(session['_f_'], ['msg1', 'msg2'])

    def test_flash_allow_duplicate_false(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        session.flash('msg1')
        session.flash('msg1', allow_duplicate=False)
        self.assertEqual(session['_f_'], ['msg1'])

    def test_flash_allow_duplicate_true_and_msg_not_in_storage(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        session.flash('msg1', allow_duplicate=True)
        self.assertEqual(session['_f_'], ['msg1'])

    def test_flash_allow_duplicate_false_and_msg_not_in_storage(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        session.flash('msg1', allow_duplicate=False)
        self.assertEqual(session['_f_'], ['msg1'])

    def test_flash_mixed(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        session.flash('warn1', 'warn')
        session.flash('warn2', 'warn')
        session.flash('err1', 'error')
        session.flash('err2', 'error')
        self.assertEqual(session['_f_warn'], ['warn1', 'warn2'])

    def test_pop_flash_default_queue(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        queue = ['one', 'two']
        session['_f_'] = queue
        result = session.pop_flash()
        self.assertEqual(result, queue)
        self.assertEqual(session.get('_f_'), None)

    def test_pop_flash_nodefault_queue(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        queue = ['one', 'two']
        session['_f_error'] = queue
        result = session.pop_flash('error')
        self.assertEqual(result, queue)
        self.assertEqual(session.get('_f_error'), None)

    def test_peek_flash_default_queue(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        queue = ['one', 'two']
        session['_f_'] = queue
        result = session.peek_flash()
        self.assertEqual(result, queue)
        self.assertEqual(session.get('_f_'), queue)

    def test_peek_flash_nodefault_queue(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        queue = ['one', 'two']
        session['_f_error'] = queue
        result = session.peek_flash('error')
        self.assertEqual(result, queue)
        self.assertEqual(session.get('_f_error'), queue)

    def test_new_csrf_token(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        token = session.new_csrf_token()
        self.assertEqual(token, session['_csrft_'])

    def test_get_csrf_token(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        session['_csrft_'] = 'token'
        token = session.get_csrf_token()
        self.assertEqual(token, 'token')
        self.assertTrue('_csrft_' in session)

    def test_get_csrf_token_new(self):
        request = testing.DummyRequest()
        session = self._makeOne(request)
        token = session.get_csrf_token()
        self.assertTrue(token)
        self.assertTrue('_csrft_' in session)

    def test_no_set_cookie_with_exception(self):
        import webob
        request = testing.DummyRequest()
        request.exception = True
        session = self._makeOne(request, set_on_exception=False)
        session['a'] = 1
        callbacks = request.response_callbacks
        self.assertEqual(len(callbacks), 1)
        response = webob.Response()
        result = callbacks[0](request, response)
        self.assertEqual(result, None)
        self.assertFalse('Set-Cookie' in dict(response.headerlist))

    def test_set_cookie_with_exception(self):
        import webob
        request = testing.DummyRequest()
        request.exception = True
        session = self._makeOne(request)
        session['a'] = 1
        callbacks = request.response_callbacks
        self.assertEqual(len(callbacks), 1)
        response = webob.Response()
        result = callbacks[0](request, response)
        self.assertEqual(result, None)
        self.assertTrue('Set-Cookie' in dict(response.headerlist))

    def test_cookie_is_set(self):
        import webob
        request = testing.DummyRequest()
        session = self._makeOne(request)
        session['a'] = 1
        callbacks = request.response_callbacks
        self.assertEqual(len(callbacks), 1)
        response = webob.Response()
        result = callbacks[0](request, response)
        self.assertEqual(result, None)
        self.assertTrue('Set-Cookie' in dict(response.headerlist))

class TestBaseCookieSession(SharedCookieSessionTests, unittest.TestCase):
    def _makeOne(self, request, **kw):
        from pyramid.session import BaseCookieSessionFactory
        serializer = DummySerializer()
        return BaseCookieSessionFactory(serializer, **kw)(request)

    def _serialize(self, value):
        return base64.b64encode(json.dumps(value).encode('utf-8'))

    def test_reissue_not_triggered(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time(), 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request, reissue_time=1)
        self.assertEqual(session['state'], 1)
        self.assertFalse(session._dirty)

    def test_reissue_never(self):
        request = testing.DummyRequest()
        cookieval = self._serialize((0, 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request, reissue_time=None, timeout=None)
        self.assertEqual(session['state'], 1)
        self.assertFalse(session._dirty)

    def test_reissue_str_triggered(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time() - 2, 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request, reissue_time='0')
        self.assertEqual(session['state'], 1)
        self.assertTrue(session._dirty)

    def test_reissue_invalid(self):
        request = testing.DummyRequest()
        self.assertRaises(ValueError, self._makeOne, request, reissue_time='invalid value')

    def test_cookie_max_age_invalid(self):
        request = testing.DummyRequest()
        self.assertRaises(ValueError, self._makeOne, request, max_age='invalid value')

class TestSignedCookieSession(SharedCookieSessionTests, unittest.TestCase):
    def _makeOne(self, request, **kw):
        from pyramid.session import SignedCookieSessionFactory
        kw.setdefault('secret', 'secret')
        return SignedCookieSessionFactory(**kw)(request)

    def _serialize(self, value, salt=b'pyramid.session.', hashalg='sha512'):
        import base64
        import hashlib
        import hmac
        import pickle

        digestmod = lambda: hashlib.new(hashalg)
        cstruct = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
        sig = hmac.new(salt + b'secret', cstruct, digestmod).digest()
        return base64.urlsafe_b64encode(sig + cstruct).rstrip(b'=')

    def test_reissue_not_triggered(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time(), 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request, reissue_time=1)
        self.assertEqual(session['state'], 1)
        self.assertFalse(session._dirty)

    def test_reissue_never(self):
        request = testing.DummyRequest()
        cookieval = self._serialize((0, 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request, reissue_time=None, timeout=None)
        self.assertEqual(session['state'], 1)
        self.assertFalse(session._dirty)

    def test_reissue_str_triggered(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time() - 2, 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request, reissue_time='0')
        self.assertEqual(session['state'], 1)
        self.assertTrue(session._dirty)

    def test_reissue_invalid(self):
        request = testing.DummyRequest()
        self.assertRaises(ValueError, self._makeOne, request, reissue_time='invalid value')

    def test_cookie_max_age_invalid(self):
        request = testing.DummyRequest()
        self.assertRaises(ValueError, self._makeOne, request, max_age='invalid value')

    def test_custom_salt(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time(), 0, {'state': 1}), salt=b'f.')
        request.cookies['session'] = cookieval
        session = self._makeOne(request, salt=b'f.')
        self.assertEqual(session['state'], 1)

    def test_salt_mismatch(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time(), 0, {'state': 1}), salt=b'f.')
        request.cookies['session'] = cookieval
        session = self._makeOne(request, salt=b'g.')
        self.assertEqual(session, {})

    def test_custom_hashalg(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time(), 0, {'state': 1}),
                                    hashalg='sha1')
        request.cookies['session'] = cookieval
        session = self._makeOne(request, hashalg='sha1')
        self.assertEqual(session['state'], 1)

    def test_hashalg_mismatch(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time(), 0, {'state': 1}),
                                    hashalg='sha1')
        request.cookies['session'] = cookieval
        session = self._makeOne(request, hashalg='sha256')
        self.assertEqual(session, {})

    def test_secret_mismatch(self):
        import time
        request = testing.DummyRequest()
        cookieval = self._serialize((time.time(), 0, {'state': 1}))
        request.cookies['session'] = cookieval
        session = self._makeOne(request, secret='evilsecret')
        self.assertEqual(session, {})

    def test_custom_serializer(self):
        import base64
        from hashlib import sha512
        import hmac
        import time
        request = testing.DummyRequest()
        serializer = DummySerializer()
        cstruct = serializer.dumps((time.time(), 0, {'state': 1}))
        sig = hmac.new(b'pyramid.session.secret', cstruct, sha512).digest()
        cookieval = base64.urlsafe_b64encode(sig + cstruct).rstrip(b'=')
        request.cookies['session'] = cookieval
        session = self._makeOne(request, serializer=serializer)
        self.assertEqual(session['state'], 1)

    def test_invalid_data_size(self):
        from hashlib import sha512
        import base64
        request = testing.DummyRequest()
        num_bytes = sha512().digest_size - 1
        cookieval = base64.b64encode(b' ' * num_bytes)
        request.cookies['session'] = cookieval
        session = self._makeOne(request)
        self.assertEqual(session, {})

    def test_very_long_key(self):
        verylongkey = b'a' * 1024
        import webob
        request = testing.DummyRequest()
        session = self._makeOne(request, secret=verylongkey)
        session['a'] = 1
        callbacks = request.response_callbacks
        self.assertEqual(len(callbacks), 1)
        response = webob.Response()

        try:
            result = callbacks[0](request, response)
        except TypeError: # pragma: no cover
            self.fail('HMAC failed to initialize due to key length.')

        self.assertEqual(result, None)
        self.assertTrue('Set-Cookie' in dict(response.headerlist))

class TestUnencryptedCookieSession(SharedCookieSessionTests, unittest.TestCase):
    def setUp(self):
        super(TestUnencryptedCookieSession, self).setUp()
        from zope.deprecation import __show__
        __show__.off()

    def tearDown(self):
        super(TestUnencryptedCookieSession, self).tearDown()
        from zope.deprecation import __show__
        __show__.on()
        
    def _makeOne(self, request, **kw):
        from pyramid.session import UnencryptedCookieSessionFactoryConfig
        self._rename_cookie_var(kw, 'path', 'cookie_path')
        self._rename_cookie_var(kw, 'domain', 'cookie_domain')
        self._rename_cookie_var(kw, 'secure', 'cookie_secure')
        self._rename_cookie_var(kw, 'httponly', 'cookie_httponly')
        self._rename_cookie_var(kw, 'set_on_exception', 'cookie_on_exception')
        return UnencryptedCookieSessionFactoryConfig('secret', **kw)(request)

    def _rename_cookie_var(self, kw, src, dest):
        if src in kw:
            kw.setdefault(dest, kw.pop(src))

    def _serialize(self, value):
        from pyramid.compat import bytes_
        from pyramid.session import signed_serialize
        return bytes_(signed_serialize(value, 'secret'))

    def test_serialize_option(self):
        from pyramid.response import Response
        secret = 'secret'
        request = testing.DummyRequest()
        session = self._makeOne(request,
            signed_serialize=dummy_signed_serialize)
        session['key'] = 'value'
        response = Response()
        self.assertEqual(session._set_cookie(response), True)
        cookie = response.headerlist[-1][1]
        expected_cookieval = dummy_signed_serialize(
            (session.accessed, session.created, {'key': 'value'}), secret)
        response = Response()
        response.set_cookie('session', expected_cookieval)
        expected_cookie = response.headerlist[-1][1]
        self.assertEqual(cookie, expected_cookie)

    def test_deserialize_option(self):
        import time
        secret = 'secret'
        request = testing.DummyRequest()
        accessed = time.time()
        state = {'key': 'value'}
        cookieval = dummy_signed_serialize((accessed, accessed, state), secret)
        request.cookies['session'] = cookieval
        session = self._makeOne(request,
            signed_deserialize=dummy_signed_deserialize)
        self.assertEqual(dict(session), state)

def dummy_signed_serialize(data, secret):
    import base64
    from pyramid.compat import pickle, bytes_
    pickled = pickle.dumps(data)
    return base64.b64encode(bytes_(secret)) + base64.b64encode(pickled)

def dummy_signed_deserialize(serialized, secret):
    import base64
    from pyramid.compat import pickle, bytes_
    serialized_data = base64.b64decode(
        serialized[len(base64.b64encode(bytes_(secret))):])
    return pickle.loads(serialized_data)

class Test_manage_accessed(unittest.TestCase):
    def _makeOne(self, wrapped):
        from pyramid.session import manage_accessed
        return manage_accessed(wrapped)

    def test_accessed_set(self):
        request = testing.DummyRequest()
        session = DummySessionFactory(request)
        session.renewed = 0
        wrapper = self._makeOne(session.__class__.get)
        wrapper(session, 'a')
        self.assertNotEqual(session.accessed, None)
        self.assertTrue(session._dirty)

    def test_accessed_without_renew(self):
        import time
        request = testing.DummyRequest()
        session = DummySessionFactory(request)
        session._reissue_time = 5
        session.renewed = time.time()
        wrapper = self._makeOne(session.__class__.get)
        wrapper(session, 'a')
        self.assertNotEqual(session.accessed, None)
        self.assertFalse(session._dirty)

    def test_already_dirty(self):
        request = testing.DummyRequest()
        session = DummySessionFactory(request)
        session.renewed = 0
        session._dirty = True
        session['a'] = 1
        wrapper = self._makeOne(session.__class__.get)
        self.assertEqual(wrapper.__doc__, session.get.__doc__)
        result = wrapper(session, 'a')
        self.assertEqual(result, 1)
        callbacks = request.response_callbacks
        if callbacks is not None: self.assertEqual(len(callbacks), 0)

class Test_manage_changed(unittest.TestCase):
    def _makeOne(self, wrapped):
        from pyramid.session import manage_changed
        return manage_changed(wrapped)

    def test_it(self):
        request = testing.DummyRequest()
        session = DummySessionFactory(request)
        wrapper = self._makeOne(session.__class__.__setitem__)
        wrapper(session, 'a', 1)
        self.assertNotEqual(session.accessed, None)
        self.assertTrue(session._dirty)

def serialize(data, secret):
    import hmac
    import base64
    from hashlib import sha1
    from pyramid.compat import bytes_
    from pyramid.compat import native_
    from pyramid.compat import pickle
    pickled = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
    sig = hmac.new(bytes_(secret, 'utf-8'), pickled, sha1).hexdigest()
    return sig + native_(base64.b64encode(pickled))

class Test_signed_serialize(unittest.TestCase):
    def _callFUT(self, data, secret):
        from pyramid.session import signed_serialize
        return signed_serialize(data, secret)

    def test_it(self):
        expected = serialize('123', 'secret')
        result = self._callFUT('123', 'secret')
        self.assertEqual(result, expected)

    def test_it_with_highorder_secret(self):
        secret = b'\xce\xb1\xce\xb2\xce\xb3\xce\xb4'.decode('utf-8')
        expected = serialize('123', secret)
        result = self._callFUT('123', secret)
        self.assertEqual(result, expected)

    def test_it_with_latin1_secret(self):
        secret = b'La Pe\xc3\xb1a'
        expected = serialize('123', secret)
        result = self._callFUT('123', secret.decode('latin-1'))
        self.assertEqual(result, expected)
        
class Test_signed_deserialize(unittest.TestCase):
    def _callFUT(self, serialized, secret, hmac=None):
        if hmac is None:
            import hmac
        from pyramid.session import signed_deserialize
        return signed_deserialize(serialized, secret, hmac=hmac)

    def test_it(self):
        serialized = serialize('123', 'secret')
        result = self._callFUT(serialized, 'secret')
        self.assertEqual(result, '123')

    def test_invalid_bits(self):
        serialized = serialize('123', 'secret')
        self.assertRaises(ValueError, self._callFUT, serialized, 'seekrit')

    def test_invalid_len(self):
        class hmac(object):
            def new(self, *arg):
                return self
            def hexdigest(self):
                return '1234'
        serialized = serialize('123', 'secret123')
        self.assertRaises(ValueError, self._callFUT, serialized, 'secret',
                          hmac=hmac())
        
    def test_it_bad_encoding(self):
        serialized = 'bad' + serialize('123', 'secret')
        self.assertRaises(ValueError, self._callFUT, serialized, 'secret')

    def test_it_with_highorder_secret(self):
        secret = b'\xce\xb1\xce\xb2\xce\xb3\xce\xb4'.decode('utf-8')
        serialized = serialize('123', secret)
        result = self._callFUT(serialized, secret)
        self.assertEqual(result, '123')

    # bwcompat with pyramid <= 1.5b1 where latin1 is the default
    def test_it_with_latin1_secret(self):
        secret = b'La Pe\xc3\xb1a'
        serialized = serialize('123', secret)
        result = self._callFUT(serialized, secret.decode('latin-1'))
        self.assertEqual(result, '123')

class Test_check_csrf_token(unittest.TestCase):
    def _callFUT(self, *args, **kwargs):
        from ..session import check_csrf_token
        return check_csrf_token(*args, **kwargs)

    def test_success_token(self):
        request = testing.DummyRequest()
        request.method = "POST"
        request.POST = {'csrf_token': request.session.get_csrf_token()}
        self.assertEqual(self._callFUT(request, token='csrf_token'), True)

    def test_success_header(self):
        request = testing.DummyRequest()
        request.headers['X-CSRF-Token'] = request.session.get_csrf_token()
        self.assertEqual(self._callFUT(request, header='X-CSRF-Token'), True)

    def test_success_default_token(self):
        request = testing.DummyRequest()
        request.method = "POST"
        request.POST = {'csrf_token': request.session.get_csrf_token()}
        self.assertEqual(self._callFUT(request), True)

    def test_success_default_header(self):
        request = testing.DummyRequest()
        request.headers['X-CSRF-Token'] = request.session.get_csrf_token()
        self.assertEqual(self._callFUT(request), True)

    def test_failure_raises(self):
        from pyramid.exceptions import BadCSRFToken
        request = testing.DummyRequest()
        self.assertRaises(BadCSRFToken, self._callFUT, request,
                          'csrf_token')

    def test_failure_no_raises(self):
        request = testing.DummyRequest()
        result = self._callFUT(request, 'csrf_token', raises=False)
        self.assertEqual(result, False)

    def test_token_differing_types(self):
        from pyramid.compat import text_
        request = testing.DummyRequest()
        request.method = "POST"
        request.session['_csrft_'] = text_('foo')
        request.POST = {'csrf_token': b'foo'}
        self.assertEqual(self._callFUT(request, token='csrf_token'), True)


class Test_check_csrf_origin(unittest.TestCase):

    def _callFUT(self, *args, **kwargs):
        from ..session import check_csrf_origin
        return check_csrf_origin(*args, **kwargs)

    def test_success_with_http(self):
        request = testing.DummyRequest()
        request.scheme = "http"
        self.assertTrue(self._callFUT(request))

    def test_success_with_https_and_referrer(self):
        request = testing.DummyRequest()
        request.scheme = "https"
        request.host = "example.com"
        request.host_port = "443"
        request.referrer = "https://example.com/login/"
        request.registry.settings = {}
        self.assertTrue(self._callFUT(request))

    def test_success_with_https_and_origin(self):
        request = testing.DummyRequest()
        request.scheme = "https"
        request.host = "example.com"
        request.host_port = "443"
        request.headers = {"Origin": "https://example.com/"}
        request.referrer = "https://not-example.com/"
        request.registry.settings = {}
        self.assertTrue(self._callFUT(request))

    def test_success_with_additional_trusted_host(self):
        request = testing.DummyRequest()
        request.scheme = "https"
        request.host = "example.com"
        request.host_port = "443"
        request.referrer = "https://not-example.com/login/"
        request.registry.settings = {
            "pyramid.csrf_trusted_origins": ["not-example.com"],
        }
        self.assertTrue(self._callFUT(request))

    def test_success_with_nonstandard_port(self):
        request = testing.DummyRequest()
        request.scheme = "https"
        request.host = "example.com:8080"
        request.host_port = "8080"
        request.referrer = "https://example.com:8080/login/"
        request.registry.settings = {}
        self.assertTrue(self._callFUT(request))

    def test_fails_with_wrong_host(self):
        from pyramid.exceptions import BadCSRFOrigin
        request = testing.DummyRequest()
        request.scheme = "https"
        request.host = "example.com"
        request.host_port = "443"
        request.referrer = "https://not-example.com/login/"
        request.registry.settings = {}
        self.assertRaises(BadCSRFOrigin, self._callFUT, request)
        self.assertFalse(self._callFUT(request, raises=False))

    def test_fails_with_no_origin(self):
        from pyramid.exceptions import BadCSRFOrigin
        request = testing.DummyRequest()
        request.scheme = "https"
        request.referrer = None
        self.assertRaises(BadCSRFOrigin, self._callFUT, request)
        self.assertFalse(self._callFUT(request, raises=False))

    def test_fails_when_http_to_https(self):
        from pyramid.exceptions import BadCSRFOrigin
        request = testing.DummyRequest()
        request.scheme = "https"
        request.host = "example.com"
        request.host_port = "443"
        request.referrer = "http://example.com/evil/"
        request.registry.settings = {}
        self.assertRaises(BadCSRFOrigin, self._callFUT, request)
        self.assertFalse(self._callFUT(request, raises=False))

    def test_fails_with_nonstandard_port(self):
        from pyramid.exceptions import BadCSRFOrigin
        request = testing.DummyRequest()
        request.scheme = "https"
        request.host = "example.com:8080"
        request.host_port = "8080"
        request.referrer = "https://example.com/login/"
        request.registry.settings = {}
        self.assertRaises(BadCSRFOrigin, self._callFUT, request)
        self.assertFalse(self._callFUT(request, raises=False))


class DummySerializer(object):
    def dumps(self, value):
        return base64.b64encode(json.dumps(value).encode('utf-8'))

    def loads(self, value):
        try:
            return json.loads(base64.b64decode(value).decode('utf-8'))

        # base64.b64decode raises a TypeError on py2 instead of a ValueError
        # and a ValueError is required for the session to handle it properly
        except TypeError:
            raise ValueError

class DummySessionFactory(dict):
    _dirty = False
    _cookie_name = 'session'
    _cookie_max_age = None
    _cookie_path = '/'
    _cookie_domain = None
    _cookie_secure = False
    _cookie_httponly = False
    _timeout = 1200
    _reissue_time = 0

    def __init__(self, request):
        self.request = request
        dict.__init__(self, {})

    def changed(self):
        self._dirty = True

class DummyResponse(object):
    def __init__(self):
        self.headerlist = []
