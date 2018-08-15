# coding: utf-8

import json
import pytest
import re

from cynnig.lib.rocketchat import RocketChat

import httpretty
from httpretty import HTTPretty

httpretty.HTTPretty.allow_net_connect = False

ROCKET_USERNAME = 'test-username'
ROCKET_PASSWORD = 'test-password'
ROCKET_SERVER = 'http://rocket-server.dev.null'
USER_ID = 'test-user-id'
AUTH_TOKEN = 'test-auth-token'


@pytest.fixture()
def chat():
    with httpretty.enabled():
        yield RocketChat(ROCKET_SERVER, ROCKET_USERNAME, ROCKET_PASSWORD)


def test_login(chat):
    login_data = json.dumps({
        'data': {
            'userId': USER_ID,
            'authToken': AUTH_TOKEN
        }
    })
    httpretty.register_uri(httpretty.POST, re.compile(r'.*/api/v1/login', re.M),
                           body=login_data)
    httpretty.register_uri(httpretty.GET, re.compile(r'.*/api/v1/info', re.M),
                           body='{"success": true}')
    chat.request('get', '/api/v1/info')
    assert len(HTTPretty.latest_requests) == 2
    login_req = HTTPretty.latest_requests[0]
    assert login_req.parsed_body == {
        'username': ROCKET_USERNAME,
        'password': ROCKET_PASSWORD
    }
    info_req = HTTPretty.latest_requests[1]
    assert_request_auth(info_req)

    chat.request('get', '/api/v1/info')
    assert len(HTTPretty.latest_requests) == 3
    info_req = HTTPretty.latest_requests[2]
    assert_request_auth(info_req)


def assert_request_auth(request):
    assert 'X-User-Id' in request.headers
    assert request.headers['X-User-Id'] == USER_ID
    assert 'X-Auth-Token' in request.headers
    assert request.headers['X-Auth-Token'] == AUTH_TOKEN
