from django.core.management import call_command
from django.core.management.base import BaseCommand
from voter.models import VoterManager



class Command(BaseCommand):
    help = 'Creates an initial user for you (the developer) without setting up oAuth on this local WeVoteServer.'

    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument(
            'args', metavar='fixture', nargs='*',
            help='Arguments: first_name last_name email password',
        )

    def handle(self, *args, **options):
        if len(args) != 4 or args[0] == 'help':
            print("Usage: $ python manage.py create_dev_user first_name last_name email password")
            print("Example: $ python manage.py create_dev_user Dianne Feinstein senator@feinstein.senate.gov DiFiPass")
        else:
            print("Creating developer first name=" +  args[0] + ", last name=" + args[1] + ", email=" + args[2])
            VoterManager().create_developer(args[0], args[1], args[2], args[3])
            # create_developer(self, first_name, last_name, email, password

        print("End of create_dev_user")
