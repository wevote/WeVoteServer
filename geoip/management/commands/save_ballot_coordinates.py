from config.base import get_environment_variable
from django.core.management.base import BaseCommand
from geopy.geocoders import get_geocoder_for_service
from geopy.exc import GeocoderQuotaExceeded
from ballot.models import BallotReturned

# GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")


class Command(BaseCommand):
    help = 'Populates the latitude and longitude fields of BallotReturned'

    def populate_latitude_for_ballots(self):
        for b in BallotReturned.objects.filter(latitude=None).order_by('id'):
            full_ballot_address = '{}, {}, {} {}'.format(
                b.normalized_line1, b.normalized_city, b.normalized_state, b.normalized_zip)
            location = self.google_client.geocode(full_ballot_address, sensor=False)
            if location is None:
                raise Exception('Could not find a location for ballot {}'.format(b.id))
            b.latitude, b.longitude = location.latitude, location.longitude
            print('ballot {}, found latitude {}, longitude {}'.format(b.id, b.latitude, b.longitude))
            b.save()

    def handle(self, *args, **options):
        self.google_client = get_geocoder_for_service('google')()  # Add in parens GOOGLE_MAPS_API_KEY

        while BallotReturned.objects.filter(latitude=None).exists():
            try:
                self.populate_latitude_for_ballots()
            except GeocoderQuotaExceeded:
                self.google_client = get_geocoder_for_service('google')()

        print('Success! All BallotReturned objects now have latitude and longitude populated.')
