import json
import os

from django.core.management.base import BaseCommand

import wevote_functions.admin
from config.base import get_environment_variable

logger = wevote_functions.admin.get_logger(__name__)

# For testing the job queue system locally, you can run an SQS 
# server locally using localstack within docker.
# Use the following commands to install:
#
#   pip install localstack localstack-client awscli-local
#
#  If 'docker' cli is not available at the command line...
#    Get the docker CLI at https://docs.docker.com/desktop/install/mac-install/
#    Find the downloaded file, and substitute its path in the following set of commands
#      (venv2) WeVoteServer % sudo hdiutil attach '/Users/stevepodell/Downloads/Docker (1).dmg'
#      (venv2) WeVoteServer % sudo /Volumes/Docker/Docker.app/Contents/MacOS/install
#      (venv2) WeVoteServer % sudo hdiutil detach /Volumes/Docker
#    In a MacOS modal dialog that appears, allow docker to make some symbolic links
#    Once the Docker Desktop starts, and shows as running, typing 'docker' at the command line, will show a response
#
# if aws (awslocal) is not available at the command line...
#   Follow instructions at
#   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html#getting-started-install-instructions
#
# Start the aws local sqs service
#    localstack start -d     (wait for sqs service to launch)
#
# Create a sqs queue, and copy the QueueUrl it reports to environment-variables.json
#   awslocal sqs create-queue --queue-name job-queue.fifo --attributes FifoQueue=true,ContentBasedDeduplication=true
#
# Make sure the QueueUrl displayed matches AWS_SQS_WEB_QUEUE_URL in the config file environment-variables.json
#
# Then start the queue processing code (in a separate python server instance) by opening a terminal window and running
#      python manage.py runsqsworker
#
#   you will see logging from the sqs worker in that terminal


# max time (in sec) that a job may take to complete
#  this prevents a different worker from picking up a job that
#  is currently being handled by another worker
MAX_JOB_PROCESSING_TIME = 60
MAX_JOB_RETRY_ATTEMPTS = 5

def process_request(function, body, message):
    logger.error('(Ok) SQS job execute process_request ' + function + '  ' + str(body))

    if function == 'caching_facebook_images_for_retrieve_process':
        from import_export_facebook.controllers import caching_facebook_images_for_retrieve_process
        repair_facebook_related_voter_caching_now = body['repair_facebook_related_voter_caching_now']
        facebook_auth_response_id = body['facebook_auth_response_id']
        voter_we_vote_id_attached_to_facebook = body['voter_we_vote_id_attached_to_facebook']
        voter_we_vote_id_attached_to_facebook_email = body['voter_we_vote_id_attached_to_facebook_email']
        voter_we_vote_id = body['voter_we_vote_id']

        caching_facebook_images_for_retrieve_process(repair_facebook_related_voter_caching_now,
                                                     facebook_auth_response_id,
                                                     voter_we_vote_id_attached_to_facebook,
                                                     voter_we_vote_id_attached_to_facebook_email,
                                                     voter_we_vote_id)
    elif function == 'voter_cache_facebook_images_process':
        from voter.controllers import voter_cache_facebook_images_process
        voter_id = body['voter_id']
        facebook_auth_response_id = body['facebook_auth_response_id']

        voter_cache_facebook_images_process(voter_id, facebook_auth_response_id)
    else:
        logger.error(f"SQS Job references unknown function [{function}], deleting.")

    return True


def worker_run(queue_url):
    if queue_url.startswith('http://localhost'):
        try:
            import localstack_client.session as boto3
        except:
            import boto3
    else:
        import boto3

    sqs = boto3.client('sqs')
    # print("sqs.receive_message startup--------------------")

    while True:
        # Receive message from SQS queue
        response = sqs.receive_message(
            QueueUrl=queue_url,
            AttributeNames=['All'],
            MaxNumberOfMessages=1,
            MessageAttributeNames=['All'],
            VisibilityTimeout=MAX_JOB_PROCESSING_TIME,
            WaitTimeSeconds=20
        )

        if 'Messages' in response.keys() and len(response['Messages']) > 0:
            message = response['Messages'][0]
            logger.error("(Ok) SQS -- Got message: ", message)
            receipt_handle = message['ReceiptHandle']
            processed = False


            if 'Function' in message['MessageAttributes'].keys():
                function = message['MessageAttributes']['Function']['StringValue']
                print(f"Calling function [{function}]")
                body = json.loads(message['Body'])
                try:
                    processed = process_request(function, body, message)
                except Exception as e:
                    print("Failed to call function {function}:", e)

            else:
                logger.error("SQS No function provided in SQS message, deleting invalid request.")
                processed = True

            # expire messages after max number of retries
            if not processed:
                job_retry_count = int(message['Attributes']['ApproximateReceiveCount'])
                if job_retry_count > MAX_JOB_RETRY_ATTEMPTS:
                    print("Message crossed max retry attempts, deleting.")
                    processed = True

            # Delete processed message from queue
            if processed:
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
                print('Deleted message: %s' % message)



class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        print("Starting job worker, waiting for jobs from SQS..")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        sqs_url = get_environment_variable("AWS_SQS_WEB_QUEUE_URL")
        worker_run(sqs_url)




    
