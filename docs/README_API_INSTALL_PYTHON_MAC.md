# README for API Installation: 3a. Installing Python/Django on Mac

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

Test with this command:
    
    (WeVoteServer) $ python manage.py runserver
 

[NEXT: 4. Set up Initial Data](README_API_INSTALL_SETUP_DATA.md)

[Working with WeVoteServer day-to-day](README_WORKING_WITH_WE_VOTE_SERVER.md)

[Back to Install Table of Contents](README_API_INSTALL.md)
