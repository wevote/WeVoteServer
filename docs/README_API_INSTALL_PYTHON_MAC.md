# README for API Installation: 3a. Installing 
Python/Django on Mac

[Back to Install Table of Contents](README_API_INSTALL.md)

[PREVIOUS: 2. Get WeVoteServer Code from Github](README_API_INSTALL_CODE_FROM_GITHUB.md)

## Preparing a virtual environment on Mac

Mac instructions (Based on [this](http://joebergantine.com/blog/2015/apr/30/installing-python-2-and-python-3-alongside-each-ot/))

Install the latest Python 3.x from package: https://www.python.org/downloads/  
(Install 3.6.1 or higher, since Python 3.6 has a known issue)

This allows you to run python3 and pip3. 
(Software gets installed into /Library/Frameworks/Python.framework/Versions/3.6/bin/.)

    $ pip3 install --user virtualenv
    $ vim ~/.bash_profile

Add the following to .bash_profile, save and quit:

    alias virtualenv3='~/Library/Python/3.6/bin/virtualenv'

Update the current Terminal window to use the alias you just saved:

    $ source ~/.bash_profile

Create a place for the virtual environment to live on your hard drive. We recommend installing it 
outside of "PythonProjects" folder:

    $ mkdir /Users/<YOUR NAME HERE>/PythonEnvironments/
    $ cd /Users/<YOUR NAME HERE>/PythonEnvironments/
    $ virtualenv3 WeVoteServer3.6

Now activate this new virtual environment for WeVoteServer:

    $ cd /Users/<YOUR NAME HERE>/PythonProjects/WeVoteServer/
    $ source /Users/<YOUR NAME HERE>/PythonEnvironments/WeVoteServer3.6/bin/activate
    (WeVoteServer) $ export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"
    
If you need to upgrade your Python version later (Macintosh), this command does it:

    $ virtualenv3 -p /Library/Frameworks/Python.framework/Versions/3.6/bin/python3 WeVoteServer3.6.1
    
Note: If you upgrade to Python 3.7.0+, tweepy package will stop working. 'streaming.py' utility has a reserved word problem, which you may fix locally.

## Continue with openssl update 

After Python3 is installed, install pyopenssl and https clients:
 
    (WeVoteServer) $ python3 -m pip install pyopenssl pyasn1 ndg-httpsclient
 
## You will also need libmagic

For mac:

    (WeVoteServer) $ brew install libmagic
    
## Installing Python 3 on Mac

    (WeVoteServer) $ pip install django-toolbelt
    (WeVoteServer) $ pip install --upgrade pip
    (WeVoteServer) $ pip install -r requirements.txt
    (WeVoteServer) $ python3 -m pip install pyopenssl pyasn1 ndg-httpsclient
    
Note: If you are having trouble with some of the packages in requirements.txt ('psycopg2') make sure that the
libraries that pip is looking for under /usr/local/lib exists in that folder, or are linked from another location.
For example, for -lssl and -lcrypto to work, you may wany to do the following:

    $ ln -s /usr/local/opt/openssl/lib/libcrypto.dylib /usr/local/lib/libcrypto.dylib
    $ ln -s /usr/local/opt/openssl/lib/libssl.dylib /usr/local/lib/libssl.dylib
    
Initialize your environment_variables.json file (otherwise makemigrations will fail with an 
'Unable to set the SECRET_KEY variable from os.environ or JSON file' error)

    (WeVoteServer) $ cp ./config/environment_variables-template.json ./config/environment_variables.json


Test with these commands:
    
    (WeVoteServer) $ python manage.py makemigrations
    (WeVoteServer) $ python manage.py migrate
    (WeVoteServer) $ python manage.py runserver
    
Note if you get a **Is the server running locally and accepting connections on Unix domain socket "/tmp/.s.PGSQL.5433"?**
error, make sure that the server port shown in pgAdmin4 (default install is port 5432), matches the port in 
`environment_variables.json`
 

[NEXT: 4. Set up Environment](README_API_INSTALL_SETUP_ENVIRONMENT.md)

[Working with WeVoteServer day-to-day](README_WORKING_WITH_WE_VOTE_SERVER.md)

[Back to Install Table of Contents](README_API_INSTALL.md)
