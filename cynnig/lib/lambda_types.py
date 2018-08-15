from typing import List, Dict, Callable
from mypy_extensions import TypedDict
from enum import Enum


class LambdaCognitoIdentity:
    cognito_identity_id: str
    cognito_identity_pool_id: str


class LambdaClientContextMobileClient:
    installation_id: str
    app_title: str
    app_version_name: str
    app_version_code: str
    app_package_name: str


class LambdaClientContext:
    client: LambdaClientContextMobileClient
    custom: Dict
    env: Dict


class LambdaContext:
    function_name: str
    function_version: str
    invoked_function_arn: str
    memory_limit_in_mb: int
    aws_request_id: str
    log_group_name: str
    log_stream_name: str
    identity: LambdaCognitoIdentity
    client_context: LambdaClientContext
    get_remaining_time_in_millis: Callable[[], int]


class S3UpdateBucketInfo(TypedDict):
    arn: str
    name: str


class S3UpdateObjectInfo(TypedDict):
    key: str


class S3UpdateInfo(TypedDict):
    object: S3UpdateObjectInfo
    bucket: S3UpdateBucketInfo


class S3UpdateRecord(TypedDict):
    s3: S3UpdateInfo


class S3UpdateEvent(TypedDict):
    """S3 Object Update Event

    Sent by AWS for all sorts of update operations on S3 objects.

    Example (some fields omitted for clarity):
    {
      "Records": [
        {
          "s3": {
            "object": {
              "key": "01-20180730195708.mkv"
            },
            "bucket": {
              "arn": "arn:aws:s3:::motion-events-velimir",
              "name": "motion-events-velimir"
            }
          }
        }
      ]
    }
    """
    Records: List[S3UpdateRecord]


class JobInput(TypedDict):
    Key: str


class JobOutput(TypedDict):
    PresetId: str
    Key: str
    Status: str # Submitted|Progressing|Completed|Warning|Error


class JobSNSOutput(TypedDict):
    presetId: str
    key: str
    status: str # Progressing|Completed|Warning|Error


class PipelineNotifications(TypedDict):
    Progressing: str
    Completed: str
    Warning: str
    Error: str


class PipelineOutputConfig(TypedDict):
    Bucket: str


class PipelineInfo(TypedDict):
    Id: str
    Arn: str
    Name: str
    Status: str
    InputBucket: str
    OutputBucket: str
    Role: str
    Notifications: PipelineNotifications
    ContentConfig: PipelineOutputConfig
    ThumbnailConfig: PipelineOutputConfig


class AWSElasticTranscoderResponse(TypedDict):
    ResponseMetadata: Dict


class AWSPipelineResponse(AWSElasticTranscoderResponse):
    Pipeline: PipelineInfo


ReadPipelineResponse = AWSPipelineResponse
CreatePipelineResponse = AWSPipelineResponse
UpdatePipelineResponse = AWSPipelineResponse


class ElasticTranscoderClient:

    def create_job(self, *, PipelineId: str, Input: JobInput, Output: JobOutput) -> Dict:
        pass

    def read_pipeline(self, *, Id: str) -> ReadPipelineResponse:
        pass

    def create_pipeline(self, *, Name: str, InputBucket: str,
                        OutputBucket: str, Role: str,
                        Notifications: PipelineNotifications) -> CreatePipelineResponse:
        pass

    def update_pipeline(self, *, Id: str, Name: str, InputBucket: str,
                        Role: str, Notifications: PipelineNotifications,
                        ContentConfig: PipelineOutputConfig,
                        ThumbnailConfig: PipelineOutputConfig) -> UpdatePipelineResponse:
        pass

    def delete_pipeline(self, *, Id: str) -> AWSElasticTranscoderResponse:
        pass


class SNSRecord(TypedDict):
    Message: str


class SNSEventRecord(TypedDict):
    Sns: SNSRecord


class SNSEvent(TypedDict):
    """SNS event that is received by lambda function

    Example:
    {
        "Records": [
            {
                "EventVersion": "1.0",
                "EventSubscriptionArn": "arn:aws:sns:EXAMPLE",
                "EventSource": "aws:sns",
                "Sns": {
                    "SignatureVersion": "1",
                    "Timestamp": "1970-01-01T00:00:00.000Z",
                    "Signature": "EXAMPLE",
                    "SigningCertUrl": "EXAMPLE",
                    "MessageId": "95df01b4-ee98-5cb9-9903-4c221d41eb5e",
                    "Message": "{\"state\": \"COMPLETED\"}",
                    "MessageAttributes": {
                        "Test": {
                            "Type": "String",
                            "Value": "TestString"
                        },
                        "TestBinary": {
                            "Type": "Binary",
                            "Value": "TestBinary"
                        }
                    },
                    "Type": "Notification",
                    "UnsubscribeUrl": "EXAMPLE",
                    "TopicArn": "arn:aws:sns:us-east-1:111122223333:ExampleTopic",
                    "Subject": "example subject"
                }
            }
        ]
    }
    """
    Records: List[SNSEventRecord]


class JobState(Enum):
    PROGRESSING = 'PROGRESSING'
    COMPLETED = 'COMPLETED'
    WARNING = 'WARNING'
    ERROR = 'ERROR'


class TranscoderJobStatus(TypedDict):
    # redefine as union of literals once they are available
    # see https://github.com/python/typing/issues/478
    state: str                  # PROGRESSING|COMPLETED|WARNING|ERROR
    outputs: List[JobSNSOutput]


class VideoPipelineProperties(TypedDict):
    DisplayName: str            # The name of the pipeline
    InputBucket: str            # input bucket arn
    OutputBucket: str           # output bucket arn
    Role: str                   # role arn for new pipeline
    Notifications: str          # SNS arn to send all notifications to


class CustomResourceRequest(TypedDict):
    RequestType: str            # Create|Delete|Update
    RequestId: str              # unique id for this create request
    ResponseURL: str            # pre signed url for create response
    ResourceType: str           # Custom::MyCustomResourceType,
    LogicalResourceId: str      # name of resource in template
    StackId: str # arn:aws:cloudformation:us-east-2:namespace:stack/stack-name/guid
    ResourceProperties: VideoPipelineProperties


class CustomResourceUpdateRequest(CustomResourceRequest):
    PhysicalResourceId: str
    OldResourceProperties: VideoPipelineProperties


class CustomResourceDeleteRequest(CustomResourceRequest):
    PhysicalResourceId: str


class CustomResourceResponse(TypedDict):
    Status: str                 # SUCCESS|FAILED
    RequestId: str # unique id for this create request (copied from request)
    LogicalResourceId: str # name of resource in template (copied from request)
    StackId: str # arn:aws:cloudformation:us-east-2:namespace:stack/stack-name/guid (copied from request)
    PhysicalResourceId: str # required vendor-defined physical id that is unique for that vendor


class VideoPipelineData(TypedDict):
    Id: str
    Arn: str


class CustomResourceSuccessResponse(CustomResourceResponse):
    Data: VideoPipelineData


class CustomResourceFailedResponse(CustomResourceResponse):
    pass
