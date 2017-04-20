import unittest
import io

class TestThreadedTaskDispatcher(unittest.TestCase):

    def _makeOne(self):
        from waitress.task import ThreadedTaskDispatcher
        return ThreadedTaskDispatcher()

    def test_handler_thread_task_is_None(self):
        inst = self._makeOne()
        inst.threads[0] = True
        inst.queue.put(None)
        inst.handler_thread(0)
        self.assertEqual(inst.stop_count, -1)
        self.assertEqual(inst.threads, {})

    def test_handler_thread_task_raises(self):
        from waitress.task import JustTesting
        inst = self._makeOne()
        inst.threads[0] = True
        inst.logger = DummyLogger()
        task = DummyTask(JustTesting)
        inst.logger = DummyLogger()
        inst.queue.put(task)
        inst.handler_thread(0)
        self.assertEqual(inst.stop_count, -1)
        self.assertEqual(inst.threads, {})
        self.assertEqual(len(inst.logger.logged), 1)

    def test_set_thread_count_increase(self):
        inst = self._makeOne()
        L = []
        inst.start_new_thread = lambda *x: L.append(x)
        inst.set_thread_count(1)
        self.assertEqual(L, [(inst.handler_thread, (0,))])

    def test_set_thread_count_increase_with_existing(self):
        inst = self._makeOne()
        L = []
        inst.threads = {0: 1}
        inst.start_new_thread = lambda *x: L.append(x)
        inst.set_thread_count(2)
        self.assertEqual(L, [(inst.handler_thread, (1,))])

    def test_set_thread_count_decrease(self):
        inst = self._makeOne()
        inst.threads = {'a': 1, 'b': 2}
        inst.set_thread_count(1)
        self.assertEqual(inst.queue.qsize(), 1)
        self.assertEqual(inst.queue.get(), None)

    def test_set_thread_count_same(self):
        inst = self._makeOne()
        L = []
        inst.start_new_thread = lambda *x: L.append(x)
        inst.threads = {0: 1}
        inst.set_thread_count(1)
        self.assertEqual(L, [])

    def test_add_task(self):
        task = DummyTask()
        inst = self._makeOne()
        inst.add_task(task)
        self.assertEqual(inst.queue.qsize(), 1)
        self.assertTrue(task.deferred)

    def test_add_task_defer_raises(self):
        task = DummyTask(ValueError)
        inst = self._makeOne()
        self.assertRaises(ValueError, inst.add_task, task)
        self.assertEqual(inst.queue.qsize(), 0)
        self.assertTrue(task.deferred)
        self.assertTrue(task.cancelled)

    def test_shutdown_one_thread(self):
        inst = self._makeOne()
        inst.threads[0] = 1
        inst.logger = DummyLogger()
        task = DummyTask()
        inst.queue.put(task)
        self.assertEqual(inst.shutdown(timeout=.01), True)
        self.assertEqual(inst.logger.logged, ['1 thread(s) still running'])
        self.assertEqual(task.cancelled, True)

    def test_shutdown_no_threads(self):
        inst = self._makeOne()
        self.assertEqual(inst.shutdown(timeout=.01), True)

    def test_shutdown_no_cancel_pending(self):
        inst = self._makeOne()
        self.assertEqual(inst.shutdown(cancel_pending=False, timeout=.01),
                         False)

