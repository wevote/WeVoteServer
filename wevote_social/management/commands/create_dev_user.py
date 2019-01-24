from django.core.management import call_command
from django.core.management.base import BaseCommand
from voter.models import VoterManager



class Command(BaseCommand):
    help = 'Creates an initial user for you (the developer) without setting up oAuth on this local WeVoteServer.'

    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument(
            'args', metavar='fixture', nargs='*',
            help='Path(s) to fixtures to load before running the server.',
        )
        parser.add_argument(
            '--noinput', '--no-input', action='store_false', dest='interactive',
            help='Tells Django to NOT prompt the user for input of any kind.',
        )
        parser.add_argument(
            '--addrport', default='',
            help='Port number or ipaddr:port to run the server on.',
        )
        parser.add_argument(
            '--ipv6', '-6', action='store_true', dest='use_ipv6',
            help='Tells Django to use an IPv6 address.',
        )

    def handle(self, *args, **options):
        if len(args) != 4 or args[0] == 'help':
            print("Usage : python manage.py initialize_dev_user first_name last_name email password")
            print("Example : python manage.py initialize_dev_user Di Feinstein senator@feinstein.senate.gov secretPwd")
        else:
            print("Creating developer first name=" +  args[0] + ", last name=" + args[1] + ", email=" + args[2])
            VoterManager().create_developer(args[0], args[1], args[2], args[3])

        # create_developer(self, first_name, last_name, email, password

        print("End of create_dev_user")
