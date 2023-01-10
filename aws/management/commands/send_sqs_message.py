from django.core.management import call_command
from django.core.management.base import BaseCommand
from aws.controllers import submit_web_function_job


class Command(BaseCommand):
    help = 'Sends a test SQS message for testing job queues.'

    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument(
            'args', metavar='fixture', nargs='*',
            help='Arguments: function_name body',
        )

    def handle(self, *args, **options):
        if len(args) != 2 or args[0] == 'help':
            print("Usage: $ python manage.py send_sqs_message function_name body")
            print("Example: $ python manage.py send_sqs_message TestFunctionName '{ \"field\": \"test\" }'")
        else:
            print("Sending test SQS message, function: " + args[0] + ", body: " + str(args[1]))
            submit_web_function_job(args[0], args[1])

        print("End of send_sqs_message")
