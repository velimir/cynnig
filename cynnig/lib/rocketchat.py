import requests
import mimetypes

from requests.auth import AuthBase
from typing import BinaryIO, Optional, Dict
from mypy_extensions import TypedDict


class LoginData(TypedDict):
    authToken: str
    userId: str


class RocketResponse(TypedDict):
    status: str                 # success


class RocketLoginResponse(RocketResponse):
    data: LoginData



class RocketChat:

    def __init__(self, server_url: str,
                 username: Optional[str] = None, password: Optional[str] = None,
                 user_id: Optional[str] = None, auth_token: Optional[str] = None) -> None:
        assert (username and password) or (user_id and auth_token), \
            'either username/password or user_id/auth_token have to be provided'

        self.username = username
        self.password = password
        self.user_id = user_id
        self.auth_token = auth_token
        self.server_url = server_url

        self._session = requests.Session()
        if self.username and self.password:
            auth = LoginAuth(self, self.username, self.password)
        elif self.user_id and self.auth_token:
            auth = TokenAuth(self.user_id, self.auth_token)

        self._session.auth = auth

    def request(self, method: str, path: str, **kwargs: Dict) -> RocketResponse:
        url = self.server_url + path
        old_auth = None
        if 'auth' in kwargs:
            old_auth = self._session.auth
            self._session.auth = kwargs['auth']

        resp = self._session.request(method, url, **kwargs)
        if old_auth:
            self._session.auth = old_auth

        resp.raise_for_status()
        return resp.json()

    def login(self, username: str, password: str) -> RocketLoginResponse:
        path = '/api/v1/login'
        creds = {
            'username': username,
            'password': password
        }
        return self.request('post', path, json=creds, auth=None)

    def upload(self, room_id: str, name: str, file: BinaryIO) -> RocketResponse:
        type, _ = mimetypes.guess_type(name)
        files = {'file': (name, file, type)}
        path =  '/api/v1/rooms.upload/{}'.format(room_id)
        return self.request('post', path, files=files)


class TokenAuth(AuthBase):

    def __init__(self, user_id, auth_token):
        self._user_id = user_id
        self._auth_token = auth_token

    def __call__(self, request):
        request.headers.update({
            'X-Auth-Token': self._auth_token,
            'X-User-Id': self._user_id
        })
        return request


class LoginAuth(AuthBase):

    def __init__(self, chat: RocketChat, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.chat = chat
        self.__token_auth = None

    @property
    def token_auth(self) -> TokenAuth:
        if not self.__token_auth:
            resp = self.chat.login(self.username, self.password)
            data = resp['data']
            user_id = data['userId']
            auth_token = data['authToken']
            self.__token_auth = TokenAuth(user_id, auth_token)
        return self.__token_auth

    def __call__(self, request):
        return self.token_auth(request)
