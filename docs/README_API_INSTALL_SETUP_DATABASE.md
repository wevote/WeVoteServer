# README for API Installation: 5. Set up Database

[Back to Install Table of Contents](README_API_INSTALL.md)

[BACK: 4. Set up Environment](README_API_INSTALL_SETUP_ENVIRONMENT.md)

## Before Installing Database

Please make sure you have installed PostgreSQL:

1a. [Installing PostgreSQL on Mac](README_API_INSTALL_POSTGRES_MAC.md)

1b. [Installing PostgreSQL on Linux](README_API_INSTALL_POSTGRES_LINUX.md)

## Setup - Database Creation

Make sure you have a database that matches the local database settings from the "config/environment_variables.json" file,
(Search for "DATABASES"), update "DATABASE_NAME":"wevoteserverdb". Using the database tool you prefer create the following Database. (You probably already created
the database in a previous step.)

    WeVoteServerDB
    
Also make sure you are running in your virtual environment, signified by the "(WeVoteServer)".

Populate your database with the latest database tables using these terminal commands (You probably already did this in 
a previous step, but it doesn't hurt anything to do this twice):

    (WeVoteServer3.11) $ pip install psycopg2 
    (WeVoteServer3.11) $ python manage.py makemigrations
    (WeVoteServer3.11) $ python manage.py migrate
    (WeVoteServer3.11) $ python manage.py createcachetable

When prompted for a super user, enter your email address and a simple password. This admin account is only used in development.

If you are not prompted to create a superuser, run the following command:

    python manage.py createsuperuser
    
## Test that WeVoteServer is running

Start up the WeVoteServer on Mac (You probably already installed requirements.txt in an earlier step, but it doesn't
hurt to do it again.):

    $ cd /Users/<YOUR NAME HERE>/PythonProjects/WeVoteServer/
    $ source /Users/<YOUR NAME HERE>/PythonEnvironments/WeVoteServer3.11/bin/activate
    (WeVoteServer3.11) $ pip install -r requirements.txt
    (WeVoteServer3.11) $ python manage.py runserver

Start up the WeVoteServer on Linux:

    $ cd ~/PythonProjects/WeVoteServer/
    $ source ~/PythonEnvironments/WeVoteServer3.11/bin/activate
    (WeVoteServer3.11) $ pip install -r requirements.txt
    (WeVoteServer3.11) $ python manage.py runserver

[Having troubles? See Installation Troubleshooting](README_INSTALLATION_TROUBLESHOOTING.md)

## Set up an admin account in your local WeVoteServer database

Now, create an account for yourself to login to the management pages of the WeVoteServer.
At WeVote, we call end users "voters".  This new "voter" will have all the 
rights that you (as a developer) need to log in to 
[http://localhost:8000/admin/](http://localhost:8000/admin/).  Once logged in you can start synchronizing data (downloading ballot and issue 
data from the master server in the cloud, to your local server).
    
1.  Open the file `WeVoteServer/voter/controllers_voter_create.py` and edit the variables to your own information.

2.  Edit the default information in this file (first_name, last_name, etc.) to be personalized for yourself, with your own information:

```
first_name = "Samuel"
last_name = "Adams"
email = "samuel@adams.com"
password = "GoodAle1776"
```

3.  Set `allow_create` to True, so when you run the script, changes can be made to your local database.

```
allow_create = True
```

4.  Visit http://localhost:8000/voter/create_dev_user 
    or https://wevotedeveloper.com:8000/voter/create_dev_user Once you have visited
    that page, you should have a new admin account you can sign in with.

5.  Navigate to [http://localhost:8000/admin/](http://localhost:8000/admin/) and sign in with your new username/password  (for example mine is stevepodell/stevePG.).    

6.  **Your local instance of the WeVoteServer is now setup and running** (although there is no election 
    data stored in your Postgres instance, for it to serve to clients at this point).


## Grant yourself Admin rights

Find admin tools here:

    http://localhost:8000/admin

Login with Email:
If you created superuser with this command "python manage.py createsuperuser" during Setup - Database Creation step,
login with same email id and password, otherwise create superuser with the following command and use that email to
login:

    python manage.py createsuperuser
    
Note 1: If you ever need to update the password for this account, you can use this command, with your email address: `python manage.py changepassword dalemcgrew@yahoo.com`

Note 2: The first time you sign in, you will need to sign out, and then sign in again to make sure you have all of your access rights.

or

Login with Twitter:
Please contact Dale.McGrew@WeVoteUSA.org for configuration settings you can add to your local
WeVoteServer/config/environment_variables.json file.

    Click "Sign in with Twitter" and use your Twitter credentials to Sign-In.

or

Login with Facebook:
Please contact Dale.McGrew@WeVoteUSA.org for configuration settings you can add to your local
WeVoteServer/config/environment_variables.json file.

    Click "Sign in with Facebook" and use your Facebook credentials to Sign-In.
    
After you have signed in, you will see an error message in red that states "You must sign in with account that has
Verified Volunteer rights to see that page." Just below the error message, there will be a field "we_vote_id" with a 
text string like "wv01voter1234" next to it, note the we_vote_id number.

### Give yourself Admin rights via PGAdmin

Open pgAdmin 4 and navigate to:

    Server Groups > Servers > WeVoteServer 

If you do not see "WeVoteServer", then do the following:

1) Right-click on "Servers" and choose "Register > Server"

2) Name: WeVoteServer

3) Switch to "Connection" tab

3a) Host name: localhost

3b) Port: 5432

3c) Maintenance database: postgres

3d) User name: postgres

Double click on WeVoteServerDB (there may be a red x thru it). It will prompt you for a password; leave it blank and click
OK. You may see an additional warning screen about saving passwords, if so, click ok. 

Once you are connected, navigate to:

    WeVoteServerDB > Schemas > public > Tables > voter_voter

Then, right click, and in the menu that appears, select:

    View Data > View Top 100 rows

In the new window that opens, scroll down and find the we_vote_id number, noted above. Scroll to the right to locate the box
"is_admin" click on it once, and a box will appear, click it and change it to TRUE. Then, go back to your browser, 
and click on:

    Back to Admin Home
    
### Give yourself Admin rights via command line

Run this command from your Postgres command line. Replace WE_VOTE_ID_HERE with the actual we_vote_id found above:

    UPDATE voter_voter SET is_admin=true WHERE we_vote_id='WE_VOTE_ID_HERE';
    
Once you see "admin: True" on your account page, sign out, and sign in again. This will lock in place your admin rights.

## Test your access

Now, you should be able to access the admin tools here:

    http://localhost:8000/admin

Find documentation for all the APIs here:

    http://localhost:8000/apis/v1/docs


[NEXT: 6. Set up Initial Data](README_API_INSTALL_SETUP_DATA.md)
    
[Working with WeVoteServer day-to-day](README_WORKING_WITH_WE_VOTE_SERVER.md)

[Back to Install Table of Contents](README_API_INSTALL.md)
