# README for API Installation: 4. Set up Environment

[Back to Install Table of Contents](README_API_INSTALL.md)

[BACK: 3a. Install Python/Django on Mac](README_API_INSTALL_PYTHON_MAC.md)

[BACK: 3b. Install Python/Django on Linux](README_API_INSTALL_PYTHON_LINUX.md)


## Setup - Environment Variables Configuration - WeVoteServer/config/environment_variables.json

NOTE: IMPORTANT STEP

Copy "WeVoteServer/config/environment_variables-template.json" to "WeVoteServer/config/environment_variables.json". 
You will configure many variables for your local environment in this file. 

New variables needed by WeVoteServer will be added to
"environment_variables-template.json" from time to time, so please check for updates by comparing your local version
with the template file.

### LOG_FILE
Create a file on your computer to match the one expected in the environment_variables.json file:

    sudo mkdir /var/log/wevote/
    sudo touch /var/log/wevote/wevoteserver.log
    sudo chmod -R 0777 /var/log/wevote/

As configured in github, only errors get written to the log.
Logging has five levels: CRITICAL, ERROR, INFO, WARN, DEBUG.
It works as a hierarchy (i.e. INFO picks up all messages logged as INFO, ERROR and CRITICAL), and when logging we
specify the level assigned to each message. You can change this to info items by changing the LOG_FILE_LEVEL variable 
in the WeVoteServer/config/environment_variables.json file to "INFO".

## Set up GeoIP


###  Only for Mac:  Install the C library on Mac (see below for Linux)

    $ cd /Users/<YOUR NAME HERE>/PythonProjects/WeVoteServer/
    $ git clone https://github.com/maxmind/geoip-api-c.git
    $ cd geoip-api-c
    $ brew install automake
    $ brew install libtool
    $ ./bootstrap
    
If you have problems with ./bootstrap command, try this. On OS X 10.10.5 I got an error 
(autoreconf: command not found), and had to do this first. For directions on installing "brew" see
[http://brew.sh/](http://brew.sh/):
    
If you had to install "brew", try this again.

    $ ./bootstrap
    $ ./configure
    $ make
    
In the "make check" step, you may see some errors like "make[2]: * [install-libLTLIBRARIES] Error 1". 
These errors won't prevent geoip from working.
    
    $ make check
    $ make install
    $ cd ..

### Only for Linux:  Install the C library on Linux

    $ git clone https://github.com/maxmind/geoip-api-c.git
    $ cd geoip-api-c
    $ ./bootstrap

### Mac and Linux:  Pull data

Run the command that downloads the GeoLite database from the WeVoteServer root folder (Where this README lives)

    $ cd ..
    $ ./manage.py update_geoip_data

###  Only for Linux: Install the C library on Linux

    $ cd ~/PythonProjects/WeVoteServer/
    $ git clone https://github.com/maxmind/geoip-api-c.git
    $ cd geoip-api-c
    $ ./bootstrap
    $ ./configure
    $ make
    
In the "make check" step, you may see some errors like "make[2]: * [install-libLTLIBRARIES] Error 1". 
These errors won't prevent geoip from working.
    
    $ make check
    $ make install
    $ cd ..
    
### Mac and Linux:  Run the command that downloads the GeoLite database from the WeVoteServer root folder:

    $ ./manage.py update_geoip_data
    
### Only for Mac: Install geoip locally:

    $ brew install geoip
    
...or:

    $ pip install geoip


[NEXT: 5. Set up Database](README_API_INSTALL_SETUP_DATABASE.md)
    
[Working with WeVoteServer day-to-day](README_WORKING_WITH_WE_VOTE_SERVER.md)

[Back to Install Table of Contents](README_API_INSTALL.md)
