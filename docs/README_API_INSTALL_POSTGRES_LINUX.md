# README for API Installation: 1b. Installing PostgreSQL on Linux

[Back to Install Table of Contents](README_API_INSTALL.md)

## Installing PostgreSQL on Linux

    $ sudo apt-get install python-psycopg2 
    $ sudo apt-get install python-dev
    $ sudo apt-get install postgresql-client
    $ sudo apt-get install postgresql postgresql-contrib
    $ sudo -u postgres psql postgres
    postgres=# \password postgres
    (NOTE: We recommend using a very simple password like "123" since it is just local development)
    postgres=# \q
    $ sudo -u postgres createdb WeVoteServerDB

See here for more detailed [instructions](https://help.ubuntu.com/community/PostgreSQL)

## Setup - Install pgAdmin 4

We recommend installing pgAdmin 4 as a WYSIWYG database administration tool.
NOTE: You may need to turn off the restriction in "Security & Privacy" on "unidentified developers"
to allow this tool to be installed.
See: http://blog.tcs.de/program-cant-be-opened-because-it-is-from-an-unidentified-developer/

In pgadmin add a server. You can use your sign in name as the server name.

Open this file:

    $ sudo vi /etc/postgres/9.5/main/pg_hba.conf

Change the line:

    # Database administrative login by Unix domain socket
    local   all             postgres                                peer
to

    # Database administrative login by Unix domain socket
    local   all             postgres                                md5
    
Now you should reload the server configuration changes and connect pgAdmin III to your PostgreSQL database server.

    sudo /etc/init.d/postgresql reload

Open pgAdmin 4 and navigate to:

    Server Groups > Servers

1) Right-click on "Servers" and choose "Create > Server"

2) Name: WeVoteServer

3) Switch to "Connection" tab

3a) Host name: localhost

3b) Port: 5432

3c) Maintenance database: postgres

3d) User name: postgres


## Create Database

If you do not see "WeVoteServerDB" in PGAdmin, try this command from your terminal window:

    $ sudo -u postgres createdb WeVoteServerDB



[NEXT: 2. Get WeVoteServer Code from Github](README_API_INSTALL_CODE_FROM_GITHUB.md)

[Working with WeVoteServer day-to-day](README_WORKING_WITH_WE_VOTE_SERVER.md)

[Back to Install Table of Contents](README_API_INSTALL.md)
