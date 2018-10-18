from unittest import mock

import pytest
from io import StringIO
from pyramid.httpexceptions import HTTPOk
from kinto.core.decorators import cache_forever


@cache_forever
def demo1(request):
    request.mock()
    return "demo1"


@cache_forever
def demo2(request, name):
    return "demo2: {}".format(name)


@cache_forever
def demo3(request):
    return request.response


def test_cache_forever_decorator_call_the_decorated_function_once():
    request = mock.MagicMock()
    demo1(request)
    demo1(request)
    demo1(request)
    assert request.mock.call_count == 1


def test_cache_forever_doesnt_care_about_arguments():
    request1 = mock.MagicMock()
    request1.response = StringIO()

    request2 = mock.MagicMock()
    request2.response = StringIO()

    response1 = demo2(request1, "Henri").getvalue()
    response2 = demo2(request2, "Paul").getvalue()
    assert response1 == response2 == "demo2: Henri"


def test_each_function_is_cached_separately_for_the_life_of_the_process():
    request1 = mock.MagicMock()
    request1.response = StringIO()
    response1 = demo1(request1).getvalue()

    request2 = mock.MagicMock()
    request2.response = StringIO()
    response2 = demo2(request2).getvalue()

    assert response1 != response2
    assert response1 == "demo1"
    assert response2 == "demo2: Henri"


def test_should_not_cache_responses():
    request = mock.MagicMock()
    request.response = HTTPOk()

    with pytest.raises(ValueError):
        demo3(request)
