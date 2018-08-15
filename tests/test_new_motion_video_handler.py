# coding: utf-8

import json
import pytest

from unittest.mock import Mock
from cynnig import app


@pytest.fixture()
def s3_new_object_lambda_event():
    return {
        'Records': [
            {
                's3': {
                    'object': {
                        'key': '01-20180730195708.mkv'
                    },
                    'bucket': {
                        'arn': 'arn:aws:s3:::motion-events-velimir',
                        'name': 'motion-events-velimir'
                    }
                }
            }
        ]
    }

def test_new_motion_video_handler(s3_new_object_lambda_event, monkeypatch):
    monkeypatch.setenv('STACK_NAME', 'cynnig')
    session = Mock()
    monkeypatch.setattr('cynnig.app.session', session)
    client = session.client.return_value
    client.list_pipelines.return_value = {
        'Pipelines': [
            {
                'Name': 'foo bar baz',
                'Id': '0534090839028-barbaz'
            },
            {
                'Name': 'cynnig motion pipeline',
                'Id': '1534090839028-jh9ib4'
            }
        ]
    }
    client.create_job.return_value = {
        'Job': {
            'Arn': 'arn:aws:elastictranscoder:eu-west-1:0340292934242:job/15340920394528-sk29dbs',
            'Id': '1534090839028-jh9ib4',
            'Input': {'Key': '01-20180730195708.mkv'},
            'Inputs': [{'Key': '01-20180730195708.mkv'}],
            'Output': {'Id': '1',
                       'Key': '01-20180730195708.gif',
                       'PresetId': '1351620000001-100200',
                       'Status': 'Submitted',
                       'Watermarks': []},
            'Outputs': [{'Id': '1',
                         'Key': '01-20180730195708.gif',
                         'PresetId': '1351620000001-100200',
                         'Status': 'Submitted',
                         'Watermarks': []}],
            'PipelineId': '15340920394528-sk29dbs',
            'Playlists': [],
            'Status': 'Submitted',
            'Timing': {'SubmitTimeMillis': 1534090839044}},
        'ResponseMetadata': {
            'HTTPHeaders': {
                'content-length': '1613',
                'content-type': 'application/json',
                'date': 'Sun, 12 Aug 2018 16:20:39 GMT',
                'x-amzn-requestid': 'a6a13a74-9e4b-11e8-badf-7d077783343e'},
            'HTTPStatusCode': 201,
            'RequestId': 'a6a13a74-9e4b-11e8-badf-7d077783343e',
            'RetryAttempts': 0}
    }
    app.new_motion_video_handler(s3_new_object_lambda_event, "")
    client.create_job.assert_called_with(
        PipelineId='1534090839028-jh9ib4',
        Input={
            'Key': '01-20180730195708.mkv'
        },
        Output={
            # System preset to convert to GIF
            'PresetId': '1351620000001-100200',
            'Key': '01-20180730195708.gif'
        }
    )
