# README for API Installation
[Back to root README](README.md)
[Read about working with WeVoteServer](README_WORKING_WITH_WE_VOTE_SERVER.md)

NOTE: We are running Django version 1.8

NOTE: WeVoteServer is built for Python 3.4. It currently still works with Python version 2.7.6.
(tests still have issues with Python 3.4, but everything else works)

## Clone WeVoteServer from github

Create a place to put all of the code from Github:

    $ mkdir /Users/<YOUR NAME HERE>/PythonProjects/

Retrieve “WeVoteServer” into that folder.

## Installing Python 3

Mac instructions (Based on [this](http://joebergantine.com/blog/2015/apr/30/installing-python-2-and-python-3-alongside-each-ot/))

Install Python 3.4 from package: https://www.python.org/downloads/ 
This allows you to run python3 and pip3. 
(Software gets installed into /Library/Frameworks/Python.framework/Versions/3.4/bin/.)

    $ pip3 install --user virtualenv
    $ vim ~/.bash_profile

Add the following to .bash_profile, save and quit:

    alias virtualenv3='~/Library/Python/3.4/bin/virtualenv'

Update the current Terminal window to use the alias you just saved:

    $ source ~/.bash_profile

Create a place for the virtual environment to live on your hard drive. We recommend installing it 
outside of "PythonProjects" folder:

    $ mkdir /Users/<YOUR NAME HERE>/PythonEnvironments/
    $ cd /Users/<YOUR NAME HERE>/PythonEnvironments/
    $ virtualenv3 WeVoteServer3.4

Now activate this new virtual environment for WeVoteServer:

    $ cd /Users/<YOUR NAME HERE>/PythonProjects/WeVoteServer/
    $ source /Users/<YOUR NAME HERE>/PythonEnvironments/WeVoteServer3.4/bin/activate
    $ pip install -r requirements.txt
    $ python manage.py runserver

### Running Linux?
If you are installing on a Linux environment, we recommend the following steps within your virtual environment. If you
are installing on a Mac or Windows machine, you can skip these steps.

DO:

    sudo apt-get install python-psycopg2 
    sudo apt-get install python-dev
    pip install psycopg2 

THEN:

    pip install django-toolbelt
    pip install --upgrade pip
    pip install -r requirements.txt

## Setup - Install the Postgres database

### METHOD 1 (Mac)
For Mac, download and install the DMG from [http://postgresapp.com/](http://postgresapp.com/)

Run this on your command line:

    export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/9.4/bin

Start up the command line for postgres (there is an 'open psql' button/navigation item if you installed postgresapp.
Run these commands:

    create role postgres;
    alter role postgres with login;

### METHOD 2 (Windows)

Install Postgres:

    $ sudo port install postgresql94
    $ sudo port install postgresql94-server

### METHOD 3 (linux Ubuntu)

Follow [these instructions](https://help.ubuntu.com/community/PostgreSQL)

## Setup - Install PG Admin III

We recommend installing pgAdmin3 as a WYSIWYG database administration tool.
NOTE: You may need to turn off the restriction in "Security & Privacy" on "unidentified developers"
to allow this tool to be installed.
See: http://blog.tcs.de/program-cant-be-opened-because-it-is-from-an-unidentified-developer/

In pgadmin add a server. You can use your sign in name as the server name.


## Setup - Environment Variables Configuration - config/environment_variables.json

WeVoteServer is currently configured (in manage.py) to look for a "config/local.py" file (configured in the
"config/settings.py" file). When we run this on a production server, we will startup with a production settings
file like "production_heroku.py".

Copy "environment_variables-template.json" to "environment_variables.json". You will configure many variables for your
local environment in this file. New variables needed by WeVoteServer will be added to
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
specify the level assigned to each message. You can change this to info items by changing this:

    LOG_FILE_LEVEL = logging.INFO

## Set up GeoIP

###  Install the C library

    $ git clone https://github.com/maxmind/geoip-api-c.git
    $ cd geoip-api-c
    $ ./bootstrap
    $ ./configure
    $ make
    $ make check
    $ make install
    $ cd ..
    
On OS X 10.10.5 I got an error (autoreconf: command not found), and had to do this first:
    
    $ brew install automake
    $ brew install libtool

###  Run the command that downloads the GeoLite database from the WeVoteServer root folder (Where this README lives)

    $ ./manage.py update_geoip_data

## Test that WeVoteServer is running

Start up the webserver:

    $ cd /Users/<YOUR NAME HERE>/PythonProjects/WeVoteServer/
    $ source /Users/<YOUR NAME HERE>/PythonEnvironments/WeVoteServer3.4/bin/activate
    $ pip install -r requirements.txt
    $ python manage.py runserver

Find admin tools here:

    http://localhost:8000/admin

Find documentation for all of the APIs here:

    http://localhost:8000/apis/v1/docs

## Setup - Database Creation

If you would like to match the local database settings from the "config/environment_variables.json" file,
(Search for "DATABASES"):

    createdb WeVoteServerDB

Populate your database with the latest database tables:

    python manage.py makemigrations
    python manage.py migrate

Create the initial database:

    $ python manage.py syncdb

When prompted for a super user, enter your email address and a simple password. This admin account is only used in development.

If you are not prompted to create a superuser, run the following command:

    python manage.py createsuperuser
    
## Sample data and the GOOGLE_CIVIC_API_KEY
Sample data is provided. You can load this data by clicking the "Import Test Data" link on this page (in the "Maintenance" section):

    http://localhost:8000/admin
 
If you need to retrieve fresh ballot data, you will need to sign up for a Google Civic API key:

  - Go here:  https://console.developers.google.com/projectselector/apis/credentials?pli=1
  - Create a new project
  - Click Credentials -> New credentials -> API Key -> Browser Key
  - Copy your newly generated key and paste it into config/environment_variables.json as the value for GOOGLE_CIVIC_API_KEY
    
[Read about working with WeVoteServer](README_WORKING_WITH_WE_VOTE_SERVER.md)

## Setup - Heroku Configuration

NOTE: These instructions are in progress.

We use Heroku for publishing a public version anyone can play with , and you can publish a public version too. Here are the instructions:
https://devcenter.heroku.com/articles/getting-started-with-django

In the config/setting.py file, search for "Heroku". There are comments that tell you which parts of the settings file to comment or uncomment to get a version running on Heroku.

[Back to root README](README.md)
