import json
import logging
import os

logger = logging.getLogger()
log_level = os.environ.get("LAMBDA_LOG_LEVEL", "INFO")
logger.setLevel(logging.getLevelName(log_level))

import boto3
from botocore.exceptions import ClientError

# Load config from Secrets Manager before Django initializes — mirrors what
# docker/prod/entrypoint does for the ECS task.  Runs once per cold start.
_secret_arn = os.environ.get('CONFIG_SECRET_ARN')
_region = os.environ.get('AWS_DEFAULT_REGION') or os.environ.get('AWS_REGION')
if _secret_arn and _region:
    try:
        _client = boto3.session.Session().client('secretsmanager', region_name=_region)
        _secret = json.loads(_client.get_secret_value(SecretId=_secret_arn)['SecretString'])
        logger.info("Loaded config from secret with %d entries", len(_secret))
        for _key, _val in _secret.items():
            if _key not in os.environ:
                os.environ[_key] = _val
    except ClientError as e:
        raise RuntimeError(f"Failed to load config secret {_secret_arn}") from e

# Django must be initialized at module level so it runs once per cold start
# and is reused across warm Lambda invocations.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()


def handler(event, context):
    """
    Lambda handler for EventBridge-scheduled batch processing jobs.

    Replaces the 4 cron jobs that previously hit WeVoteServer API endpoints
    via wget every minute. EventBridge rules invoke this function directly,
    passing { "function": "<job_name>" } in the event input.

    The controller functions manage their own concurrency via date_checked_out
    on BatchProcess records, so concurrent Lambda invocations are safe — they
    simply return immediately when no work is available.
    """
    function_name = event.get('function')
    logger.info("Batch processor invoked: function=%s", function_name)

    if function_name == 'process_next_activity_notices':
        from import_export_batches.controllers_batch_process import process_next_activity_notices
        result = process_next_activity_notices()
    elif function_name == 'process_next_ballot_items':
        from import_export_batches.controllers_batch_process import process_next_ballot_items
        result = process_next_ballot_items()
    elif function_name == 'process_next_general_maintenance':
        from import_export_batches.controllers_batch_process import process_next_general_maintenance
        result = process_next_general_maintenance()
    elif function_name == 'process_next_representatives':
        from import_export_batches.controllers_batch_process import process_next_representatives
        result = process_next_representatives()
    else:
        raise ValueError(f"Unknown batch function: {function_name!r}")

    logger.info("Batch processor complete: function=%s success=%s", function_name, result.get('success'))
    logger.info("Batch processor result: %s", result)
    return result