class TestTask(unittest.TestCase):

    def _makeOne(self, channel=None, request=None):
        if channel is None:
            channel = DummyChannel()
        if request is None:
            request = DummyParser()
        from waitress.task import Task
        return Task(channel, request)

    def test_ctor_version_not_in_known(self):
        request = DummyParser()
        request.version = '8.4'
        inst = self._makeOne(request=request)
        self.assertEqual(inst.version, '1.0')

    def test_cancel(self):
        inst = self._makeOne()
        inst.cancel()
        self.assertTrue(inst.close_on_finish)

    def test_defer(self):
        inst = self._makeOne()
        self.assertEqual(inst.defer(), None)

    def test_build_response_header_bad_http_version(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '8.4'
        self.assertRaises(AssertionError, inst.build_response_header)

    def test_build_response_header_v10_keepalive_no_content_length(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.request.headers['CONNECTION'] = 'keep-alive'
        inst.version = '1.0'
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], b'HTTP/1.0 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')
        self.assertEqual(inst.close_on_finish, True)
        self.assertTrue(('Connection', 'close') in inst.response_headers)

    def test_build_response_header_v10_keepalive_with_content_length(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.request.headers['CONNECTION'] = 'keep-alive'
        inst.response_headers = [('Content-Length', '10')]
        inst.version = '1.0'
        inst.content_length = 0
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], b'HTTP/1.0 200 OK')
        self.assertEqual(lines[1], b'Connection: Keep-Alive')
        self.assertEqual(lines[2], b'Content-Length: 10')
        self.assertTrue(lines[3].startswith(b'Date:'))
        self.assertEqual(lines[4], b'Server: waitress')
        self.assertEqual(inst.close_on_finish, False)

    def test_build_response_header_v11_connection_closed_by_client(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '1.1'
        inst.request.headers['CONNECTION'] = 'close'
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], b'HTTP/1.1 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')
        self.assertEqual(lines[4], b'Transfer-Encoding: chunked')
        self.assertTrue(('Connection', 'close') in inst.response_headers)
        self.assertEqual(inst.close_on_finish, True)

    def test_build_response_header_v11_connection_keepalive_by_client(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.request.headers['CONNECTION'] = 'keep-alive'
        inst.version = '1.1'
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], b'HTTP/1.1 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')
        self.assertEqual(lines[4], b'Transfer-Encoding: chunked')
        self.assertTrue(('Connection', 'close') in inst.response_headers)
        self.assertEqual(inst.close_on_finish, True)

    def test_build_response_header_v11_200_no_content_length(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '1.1'
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], b'HTTP/1.1 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')
        self.assertEqual(lines[4], b'Transfer-Encoding: chunked')
        self.assertEqual(inst.close_on_finish, True)
        self.assertTrue(('Connection', 'close') in inst.response_headers)

    def test_build_response_header_via_added(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '1.0'
        inst.response_headers = [('Server', 'abc')]
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], b'HTTP/1.0 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: abc')
        self.assertEqual(lines[4], b'Via: waitress')

    def test_build_response_header_date_exists(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '1.0'
        inst.response_headers = [('Date', 'date')]
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], b'HTTP/1.0 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')

    def test_build_response_header_preexisting_content_length(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '1.1'
        inst.content_length = 100
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], b'HTTP/1.1 200 OK')
        self.assertEqual(lines[1], b'Content-Length: 100')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')

    def test_remove_content_length_header(self):
        inst = self._makeOne()
        inst.response_headers = [('Content-Length', '70')]
        inst.remove_content_length_header()
        self.assertEqual(inst.response_headers, [])

    def test_start(self):
        inst = self._makeOne()
        inst.start()
        self.assertTrue(inst.start_time)

    def test_finish_didnt_write_header(self):
        inst = self._makeOne()
        inst.wrote_header = False
        inst.complete = True
        inst.finish()
        self.assertTrue(inst.channel.written)

    def test_finish_wrote_header(self):
        inst = self._makeOne()
        inst.wrote_header = True
        inst.finish()
        self.assertFalse(inst.channel.written)

    def test_finish_chunked_response(self):
        inst = self._makeOne()
        inst.wrote_header = True
        inst.chunked_response = True
        inst.finish()
        self.assertEqual(inst.channel.written, b'0\r\n\r\n')

    def test_write_wrote_header(self):
        inst = self._makeOne()
        inst.wrote_header = True
        inst.complete = True
        inst.content_length = 3
        inst.write(b'abc')
        self.assertEqual(inst.channel.written, b'abc')

    def test_write_header_not_written(self):
        inst = self._makeOne()
        inst.wrote_header = False
        inst.complete = True
        inst.write(b'abc')
        self.assertTrue(inst.channel.written)
        self.assertEqual(inst.wrote_header, True)

    def test_write_start_response_uncalled(self):
        inst = self._makeOne()
        self.assertRaises(RuntimeError, inst.write, b'')

    def test_write_chunked_response(self):
        inst = self._makeOne()
        inst.wrote_header = True
        inst.chunked_response = True
        inst.complete = True
        inst.write(b'abc')
        self.assertEqual(inst.channel.written, b'3\r\nabc\r\n')

    def test_write_preexisting_content_length(self):
        inst = self._makeOne()
        inst.wrote_header = True
        inst.complete = True
        inst.content_length = 1
        inst.logger = DummyLogger()
        inst.write(b'abc')
        self.assertTrue(inst.channel.written)
        self.assertEqual(inst.logged_write_excess, True)
        self.assertEqual(len(inst.logger.logged), 1)

