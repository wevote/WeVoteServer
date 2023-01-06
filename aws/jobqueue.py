import boto3
import json

web_function_sqs_queue_url = os.environ.get("WEVOTE_SQS_WEB_FUNCTIONS_QUEUE_URL")

sqs_client = None

def _init_client():
    global sqs_client
    if sqs_client is None:
        sqs_client = boto3.client('sqs')
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


