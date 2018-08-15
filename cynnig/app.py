import boto3
import json
import logging
import os
import re
import sys

CWD = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(CWD, 'lib'))

from base64 import b64decode

import crhelper
from rocketchat import RocketChat

from typing import Dict, Tuple
from lambda_types import LambdaContext, S3UpdateEvent, \
    ElasticTranscoderClient, TranscoderJobStatus, VideoPipelineData, \
    PipelineInfo, CustomResourceUpdateRequest, CustomResourceRequest, \
    SNSEvent, JobState


session = boto3.Session()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def new_motion_video_handler(event: S3UpdateEvent,
                             context: LambdaContext) -> None:
    """AWS Lambda handler which receives notifications with new video
    recording and send a request to elastic transcoder to make a GIF,
    which can be viewed in a chat app

    """
    logger.debug('EVENT: %s', event)
    stack_name: str = os.environ['STACK_NAME']
    client: ElasticTranscoderClient = session.client('elastictranscoder')
    pipeline_id: str = find_pipeline_id(client, stack_name)

    for record in event['Records']:
        object_key: str = record['s3']['object']['key']
        result = schedule_gif_transcoding(client, pipeline_id, object_key)
        logger.debug('job scheduled: %s', result)


def new_motion_gifs_handler(event: SNSEvent, context: LambdaContext) -> None:
    """AWS Lambda handler which receives notifications about new GIFs
    and sends them to a configured chat room

    """
    logger.debug('EVENT: %s', event)

    username = os.environ['ROCKET_USERNAME']
    password = os.environ['ROCKET_PASSWORD']
    server_url = os.environ['ROCKET_SERVER']
    room_id = os.environ['ROCKET_ROOM_ID']

    kms = session.client('kms')
    password = kms.decrypt(CiphertextBlob=b64decode(password))['Plaintext']
    password = password.decode('ascii')
    chat = RocketChat(server_url, username=username, password=password)

    s3 = session.client('s3')
    bucket = os.environ['PIPELINE_BUCKET']

    for record in event['Records']:
        job: TranscoderJobStatus = json.loads(record['Sns']['Message'])
        state = JobState(job['state'])
        if state is JobState.COMPLETED:
            for output in job['outputs']:
                key = output['key']
                obj = s3.get_object(Bucket=bucket, Key=key)
                chat.upload(room_id, key, obj['Body'])


def elastictranscoder_resource_handler(
        event: CustomResourceRequest, context: LambdaContext) -> None:
    """AWS Lambda handler for ElasticTranscoder service to
    create/update and delete Video Pipelines from using CFN

    """
    try:
        logger = crhelper.log_config(event)
        init_failed = False
    except Exception as e:
        logger.error(e, exc_info=True)
        init_failed = True

    crhelper.cfn_handler(event, context, create_pipeline, update_pipeline,
                         delete_pipeline, logger, init_failed)


def create_pipeline(event: CustomResourceRequest,
                    context: LambdaContext) -> Tuple[str, VideoPipelineData]:
    properties = event['ResourceProperties']
    sns = properties['Notifications']
    client: ElasticTranscoderClient = session.client('elastictranscoder')
    result = client.create_pipeline(
        Name=properties['DisplayName'],
        InputBucket=properties['InputBucket'],
        OutputBucket=properties['OutputBucket'],
        Role=properties['Role'],
        Notifications={
            'Progressing': sns,
            'Completed': sns,
            'Warning': sns,
            'Error': sns
        }
    )
    pipeline: PipelineInfo = result['Pipeline']
    pipeline_arn = pipeline['Arn']
    pipeline_id = pipeline['Id']
    data = {
        'Arn': pipeline_arn,
        'Id': pipeline_id
    }
    return pipeline_id, data


def update_pipeline(event: CustomResourceUpdateRequest,
                    context: LambdaContext) -> Tuple[str, VideoPipelineData]:
    client: ElasticTranscoderClient = session.client('elastictranscoder')
    pipeline_id = event['PhysicalResourceId']
    try:
        read_response = client.read_pipeline(Id=pipeline_id)
    except client.exceptions.ResourceNotFoundException as e:
        logger.debug('resource %s not found', pipeline_id)
        return create_pipeline(event, context)

    pipeline: PipelineInfo = read_response['Pipeline']
    properties = event['ResourceProperties']
    pipeline_data = {'Arn': pipeline['Arn'], 'Id': pipeline['Id']}
    if event['OldResourceProperties'] == properties:
        return pipeline_id, pipeline_data

    sns = properties['Notifications']
    client.update_pipeline(
        Id=pipeline['Id'],
        Name=properties['DisplayName'],
        InputBucket=properties['InputBucket'],
        Role=properties['Role'],
        Notifications={
            'Progressing': sns,
            'Completed': sns,
            'Warning': sns,
            'Error': sns
        },
        ContentConfig={
            'Bucket': properties['OutputBucket']
        },
        ThumbnailConfig={
            'Bucket': properties['OutputBucket']
        }
    )
    return pipeline_id, pipeline_data


def delete_pipeline(event: CustomResourceRequest,
                    context: LambdaContext) -> None:
    client: ElasticTranscoderClient = session.client('elastictranscoder')
    pipeline_id = event['PhysicalResourceId']

    try:
        client.delete_pipeline(Id=pipeline_id)
    except client.exceptions.ResourceNotFoundException as e:
        logger.debug('resource %s not found', pipeline_id)


def schedule_gif_transcoding(client: ElasticTranscoderClient, pipeline_id: str,
                             object_key: str) -> Dict:
    name, _ = os.path.splitext(object_key)
    output_key = '{}.gif'.format(name)
    return client.create_job(
        PipelineId=pipeline_id,
        Input={
            'Key': object_key
        },
        Output={
            # System preset to convert to GIF
            'PresetId': '1351620000001-100200',
            'Key': output_key
        }
    )


def find_pipeline_id(client: ElasticTranscoderClient, stack_name: str) -> str:
    response = client.list_pipelines()
    return next(pl['Id'] for pl in response['Pipelines']
                if re.search(stack_name, pl['Name']))
