# coding: utf-8

import json
import pytest

from cynnig import app
from unittest.mock import Mock


REQUEST_ID = '41F948A0-D65C-4C1C-9BAC-9EA2E57557DA'
STACK_ID = 'arn:aws:cloudformation:us-east-2:namespace:stack/stack-name/guid'
DISPLAY_NAME = 'test-stack motion pipeline'
DISPLAY_NAME_UPDATED = DISPLAY_NAME + ' updated'
ROLE_ARN = 'arn:aws:iam::034029384242:role/Elastic_Transcoder_Default_Role'
ROLE_ARN_UPDATED = ROLE_ARN + '-updated'
INPUT_BUCKET = 'test-pipeline-input-bucket'
INPUT_BUCKET_UPDATED = INPUT_BUCKET + '-updated'
OUTPUT_BUCKET = 'test-pipeline-output-bucket'
OUTPUT_BUCKET_UPDATED = OUTPUT_BUCKET + '-updated'
SNS_ARN = 'arn:aws:sns:eu-west-1:034029384242:test-sns-topic'
SNS_ARN_UPDATED = SNS_ARN + '-updated'
LOGICAL_RESOURCE_ID = 'VideoPipeline'

PIPELINE_ARN = 'arn:aws:elastictranscoder:eu-west-1:034029384242:pipeline/1532349581389-ms8sbr'
PIPELINE_ID = '1532349581389-ms8sbr'


@pytest.fixture()
def create_event():
    return {
        'RequestType': 'Create',
        'RequestId': REQUEST_ID,
        'ResponseURL': 'https://httpbin.org/put',
        'ResourceType': 'Custom::ElasticTranscoderPipeline',
        'LogicalResourceId': LOGICAL_RESOURCE_ID,
        'StackId': STACK_ID,
        'ResourceProperties': {
            'DisplayName': DISPLAY_NAME,
            'Role': ROLE_ARN,
            'InputBucket': INPUT_BUCKET,
            'OutputBucket': OUTPUT_BUCKET,
            'Notifications': SNS_ARN
        }
    }


@pytest.fixture()
def update_event():
    return {
        'RequestType': 'Update',
        'RequestId': REQUEST_ID,
        'ResponseURL': 'https://httpbin.org/put',
        'ResourceType': 'Custom::ElasticTranscoderPipeline',
        'LogicalResourceId': LOGICAL_RESOURCE_ID,
        'StackId': STACK_ID,
        'PhysicalResourceId': PIPELINE_ID,
        'ResourceProperties': {
            'DisplayName': DISPLAY_NAME_UPDATED,
            'Role': ROLE_ARN_UPDATED,
            'InputBucket': INPUT_BUCKET_UPDATED,
            'OutputBucket': OUTPUT_BUCKET_UPDATED,
            'Notifications': SNS_ARN_UPDATED
        },
        'OldResourceProperties' : {
            'DisplayName': DISPLAY_NAME,
            'Role': ROLE_ARN,
            'InputBucket': INPUT_BUCKET,
            'OutputBucket': OUTPUT_BUCKET,
            'Notifications': SNS_ARN
        }
    }


@pytest.fixture()
def non_update_event():
    properties = {
        'DisplayName': DISPLAY_NAME,
        'Role': ROLE_ARN,
        'InputBucket': INPUT_BUCKET,
        'OutputBucket': OUTPUT_BUCKET,
        'Notifications': SNS_ARN
    }
    return {
        'RequestType': 'Update',
        'RequestId': REQUEST_ID,
        'ResponseURL': 'https://httpbin.org/put',
        'ResourceType': 'Custom::ElasticTranscoderPipeline',
        'LogicalResourceId': LOGICAL_RESOURCE_ID,
        'StackId': STACK_ID,
        'PhysicalResourceId': PIPELINE_ID,
        'ResourceProperties': properties,
        'OldResourceProperties' : properties
    }


@pytest.fixture()
def delete_event():
    return {
        'RequestType': 'Delete',
        'RequestId': REQUEST_ID,
        'ResponseURL': 'https://httpbin.org/put',
        'ResourceType': 'Custom::ElasticTranscoderPipeline',
        'LogicalResourceId': LOGICAL_RESOURCE_ID,
        'StackId': STACK_ID,
        'PhysicalResourceId': PIPELINE_ID,
        'ResourceProperties': {
            'DisplayName': DISPLAY_NAME,
            'Role': ROLE_ARN,
            'InputBucket': INPUT_BUCKET,
            'OutputBucket': OUTPUT_BUCKET,
            'Notifications': SNS_ARN
        }
    }


@pytest.fixture()
def lambda_context():
    context = Mock()
    context.log_stream_name = 'log_stream_name'
    context.aws_request_id = 'aws_request_id'
    context.get_remaining_time_in_millis.return_value = 5 * 1000.0
    return context


@pytest.fixture()
def requests(monkeypatch):
    requests = Mock()
    response = requests.put.return_value
    response.reason = "OK"
    monkeypatch.setattr('crhelper.requests', requests)
    return requests