class TestWSGITask(unittest.TestCase):

    def _makeOne(self, channel=None, request=None):
        if channel is None:
            channel = DummyChannel()
        if request is None:
            request = DummyParser()
        from waitress.task import WSGITask
        return WSGITask(channel, request)

    def test_service(self):
        inst = self._makeOne()
        def execute():
            inst.executed = True
        inst.execute = execute
        inst.complete = True
        inst.service()
        self.assertTrue(inst.start_time)
        self.assertTrue(inst.close_on_finish)
        self.assertTrue(inst.channel.written)
        self.assertEqual(inst.executed, True)

    def test_service_server_raises_socket_error(self):
        import socket
        inst = self._makeOne()
        def execute():
            raise socket.error
        inst.execute = execute
        self.assertRaises(socket.error, inst.service)
        self.assertTrue(inst.start_time)
        self.assertTrue(inst.close_on_finish)
        self.assertFalse(inst.channel.written)

    def test_execute_app_calls_start_response_twice_wo_exc_info(self):
        def app(environ, start_response):
            start_response('200 OK', [])
            start_response('200 OK', [])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(AssertionError, inst.execute)

    def test_execute_app_calls_start_response_w_exc_info_complete(self):
        def app(environ, start_response):
            start_response('200 OK', [], [ValueError, ValueError(), None])
            return [b'a']
        inst = self._makeOne()
        inst.complete = True
        inst.channel.server.application = app
        inst.execute()
        self.assertTrue(inst.complete)
        self.assertEqual(inst.status, '200 OK')
        self.assertTrue(inst.channel.written)

    def test_execute_app_calls_start_response_w_excinf_headers_unwritten(self):
        def app(environ, start_response):
            start_response('200 OK', [], [ValueError, None, None])
            return [b'a']
        inst = self._makeOne()
        inst.wrote_header = False
        inst.channel.server.application = app
        inst.response_headers = [('a', 'b')]
        inst.execute()
        self.assertTrue(inst.complete)
        self.assertEqual(inst.status, '200 OK')
        self.assertTrue(inst.channel.written)
        self.assertFalse(('a','b') in inst.response_headers)

    def test_execute_app_calls_start_response_w_excinf_headers_written(self):
        def app(environ, start_response):
            start_response('200 OK', [], [ValueError, ValueError(), None])
        inst = self._makeOne()
        inst.complete = True
        inst.wrote_header = True
        inst.channel.server.application = app
        self.assertRaises(ValueError, inst.execute)

    def test_execute_bad_header_key(self):
        def app(environ, start_response):
            start_response('200 OK', [(None, 'a')])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(AssertionError, inst.execute)

    def test_execute_bad_header_value(self):
        def app(environ, start_response):
            start_response('200 OK', [('a', None)])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(AssertionError, inst.execute)

    def test_execute_hopbyhop_header(self):
        def app(environ, start_response):
            start_response('200 OK', [('Connection', 'close')])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(AssertionError, inst.execute)

    def test_execute_bad_header_value_control_characters(self):
        def app(environ, start_response):
            start_response('200 OK', [('a', '\n')])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(ValueError, inst.execute)

    def test_execute_bad_header_name_control_characters(self):
        def app(environ, start_response):
            start_response('200 OK', [('a\r', 'value')])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(ValueError, inst.execute)

    def test_execute_bad_status_control_characters(self):
        def app(environ, start_response):
            start_response('200 OK\r', [])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(ValueError, inst.execute)

    def test_preserve_header_value_order(self):
        def app(environ, start_response):
            write = start_response('200 OK', [('C', 'b'), ('A', 'b'), ('A', 'a')])
            write(b'abc')
            return []
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertTrue(b'A: b\r\nA: a\r\nC: b\r\n' in inst.channel.written)

    def test_execute_bad_status_value(self):
        def app(environ, start_response):
            start_response(None, [])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(AssertionError, inst.execute)

    def test_execute_with_content_length_header(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '1')])
            return [b'a']
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertEqual(inst.content_length, 1)

    def test_execute_app_calls_write(self):
        def app(environ, start_response):
            write = start_response('200 OK', [('Content-Length', '3')])
            write(b'abc')
            return []
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertEqual(inst.channel.written[-3:], b'abc')

    def test_execute_app_returns_len1_chunk_without_cl(self):
        def app(environ, start_response):
            start_response('200 OK', [])
            return [b'abc']
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertEqual(inst.content_length, 3)

    def test_execute_app_returns_empty_chunk_as_first(self):
        def app(environ, start_response):
            start_response('200 OK', [])
            return ['', b'abc']
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertEqual(inst.content_length, None)

    def test_execute_app_returns_too_many_bytes(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '1')])
            return [b'abc']
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.logger = DummyLogger()
        inst.execute()
        self.assertEqual(inst.close_on_finish, True)
        self.assertEqual(len(inst.logger.logged), 1)

    def test_execute_app_returns_too_few_bytes(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '3')])
            return [b'a']
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.logger = DummyLogger()
        inst.execute()
        self.assertEqual(inst.close_on_finish, True)
        self.assertEqual(len(inst.logger.logged), 1)

    def test_execute_app_do_not_warn_on_head(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '3')])
            return [b'']
        inst = self._makeOne()
        inst.request.command = 'HEAD'
        inst.channel.server.application = app
        inst.logger = DummyLogger()
        inst.execute()
        self.assertEqual(inst.close_on_finish, True)
        self.assertEqual(len(inst.logger.logged), 0)

    def test_execute_app_returns_closeable(self):
        class closeable(list):
            def close(self):
                self.closed = True
        foo = closeable([b'abc'])
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '3')])
            return foo
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertEqual(foo.closed, True)

    def test_execute_app_returns_filewrapper_prepare_returns_True(self):
        from waitress.buffers import ReadOnlyFileBasedBuffer
        f = io.BytesIO(b'abc')
        app_iter = ReadOnlyFileBasedBuffer(f, 8192)
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '3')])
            return app_iter
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertTrue(inst.channel.written) # header
        self.assertEqual(inst.channel.otherdata, [app_iter])

    def test_execute_app_returns_filewrapper_prepare_returns_True_nocl(self):
        from waitress.buffers import ReadOnlyFileBasedBuffer
        f = io.BytesIO(b'abc')
        app_iter = ReadOnlyFileBasedBuffer(f, 8192)
        def app(environ, start_response):
            start_response('200 OK', [])
            return app_iter
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertTrue(inst.channel.written) # header
        self.assertEqual(inst.channel.otherdata, [app_iter])
        self.assertEqual(inst.content_length, 3)

    def test_execute_app_returns_filewrapper_prepare_returns_True_badcl(self):
        from waitress.buffers import ReadOnlyFileBasedBuffer
        f = io.BytesIO(b'abc')
        app_iter = ReadOnlyFileBasedBuffer(f, 8192)
        def app(environ, start_response):
            start_response('200 OK', [])
            return app_iter
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.content_length = 10
        inst.response_headers = [('Content-Length', '10')]
        inst.execute()
        self.assertTrue(inst.channel.written) # header
        self.assertEqual(inst.channel.otherdata, [app_iter])
        self.assertEqual(inst.content_length, 3)
        self.assertEqual(dict(inst.response_headers)['Content-Length'], '3')

    def test_get_environment_already_cached(self):
        inst = self._makeOne()
        inst.environ = object()
        self.assertEqual(inst.get_environment(), inst.environ)

    def test_get_environment_path_startswith_more_than_one_slash(self):
        inst = self._makeOne()
        request = DummyParser()
        request.path = '///abc'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['PATH_INFO'], '/abc')

    def test_get_environment_path_empty(self):
        inst = self._makeOne()
        request = DummyParser()
        request.path = ''
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['PATH_INFO'], '')

    def test_get_environment_no_query(self):
        inst = self._makeOne()
        request = DummyParser()
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['QUERY_STRING'], '')

    def test_get_environment_with_query(self):
        inst = self._makeOne()
        request = DummyParser()
        request.query = 'abc'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['QUERY_STRING'], 'abc')

    def test_get_environ_with_url_prefix_miss(self):
        inst = self._makeOne()
        inst.channel.server.adj.url_prefix = '/foo'
        request = DummyParser()
        request.path = '/bar'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['PATH_INFO'], '/bar')
        self.assertEqual(environ['SCRIPT_NAME'], '/foo')

    def test_get_environ_with_url_prefix_hit(self):
        inst = self._makeOne()
        inst.channel.server.adj.url_prefix = '/foo'
        request = DummyParser()
        request.path = '/foo/fuz'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['PATH_INFO'], '/fuz')
        self.assertEqual(environ['SCRIPT_NAME'], '/foo')

    def test_get_environ_with_url_prefix_empty_path(self):
        inst = self._makeOne()
        inst.channel.server.adj.url_prefix = '/foo'
        request = DummyParser()
        request.path = '/foo'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['PATH_INFO'], '')
        self.assertEqual(environ['SCRIPT_NAME'], '/foo')

    def test_get_environment_values(self):
        import sys
        inst = self._makeOne()
        request = DummyParser()
        request.headers = {
            'CONTENT_TYPE': 'abc',
            'CONTENT_LENGTH': '10',
            'X_FOO': 'BAR',
            'CONNECTION': 'close',
        }
        request.query = 'abc'
        inst.request = request
        environ = inst.get_environment()

        # nail the keys of environ
        self.assertEqual(sorted(environ.keys()), [
            'CONTENT_LENGTH', 'CONTENT_TYPE', 'HTTP_CONNECTION', 'HTTP_X_FOO',
            'PATH_INFO', 'QUERY_STRING', 'REMOTE_ADDR', 'REQUEST_METHOD',
            'SCRIPT_NAME', 'SERVER_NAME', 'SERVER_PORT', 'SERVER_PROTOCOL',
            'SERVER_SOFTWARE', 'wsgi.errors', 'wsgi.file_wrapper', 'wsgi.input',
            'wsgi.multiprocess', 'wsgi.multithread', 'wsgi.run_once',
            'wsgi.url_scheme', 'wsgi.version'])

        self.assertEqual(environ['REQUEST_METHOD'], 'GET')
        self.assertEqual(environ['SERVER_PORT'], '80')
        self.assertEqual(environ['SERVER_NAME'], 'localhost')
        self.assertEqual(environ['SERVER_SOFTWARE'], 'waitress')
        self.assertEqual(environ['SERVER_PROTOCOL'], 'HTTP/1.0')
        self.assertEqual(environ['SCRIPT_NAME'], '')
        self.assertEqual(environ['HTTP_CONNECTION'], 'close')
        self.assertEqual(environ['PATH_INFO'], '/')
        self.assertEqual(environ['QUERY_STRING'], 'abc')
        self.assertEqual(environ['REMOTE_ADDR'], '127.0.0.1')
        self.assertEqual(environ['CONTENT_TYPE'], 'abc')
        self.assertEqual(environ['CONTENT_LENGTH'], '10')
        self.assertEqual(environ['HTTP_X_FOO'], 'BAR')
        self.assertEqual(environ['wsgi.version'], (1, 0))
        self.assertEqual(environ['wsgi.url_scheme'], 'http')
        self.assertEqual(environ['wsgi.errors'], sys.stderr)
        self.assertEqual(environ['wsgi.multithread'], True)
        self.assertEqual(environ['wsgi.multiprocess'], False)
        self.assertEqual(environ['wsgi.run_once'], False)
        self.assertEqual(environ['wsgi.input'], 'stream')
        self.assertEqual(inst.environ, environ)

    def test_get_environment_values_w_scheme_override_untrusted(self):
        inst = self._makeOne()
        request = DummyParser()
        request.headers = {
            'CONTENT_TYPE': 'abc',
            'CONTENT_LENGTH': '10',
            'X_FOO': 'BAR',
            'X_FORWARDED_PROTO': 'https',
            'CONNECTION': 'close',
        }
        request.query = 'abc'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['wsgi.url_scheme'], 'http')

    def test_get_environment_values_w_scheme_override_trusted(self):
        import sys
        inst = self._makeOne()
        inst.channel.addr = ['192.168.1.1']
        inst.channel.server.adj.trusted_proxy = '192.168.1.1'
        request = DummyParser()
        request.headers = {
            'CONTENT_TYPE': 'abc',
            'CONTENT_LENGTH': '10',
            'X_FOO': 'BAR',
            'X_FORWARDED_PROTO': 'https',
            'CONNECTION': 'close',
        }
        request.query = 'abc'
        inst.request = request
        environ = inst.get_environment()

        # nail the keys of environ
        self.assertEqual(sorted(environ.keys()), [
            'CONTENT_LENGTH', 'CONTENT_TYPE', 'HTTP_CONNECTION', 'HTTP_X_FOO',
            'PATH_INFO', 'QUERY_STRING', 'REMOTE_ADDR', 'REQUEST_METHOD',
            'SCRIPT_NAME', 'SERVER_NAME', 'SERVER_PORT', 'SERVER_PROTOCOL',
            'SERVER_SOFTWARE', 'wsgi.errors', 'wsgi.file_wrapper', 'wsgi.input',
            'wsgi.multiprocess', 'wsgi.multithread', 'wsgi.run_once',
            'wsgi.url_scheme', 'wsgi.version'])

        self.assertEqual(environ['REQUEST_METHOD'], 'GET')
        self.assertEqual(environ['SERVER_PORT'], '80')
        self.assertEqual(environ['SERVER_NAME'], 'localhost')
        self.assertEqual(environ['SERVER_SOFTWARE'], 'waitress')
        self.assertEqual(environ['SERVER_PROTOCOL'], 'HTTP/1.0')
        self.assertEqual(environ['SCRIPT_NAME'], '')
        self.assertEqual(environ['HTTP_CONNECTION'], 'close')
        self.assertEqual(environ['PATH_INFO'], '/')
        self.assertEqual(environ['QUERY_STRING'], 'abc')
        self.assertEqual(environ['REMOTE_ADDR'], '192.168.1.1')
        self.assertEqual(environ['CONTENT_TYPE'], 'abc')
        self.assertEqual(environ['CONTENT_LENGTH'], '10')
        self.assertEqual(environ['HTTP_X_FOO'], 'BAR')
        self.assertEqual(environ['wsgi.version'], (1, 0))
        self.assertEqual(environ['wsgi.url_scheme'], 'https')
        self.assertEqual(environ['wsgi.errors'], sys.stderr)
        self.assertEqual(environ['wsgi.multithread'], True)
        self.assertEqual(environ['wsgi.multiprocess'], False)
        self.assertEqual(environ['wsgi.run_once'], False)
        self.assertEqual(environ['wsgi.input'], 'stream')
        self.assertEqual(inst.environ, environ)

    def test_get_environment_values_w_bogus_scheme_override(self):
        inst = self._makeOne()
        inst.channel.addr = ['192.168.1.1']
        inst.channel.server.adj.trusted_proxy = '192.168.1.1'
        request = DummyParser()
        request.headers = {
            'CONTENT_TYPE': 'abc',
            'CONTENT_LENGTH': '10',
            'X_FOO': 'BAR',
            'X_FORWARDED_PROTO': 'http://p02n3e.com?url=http',
            'CONNECTION': 'close',
        }
        request.query = 'abc'
        inst.request = request
        self.assertRaises(ValueError, inst.get_environment)

