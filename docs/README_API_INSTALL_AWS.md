# README for Amazon Web Services

[Back to Install Table of Contents](README_API_INSTALL.md)

[Installation Troubleshooting](README_INSTALLATION_TROUBLESHOOTING.md)
    
### On Amazon Web Services - NOT for local install

Buy the latest database ("GEO-133	GeoIP Legacy City with DMA/Area Codes") at http://www.maxmind.com

Find and copy the GZIP download link from this page https://www.maxmind.com/en/download_files which will look like:

    https://download.maxmind.com/app/geoip_download?edition_id=133&date=20160517&suffix=tar.gz&license_key=KEYHERE

Transfer it to the live API server:
    
    $ cd /home/wevote/WeVoteServer/geoip/import_data/
    $ wget "https://download.maxmind.com/app/geoip_download? (FILL IN ACTUAL LINK FROM THEIR DOWNLOADS PAGE)"
    $ mv geoip_download\?edition_id\=133\&date\=20160202 GeoIP-133_DATE_HERE.tar.gz
    $ chmod 0777 GeoIP-133_DATE_HERE.tar.gz
    $ tar zxvf GeoIP-133_DATE_HERE.tar.gz
    $ cp GeoIP-133_20160202/GeoIPCity.dat .
    $ chmod 0777 *.*


[Back to Install Table of Contents](README_API_INSTALL.md)
