import boto3
import json
from config.base import get_environment_variable

web_function_sqs_queue_url = get_environment_variable("WEVOTE_SQS_WEB_FUNCTIONS_QUEUE_URL")

sqs_client = None

def _init_client():
    global sqs_client
    if sqs_client is None:
        AWS_REGION_NAME = get_environment_variable("AWS_REGION_NAME")
        sqs_client = boto3.client('sqs', region_name=AWS_REGION_NAME)
    return sqs_client

def submit_web_function_job(function_name, body):
    sqs = _init_client()
    response = sqs.send_message(
        QueueUrl=web_function_sqs_queue_url,
        MessageGroupId='WebFunctions',
        MessageAttributes={
            'Function': {
                'DataType': 'String',
                'StringValue': function_name
            }
        },
        MessageBody=json.dumps(body)
    )
    return response['MessageId']