@pytest.fixture()
def session(monkeypatch):
    session_mock = Mock()
    monkeypatch.setattr('cynnig.app.session', session_mock)
    return session_mock


def test_create(create_event, lambda_context, session, requests):
    create_pipeline_test(
        app.elastictranscoder_resource_handler,
        create_event, lambda_context, session, PIPELINE_ARN, PIPELINE_ID,
        requests)
    client = session.client.return_value
    client.create_pipeline.assert_called_with(
        Name=DISPLAY_NAME,
        InputBucket=INPUT_BUCKET,
        OutputBucket=OUTPUT_BUCKET,
        Role=ROLE_ARN,
        Notifications={
            'Progressing': SNS_ARN,
            'Completed': SNS_ARN,
            'Warning': SNS_ARN,
            'Error': SNS_ARN
        }
    )


class ResourceNotFoundException(Exception):
    pass


def test_update_not_found(update_event, lambda_context, session, requests):
    client = session.client.return_value
    client.exceptions.ResourceNotFoundException = ResourceNotFoundException
    client.read_pipeline.side_effect = ResourceNotFoundException()
    create_pipeline_test(
        app.elastictranscoder_resource_handler,
        update_event, lambda_context, session, PIPELINE_ARN, PIPELINE_ID,
        requests)
    client.read_pipeline.assert_called_with(Id=PIPELINE_ID)
    client.create_pipeline.assert_called_with(
        Name=DISPLAY_NAME_UPDATED,
        InputBucket=INPUT_BUCKET_UPDATED,
        OutputBucket=OUTPUT_BUCKET_UPDATED,
        Role=ROLE_ARN_UPDATED,
        Notifications={
            'Progressing': SNS_ARN_UPDATED,
            'Completed': SNS_ARN_UPDATED,
            'Warning': SNS_ARN_UPDATED,
            'Error': SNS_ARN_UPDATED
        }
    )


def test_non_update(non_update_event, lambda_context, session, requests):
    data = {
        'Arn': PIPELINE_ARN,
        'Id': PIPELINE_ID
    }
    client = session.client.return_value
    client.read_pipeline.return_value = {'Pipeline': data}
    app.elastictranscoder_resource_handler(non_update_event, lambda_context)
    assert_cfn_response(requests, data)


def test_update(update_event, lambda_context, session, requests):
    data = {
        'Arn': PIPELINE_ARN,
        'Id': PIPELINE_ID
    }
    client = session.client.return_value
    client.read_pipeline.return_value = {'Pipeline': data}
    app.elastictranscoder_resource_handler(update_event, lambda_context)
    sns = SNS_ARN_UPDATED
    client.update_pipeline.assert_called_with(
        Id=PIPELINE_ID,
        Name=DISPLAY_NAME_UPDATED,
        InputBucket=INPUT_BUCKET_UPDATED,
        Role=ROLE_ARN_UPDATED,
        Notifications={
            'Progressing': sns,
            'Completed': sns,
            'Warning': sns,
            'Error': sns
        },
        ContentConfig={
            'Bucket': OUTPUT_BUCKET_UPDATED
        },
        ThumbnailConfig={
            'Bucket': OUTPUT_BUCKET_UPDATED
        }
    )
    assert_cfn_response(requests, data)


def test_delete(delete_event, lambda_context, session, requests):
    app.elastictranscoder_resource_handler(delete_event, lambda_context)
    client = session.client.return_value
    client.delete_pipeline.assert_called_with(Id=PIPELINE_ID)
    assert_cfn_response(requests)


def test_delete_not_found(delete_event, lambda_context, session, requests):
    client = session.client.return_value
    client.exceptions.ResourceNotFoundException = ResourceNotFoundException
    client.delete_pipeline.side_effect = ResourceNotFoundException()
    app.elastictranscoder_resource_handler(delete_event, lambda_context)
    client.delete_pipeline.assert_called_with(Id=PIPELINE_ID)
    assert_cfn_response(requests)


def create_pipeline_test(lambda_fn, event, context, session,
                         pipeline_arn, pipeline_id, requests):
    data = {
        'Arn': pipeline_arn,
        'Id': pipeline_id
    }
    client = session.client.return_value
    client.create_pipeline.return_value = {'Pipeline': data}
    lambda_fn(event, context)
    assert_cfn_response(requests, data)


def assert_cfn_response(requests, data=None):
    response_obj = {
        'Status': 'SUCCESS',
        'Reason': 'See details in CloudWatch Log Stream: log_stream_name',
        'PhysicalResourceId': PIPELINE_ID,
        'StackId': STACK_ID,
        'RequestId': REQUEST_ID,
        'LogicalResourceId': LOGICAL_RESOURCE_ID
    }

    if data:
        response_obj['Data'] = data

    response_body = json.dumps(response_obj)
    requests.put.assert_called_with(
        'https://httpbin.org/put',
        data=response_body,
        headers={
            'content-type': '',
            'content-length': str(len(response_body))
        }
    )
