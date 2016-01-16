import os
import gzip
import urllib
import urlparse

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

download_folder = settings.GEOIP_PATH

class Command(BaseCommand):
    help = 'Updates GeoIP data in %s' % download_folder
    base_url = 'http://www.maxmind.com/download/geoip/database/'
    files = ['GeoLiteCity.dat.gz', 'GeoLiteCountry/GeoIP.dat.gz']

    def handle(self, *args, **options):
        for path in self.files:
            root, filepath = os.path.split(path)
            dowloadpath = os.path.join(download_folder, filepath)
            downloadurl = urlparse.urljoin(self.base_url, path)
            self.stdout.write('Downloading %s to %s\n' % (downloadurl, dowloadpath))
            urllib.urlretrieve(downloadurl, dowloadpath)
            outfilepath, ext = os.path.splitext(dowloadpath)
            if ext != '.gz':
                raise CommandError('Something went wrong while '
                                   'decompressing %s' % dowloadpath)
            self.stdout.write('Extracting %s to %s\n' % (dowloadpath, outfilepath))
            infile = gzip.open(dowloadpath, 'rb')
            outfile = open(outfilepath, 'wb')
            try:
                outfile.writelines(infile)
            finally:
                infile.close()
                outfile.close()
            self.stdout.write('Deleting %s\n' % dowloadpath)
            os.remove(dowloadpath)
            self.stdout.write('Done with %s' % path)
