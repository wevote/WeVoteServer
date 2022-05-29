# README for API Installation: 2. Get WeVoteServer Code from Github

[Back to Install Table of Contents](README_API_INSTALL.md)

[BACK: 1a. Installing PostgreSQL on Mac](README_API_INSTALL_POSTGRES_MAC.md)

[BACK: 1b. Installing PostgreSQL on Linux](README_API_INSTALL_POSTGRES_LINUX.md)


## Clone WeVoteServer from github

Create a place to put all the code from Github (this example is for Mac):

    $ mkdir /Users/<YOUR NAME HERE>/PythonProjects/
    
This example is for Linux:

    $ mkdir ~/PythonProjects/WeVoteServer/

Retrieve “WeVoteServer” into that folder:

1. Create a fork of wevote/WeVoteServer.git. You can do this from https://github.com/wevote/WeVoteServer with the "Fork" button  
(upper right of screen)

1. Go to your fork repo page, click green 'Clone or Download' button, copy the URL and clone your fork to local dev:

    $ cd  ~/PythonProjects

    $ git clone https://github.com/wevote/WeVoteServer.git
 
1. Change into your local WeVoteServer repository folder, and set up a remote for upstream: 
    
       $ cd  ~/PythonProjects/WeVoteServer

       $ git remote add upstream git@github.com:wevote/WeVoteServer.git

## Updating openssl on Mac

This will ensure you will be able to test donations with the most up to date TLS1.2:

 `brew install openssl`


[NEXT: 3a. Install Python/Django on Mac](README_API_INSTALL_PYTHON_MAC.md)

[NEXT: 3b. Install Python/Django on Linux](README_API_INSTALL_PYTHON_LINUX.md)

[Working with WeVoteServer day-to-day](README_WORKING_WITH_WE_VOTE_SERVER.md)

[Back to Install Table of Contents](README_API_INSTALL.md)