class TestErrorTask(unittest.TestCase):

    def _makeOne(self, channel=None, request=None):
        if channel is None:
            channel = DummyChannel()
        if request is None:
            request = DummyParser()
            request.error = DummyError()
        from waitress.task import ErrorTask
        return ErrorTask(channel, request)

    def test_execute_http_10(self):
        inst = self._makeOne()
        inst.execute()
        lines = filter_lines(inst.channel.written)
        self.assertEqual(len(lines), 9)
        self.assertEqual(lines[0], b'HTTP/1.0 432 Too Ugly')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertEqual(lines[2], b'Content-Length: 43')
        self.assertEqual(lines[3], b'Content-Type: text/plain')
        self.assertTrue(lines[4])
        self.assertEqual(lines[5], b'Server: waitress')
        self.assertEqual(lines[6], b'Too Ugly')
        self.assertEqual(lines[7], b'body')
        self.assertEqual(lines[8], b'(generated by waitress)')

    def test_execute_http_11(self):
        inst = self._makeOne()
        inst.version = '1.1'
        inst.execute()
        lines = filter_lines(inst.channel.written)
        self.assertEqual(len(lines), 8)
        self.assertEqual(lines[0], b'HTTP/1.1 432 Too Ugly')
        self.assertEqual(lines[1], b'Content-Length: 43')
        self.assertEqual(lines[2], b'Content-Type: text/plain')
        self.assertTrue(lines[3])
        self.assertEqual(lines[4], b'Server: waitress')
        self.assertEqual(lines[5], b'Too Ugly')
        self.assertEqual(lines[6], b'body')
        self.assertEqual(lines[7], b'(generated by waitress)')

    def test_execute_http_11_close(self):
        inst = self._makeOne()
        inst.version = '1.1'
        inst.request.headers['CONNECTION'] = 'close'
        inst.execute()
        lines = filter_lines(inst.channel.written)
        self.assertEqual(len(lines), 9)
        self.assertEqual(lines[0], b'HTTP/1.1 432 Too Ugly')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertEqual(lines[2], b'Content-Length: 43')
        self.assertEqual(lines[3], b'Content-Type: text/plain')
        self.assertTrue(lines[4])
        self.assertEqual(lines[5], b'Server: waitress')
        self.assertEqual(lines[6], b'Too Ugly')
        self.assertEqual(lines[7], b'body')
        self.assertEqual(lines[8], b'(generated by waitress)')

    def test_execute_http_11_keep(self):
        inst = self._makeOne()
        inst.version = '1.1'
        inst.request.headers['CONNECTION'] = 'keep-alive'
        inst.execute()
        lines = filter_lines(inst.channel.written)
        self.assertEqual(len(lines), 8)
        self.assertEqual(lines[0], b'HTTP/1.1 432 Too Ugly')
        self.assertEqual(lines[1], b'Content-Length: 43')
        self.assertEqual(lines[2], b'Content-Type: text/plain')
        self.assertTrue(lines[3])
        self.assertEqual(lines[4], b'Server: waitress')
        self.assertEqual(lines[5], b'Too Ugly')
        self.assertEqual(lines[6], b'body')
        self.assertEqual(lines[7], b'(generated by waitress)')


