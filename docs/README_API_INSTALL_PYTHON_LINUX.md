# README for API Installation: 3b. Installing Python/Django on Linux

[Back to Install Table of Contents](README_API_INSTALL.md)

[PREVIOUS: 2. Get WeVoteServer Code from Github](README_API_INSTALL_CODE_FROM_GITHUB.md)

## Preparing a virtual environment

Taken from here:
https://www.digitalocean.com/community/tutorials/how-to-install-the-django-web-framework-on-ubuntu-16-04#install-through-pip-in-a-virtualenv
    
Perhaps the most flexible way to install Django on your system is with the virtualenv tool. This tool allows you to create virtual Python environments where you can install any Python packages you want without affecting the rest of the system. This allows you to select Python packages on a per-project basis regardless of conflicts with other project's requirements.

We will begin by installing pip from the Ubuntu repositories. Refresh your local package index before starting:

    $ sudo apt-get update

If, instead, you plan on using version 3 of Python, you can install pip by typing:

    $ sudo apt-get install python3-pip

If you installed the Python 3 version of pip, you should type this instead:

    $ sudo pip3 install virtualenv

Now, whenever you start a new project, you can create a virtual environment for it. Start by creating and moving into a new project directory:

    $ mkdir ~/WeVoteServer3.5
    
    $ cd ~/WeVoteServer3.5

Now, create a virtual environment within the project directory by typing:

    $ virtualenv --python=/usr/bin/python3 WeVoteServer
    
Now activate this new virtual environment for WeVoteServer:

    $ cd ~/PythonProjects/WeVoteServer/
    $ source ~/WeVoteServer3.5/WeVoteServer/bin/activate
    (WeVoteServer) $ export PATH="TBD/Postgres.app/Contents/Versions/latest/bin:$PATH"


## Installing Python 3 on Linux

    (WeVoteServer) $ pip3 install django-toolbelt
    (WeVoteServer) $ pip3 install --upgrade pip
    (WeVoteServer) $ pip3 install -r requirements.txt
    (WeVoteServer) $ python3 -m pip install pyopenssl pyasn1 ndg-httpsclient

If installing requirements.txt does not work because of different dependencies, attempt install -r requirements.txt several times.
Also,relying on IDEs like PyCharm may help installing the packages.

Test with this command:
    
    (WeVoteServer) $ python manage.py makemigrations
    (WeVoteServer) $ python manage.py migrate
    (WeVoteServer) $ python3 manage.py runserver


    
[NEXT: 4. Set up Environment](README_API_INSTALL_SETUP_ENVIRONMENT.md)

[Working with WeVoteServer day-to-day](README_WORKING_WITH_WE_VOTE_SERVER.md)

[Back to Install Table of Contents](README_API_INSTALL.md)
