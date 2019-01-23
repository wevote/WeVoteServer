import os
import gzip
import urllib

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


download_folder = settings.GEOIP_PATH


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write('\nIf you want to get an updated free database (GeoLite2-City.mmdb) download it from https://dev.maxmind.com/geoip/geoip2/geolite2/, unzip it, and overwrite the source controlled version')
        self.stdout.write('\nDownload the paid db from MaxMind for more precise results. Ask Dale for the credentials')
