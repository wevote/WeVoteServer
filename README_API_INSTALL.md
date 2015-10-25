# README for API Installation
[Back to root README](README.md)
[Read about working with WeVoteServer](README_WORKING_WITH_WE_VOTE_SERVER.md)

## Setup - Dependencies

NOTE: We are running Django version 1.8

NOTE: We are running Python version 2.7.6 and in the process of upgrading to Python 3

Once you have cloned this repository to your local machine, set up a virtual environment:

    cd /path_to_dev_environment/WeVoteServer/
    virtualenv venv
    source venv/bin/activate

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

### METHOD 1
For Mac, download and install the DMG from [http://postgresapp.com/](http://postgresapp.com/)

Run this on your command line:

    export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/9.4/bin

Start up the command line for postgres (there is an 'open psql' button/navigation item if you installed postgresapp.
Run these commands:

    create role postgres;
    alter role postgres with login;

### METHOD 2

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

### GOOGLE_CIVIC_API_KEY
If you are going to connect to Google Civic API, add your key to this variable.
TODO: Describe the process of getting a Google Civic API Key


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

    Import GeoIP data:

        $ python manage.py update_geoip_data

## Test that WeVoteServer is running

Start up the webserver:

    cd WeVoteServer
    source venv/bin/activate
    pip install -r requirements.txt
    python manage.py runserver

Find admin tools here:

    http://localhost:8000/admin

Find documentation for all of the APIs here:

    http://localhost:8000/apis/v1/docs
    
[Read about working with WeVoteServer](README_WORKING_WITH_WE_VOTE_SERVER.md)

## Setup - Heroku Configuration

NOTE: These instructions are in progress.

We use Heroku for publishing a public version anyone can play with , and you can publish a public version too. Here are the instructions:
https://devcenter.heroku.com/articles/getting-started-with-django

In the config/setting.py file, search for "Heroku". There are comments that tell you which parts of the settings file to comment or uncomment to get a version running on Heroku.

[Back to root README](README.md)
