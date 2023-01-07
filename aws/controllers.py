import json
from config.base import get_environment_variable
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

sqs_client = None

def _init_client(queue_url):
    global sqs_client
    if sqs_client is None:
        if queue_url.startswith('http://localhost'):
            try:
                import localstack_client.session as boto3
            except:
                import boto3
        else:
            import boto3

        sqs_client = boto3.client('sqs')
    return sqs_client

def submit_web_function_job(function_name, body):
    queue_url = get_environment_variable("AWS_SQS_WEB_QUEUE_URL")
    sqs = _init_client(queue_url)
    response = sqs.send_message(
        QueueUrl = queue_url,
        MessageGroupId = 'WebFunctions',
        MessageAttributes = {
            'Function': {
                'DataType': 'String',
                'StringValue': function_name
            }
        },
        MessageBody = json.dumps(body)
    )
    return response['MessageId']