class DummyError(object):
    code = '432'
    reason = 'Too Ugly'
    body = 'body'

class DummyTask(object):
    serviced = False
    deferred = False
    cancelled = False

    def __init__(self, toraise=None):
        self.toraise = toraise

    def service(self):
        self.serviced = True
        if self.toraise:
            raise self.toraise

    def defer(self):
        self.deferred = True
        if self.toraise:
            raise self.toraise

    def cancel(self):
        self.cancelled = True

class DummyAdj(object):
    log_socket_errors = True
    ident = 'waitress'
    host = '127.0.0.1'
    port = 80
    url_prefix = ''
    trusted_proxy = None

class DummyServer(object):
    server_name = 'localhost'
    effective_port = 80

    def __init__(self):
        self.adj = DummyAdj()

class DummyChannel(object):
    closed_when_done = False
    adj = DummyAdj()
    creation_time = 0
    addr = ['127.0.0.1']

    def __init__(self, server=None):
        if server is None:
            server = DummyServer()
        self.server = server
        self.written = b''
        self.otherdata = []

    def write_soon(self, data):
        if isinstance(data, bytes):
            self.written += data
        else:
            self.otherdata.append(data)
        return len(data)

class DummyParser(object):
    version = '1.0'
    command = 'GET'
    path = '/'
    query = ''
    url_scheme = 'http'
    expect_continue = False
    headers_finished = False

    def __init__(self):
        self.headers = {}

    def get_body_stream(self):
        return 'stream'

def filter_lines(s):
    return list(filter(None, s.split(b'\r\n')))

class DummyLogger(object):

    def __init__(self):
        self.logged = []

    def warning(self, msg):
        self.logged.append(msg)

    def exception(self, msg):
        self.logged.append(msg)
