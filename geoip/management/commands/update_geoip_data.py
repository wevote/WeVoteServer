import os
import gzip
import urllib

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


download_folder = settings.GEOIP_PATH


class Command(BaseCommand):
    help = 'Updates GeoIP data in {}'.format(download_folder)
    base_url = 'http://www.maxmind.com/download/geoip/database/'
    files = ['GeoLiteCity.dat.gz', 'GeoLiteCountry/GeoIP.dat.gz']

    def handle(self, *args, **options):
        for path in self.files:
            root, filepath = os.path.split(path)
            dowloadpath = os.path.join(download_folder, filepath)
            download_url = urllib.parse.urljoin(self.base_url, path)
            self.stdout.write('Downloading {} to {}\n'.format(download_url, dowloadpath))
            urllib.request.urlretrieve(download_url, dowloadpath)
            outfilepath, ext = os.path.splitext(dowloadpath)
            if ext != '.gz':
                raise CommandError('Something went wrong while decompressing {}'.format(dowloadpath))
            self.stdout.write('Extracting {} to {}\n'.format(dowloadpath, outfilepath))
            with gzip.open(dowloadpath, 'rb') as infile, open(outfilepath, 'wb') as outfile:
                outfile.writelines(infile)
            self.stdout.write('Deleting {}\n'.format(dowloadpath))
            os.remove(dowloadpath)
            self.stdout.write('Done with {}\n'.format(path))

            self.stdout.write('\nDownload the paid db from MaxMind for more precise results. Ask Dale for the credentials'.format(path))
