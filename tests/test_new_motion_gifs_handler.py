# coding: utf-8

import json
import pytest

from base64 import b64encode
from unittest.mock import Mock, MagicMock, sentinel
from cynnig import app

@pytest.fixture()
def sns_job_completed_lambda_event():
    return {
        'Records': [
            {
                'Sns': {
                    'Message': json.dumps(
                        {
                            'state' : 'COMPLETED',
                            'outputs': [
                                {
                                    'key': '25-20180801023512.gif',
                                    'presetId': '1351620000001-100200',
                                    'status': 'Complete'
                                }
                            ]
                        }
                    )
                }
            }
        ]
    }


class KMS:

    def decrypt(self, CiphertextBlob):
        return {
            'Plaintext': CiphertextBlob + b'-decrypted'
        }


def test_new_motion_video_handler(sns_job_completed_lambda_event, monkeypatch):
    monkeypatch.setenv('ROCKET_USERNAME', 'test/username')
    encoded_pwd = b64encode(b'test/password').decode('ascii')
    monkeypatch.setenv('ROCKET_PASSWORD', encoded_pwd)
    monkeypatch.setenv('ROCKET_SERVER', 'https://rocket.test.srv')
    monkeypatch.setenv('ROCKET_ROOM_ID', 'test/room-id')
    monkeypatch.setenv('PIPELINE_BUCKET', 'test-output-bucket')

    s3 = MagicMock()
    s3_obj = s3.get_object.return_value
    s3_obj.__getitem__.return_value = sentinel.s3_file
    def mocked_client(name):
        if name == 'kms':
            return KMS()
        elif name == 's3':
            return s3

    session = Mock()
    session.client.side_effect = mocked_client
    monkeypatch.setattr('cynnig.app.session', session)
    rocket_chat = Mock()
    chat = rocket_chat.return_value
    monkeypatch.setattr('cynnig.app.RocketChat', rocket_chat)
    app.new_motion_gifs_handler(sns_job_completed_lambda_event, None)
    rocket_chat.assert_called_with(
        'https://rocket.test.srv',
        username='test/username',
        password='test/password-decrypted'
    )
    s3_obj.__getitem__.assert_called_with('Body')
    s3.get_object.assert_called_with(
        Bucket='test-output-bucket', Key='25-20180801023512.gif')
    chat.upload.assert_called_with(
        'test/room-id', '25-20180801023512.gif', sentinel.s3_file)
