# README for Simplified Installation with PyCharm on a Mac
[Back to root README](../README.md)


**Caveat:  Operating Systems, IDEs, tools, packages, dependencies, and languages are constantly changing.**
We do our best to keep this procedure current with the external changes.  Tell us if you run into troubles.

## Installing WeVoteServer: On a new Mac
These instructions are for a new Mac, or at least a Mac that hasn't been used for 
Python development before.  Some of these tools may already be setup on your Mac, but
reinstalling them causes no harm, skip the parts you are sure you already have.

If you have never installed Postgres on your Mac (or don't mind fully deleting any Postgres that you have already 
installed on your Mac), follow these instructions.  They should take an hour or so to complete. 

1. Install the Chrome browser for Mac

2. Open the Mac "App Store" app, and download the current version of Apple's Xcode, which includes "c" language compilers 
    and native git integration. This download also includes Apple's Xcode IDE for macOS and iOS native development.

    **Note: Xcode requires about 13 GB of disk space, if you don't have much that room on your Mac, it is sufficient 
    to download only the "Xcode Command Line Tools".  Unfortunately you need to sign up as an Apple developer to do that.
    Download (the latest version of) "Command Line Tools for Xcode 13" at 
    [https://developer.apple.com/download/more/](https://developer.apple.com/download/more/).  These tools only require 185 MB 
    of disk space.  If you choose to download only the tools, skip on to Step 6.**
    
    If you have enough disk space, it is much easier to just install all of Xcode (including the full Xcode IDE) from 
    the app store:
    <img width="500" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/DownloadXcodeFromAppStore.png"> 

3. Start xcode (you can find it with Spotlight, or in the Application folder)

    <img width="500" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/FindXcode.png"> 


4. July 2022, this step happens without a prompt:  When prompted, download the "Additional Components" (the Command Line Tools).  This takes many minutes to complete.

5. When you get to "Welcome to Xcode", quit out of the app. (For the WeVoteServer, we only need the command line tools that 
come with Xcode.)

   <img width="500" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/WelcomeToXcode.png"> 

6. Navigate in Chrome to [GitHub](https://GitHub.com).  Create a personal account if you don't already have one.
 
7. Within the GitHub site, navigate to [https://GitHub.com/wevote/WeVoteServer](https://GitHub.com/wevote/WeVoteServer). 
    Create a fork of wevote/WeVoteServer.git by selecting the "Fork" button (in the upper right of screen).
    
   <img width="800" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/Fork3.png"> 


8. Download and install the Community version of PyCharm, it's free!  (If you are a student, you can get PyCharem Professional for free.  Professional is nice, but not necessary.)
    [https://www.jetbrains.com/pycharm/download/#section=mac](https://www.jetbrains.com/pycharm/download/#section=mac)

9. StartPyCharm, and press the 'Get from VCS' button.

   <img width="800" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/PyCharmStartScreen2021.png"> 

10. Clone your fork of the git repository, by copying the URL to the repository into the URL filed, then press the Clone button.
_What this means in english is that you have created a copy in GitHub of the WeVoteServer codebase, and cloning it downloads
a copy of your copy to your Mac.  At this instant, the 'develop' branch of wevote/WeVoteServer matches
    your branch (in this example) SailingSteve/WeVoteServer and also matches the code on your Mac.

    <img width="800" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/PyCharmStartScreenURL2021.png">

11. The PyCharm IDE appears in 'Dracula' mode, with the repository loaded to your disk, and ready to edit.

    <img width="800" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/PyCharmDracula.png"> 

12. If you like 'Dracula' mode, you can skip this step.  Open PyCharm/Preferences and press the
'Sync with OS' button to match the display mode of your Mac.  
   
    <img src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/transparent8x8.png"> 
    <img width="800" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/PyCharm2021OutOfDracula.png"> 


13. In PyCharm/Preferences/Plugins enable the IdeaVim tool (this takes a while).  
Feel free to add any other PyCharm tools that you would like!  When done press 'Ok', and the IDE will reboot.

    <img width="700" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/CustomizePyCharm2021.png"> 

14.  If you are using one of the newer Macs with Apple Silicon processor, he installer offers the "Apple Silicon Version" which is better and more stable -- take it if it is offered!

15. If the Apple top menu, shows "Git" skip this step.  If it says "VCS", the follow this step to configure Git

    <img width="500" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/VCSorGIT2.png"> 
   
    Select 'Git' on the VCS meu, and press Ok.
   
    <img width="700" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/AddGit.png"> 

16. In PyCharm set your git remotes. Navigate to the Git/'Manage Remotes...' dialog  (July 2022:  these two images might be reversed! (Verify!) But the results in the next step are corect.)

    ![ScreenShot](images/RemotesUpstream.png)

    The WeVoteServer project defines upstream and origin differently than most projects.

    Click the edit (pencil) icon, and change the word origin to upstream. This is how it looks after the change.
   
    ![ScreenShot](images/RemotesOrigin.png)

17. Then add a remote for your private branch by pressing the '+' button on the Git Remotes dialog.  Add the url for your
     fork of the WeVoteServer project origin (copy the url from the GitHub website). In this example, the developer 
     is "SailingSteve".
    
    ![ScreenShot](images/AddUpstream2021.png)
18. When the cloning is complete, it will look something like this.
    
     ![ScreenShot](images/CorrectOrigin2021.png)
    
     Press Ok to close the dialog

19. In PyCharm copy `environment_variables-template.json` to `environment_variables.json`

     ![ScreenShot](images/PyCharmTemplateCopy2021.png)

     Right click on `environment_variables-template.json` and select 'Copy', then right click paste on the `config` 
     directory and select 'Paste' in the pop-up, and then in the copy dialog that open up, and change the "new name:" to 
     `environment_variables.json`
    
     If you skip this step, in a much later step, when you run "makemigrations", it will fail with an 
     'Unable to set the **** variable from "os.environ" or JSON file' error.
    
     **There are a number of secret values in `environment_variables.json` that are not in source control,
     you will need to check in with Dale, as you find that you need them.**

20. In PyCharm, open the Terminal window and accept use of the z shell (if you want to use some other shell, feel free to skip this step).
   
     ![ScreenShot](images/AcceptZShell.png)

     The terminal opens up with the project root directory set as the pwd (which is handy).

21. In the PyCharm terminal window download [Homebrew]( https://brew.sh/) ("the missing package manager for macOS") by entering
the following command:
    
     ``` 
     $ /bin/bash -c "$(curl -fsSL https://raw.GitHubusercontent.com/Homebrew/install/master/install.sh)"
     ``` 

     This loads and runs a Ruby script (Ruby comes pre-installed in macOS), and Ruby uses curl (also pre-loaded) to pull the file 
    into the bash (terminal) command shell for execution.  This Ruby script also internally uses 'sudo' which temporarily gives 
     the script root privileges to install software, so you will need to know an admin password for your Mac.  

     This script can take a few minutes to complete.

22. Install the latest version of Python

     ```
     $ brew install python
     ```
     If an older version of Python has been installed, and the installation fails, you will see the following error:
     ```
     Error: python@3.9 3.9.1_1 is already installed
     To upgrade to 3.9.5, run:
       brew upgrade python@3.9
     Steve@Vickies-MacBook-Pro-2037 WeVoteServer % 
     ```
     In which case you run the suggested upgrade command, in this example it would be `brew upgrade python@3.9`, then finally export the path as shown below.
     ```
     $ export PATH="/usr/local/opt/python/libexec/bin:$PATH"
     ```
23. Test that the newly installed Python is in the path. macOS comes with Python 2 preinstalled, so
if the reported version is 2, then add the newly loaded python to the path with the export command. 
Then confirm that the default python is now version 3.9 or later.  (Version 3.6 has problems with macOS Big Sur or later)

     ```
     Steve@Vickies-MacBook-Pro-2037 WeVoteServer % python --version
     Python 2.7.16
     Steve@Vickies-MacBook-Pro-2037 WeVoteServer % export PATH="/usr/local/opt/python/libexec/bin:$PATH"
     Steve@Vickies-MacBook-Pro-2037 WeVoteServer % python --version                                     
     Python 3.9.5
     Steve@Vickies-MacBook-Pro-2037 WeVoteServer % 
     ```   
     2021: For an 'Apple M1 Max' ARM-64 Processor...
     ```
     stevepodell@Steves-MBP-M1-Dec2021 WeVoteServer % python --version
     Python 2.7.18
     stevepodell@Steves-MBP-M1-Dec2021 WeVoteServer % export PATH="/opt/homebrew/opt/python@3.9/libexec/bin:$PATH"
     stevepodell@Steves-MBP-M1-Dec2021 WeVoteServer % python --version                                            
     Python 3.9.9
     stevepodell@Steves-MBP-M1-Dec2021 WeVoteServer % 
     ```
     Note July 2022:  n the homebrew directory (not in the venv), had to make a symlink between python3 and python so that psycopg2-binary could find python.  (To be verified)      

24. If python --version fails,
    try 
    ```
    ln -s /opt/homebrew/bin/python3 /opt/homebrew/bin/python
    ```
needed to install postgres before the requirements because psyco3-3 binary requires pg_config which is not installed yet.

25. Set up a Virtual Environment with the new Python Interpreter.  
Navigate to: PyCharm/Preferences/Project: WeVoteServer/Python Interpreter.

    <img width="800" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/NoVENV.png"> 

26. Click the Gear icon, then select "Add".  PyCharm will detect the latest interpreter from the PATH environment variable, 
    and pre-populate the dialog.  Check the two checkboxes `Inherit global site-packages` and `make available to all projects`.
   
    <img width="800" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/Py3-9Selected.png"> 

    Confirm that the 'Base interpreter' field shows us using the Python version that you just downloaded, and it knows the location for pip, setuptools, and wheel (3 python utilities).
    Then press Ok.
   
    ![ScreenShot](images/VenvCompleted.png)

27. Confirm that the new virtual environment is in effect, by closing all open Terminal windows within
PyCharm and opening a new one.

    <img width="700" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/VenvConfirm2.png"> 

    If you see '(venv)' at the beginning of the command line, all is well.
   
28. Install OpenSSL, the pyopenssl and https clients:
 
     `(WeVoteServerPy3.7) $ brew install openssl`
     If it is already installed, no worries!

29. Link libssl and libcrypto so that pip can find them:
     ```
     $ ln -s /usr/local/opt/openssl/lib/libcrypto.dylib /usr/local/lib/libcrypto.dylib
     $ ln -s /usr/local/opt/openssl/lib/libssl.dylib /usr/local/lib/libssl.dylib
     ```
30. Install libmagic

     `(WeVoteServerPy3.7) $ brew install libmagic`

31. Install all the other Python packages required by the WeVoteServer project (there are a lot of them!)

     `(WeVoteServer3.7) $ pip3 install -r requirements.txt`

     This is a big operation that loads a number of wheels definitions and then compiles them.   Wheels are
     linux/macOS binary libraries based on c language packages and compiled with gcc. 
     Wheels allow python library developers to speed up execution by coding critical or complex sections the c language.
     Interpreted Python code runs slower than compiled c. 

     **Note July 2022 if this fails due to `psycopg2-binary` requiring `pg_config` (which is installed with postgres), install Postgres first then come back and do the pip3 install -r requirements.txt` command.**
    
     If this installation succeeds with no missing libraries, or other compiler errors, we are
     almost done.  If this installation fails, please ask for help.


## Install and set up PostgreSQL and pgAdmin4

1. If you are sure that Postgres has not already been installed, and is not currently running on this Mac, you can skip
this step.  To see if postgres is already running, check with lsof in a terminal window `lsof -i -P | grep -i "listen" | grep postgres`:

    ```
    (venv) $ lsof -i -P | grep -i "listen" | grep postgres
    postgres  13254 admin    5u  IPv6 0x35032d9cf207f247      0t0  TCP localhost:5432 (LISTEN)
    postgres  13254 admin    6u  IPv4 0x35032d9d01cd2647      0t0  TCP localhost:5432 (LISTEN)
    (venv) $
    ```  
 
    If the output shows postgres has already been installed and is listening on port 5432.  Stop and fix this,  
    otherwise you would install a second postgres instance running on port 5433, and the result would be hours of "port 
    assignment" mess to clean up. 
   
    **If that lsof line returns nothing**, then you don't currently have postgres running, and you can continue on to the next step.

    or
   
    **If you don't mind fully deleting any Postgres database data that you have already installed**, then delete the existing Postgres now.  If you installed postgres with homebrew try `brew uninstall postgresql`, 
    but if that fails Postgres can be setup in many ways, so there are no detailed instructions here on how to delete Postgres (but. You can start with running `which postgres`
    in a terminal and going to that directory and deleting the instance or the symbolic links to the instance.  
    Next step is to reboot your Mac to see if Postgres starts up again.

    or

    **If you have to keep some data that is already stored in the Postgres instance on your Mac** that you absolutely need to 
    retain, then you will need to manually upgrade Postgres.  This is a ton of work, and is rarely necessary.
   
3. Install PostgreSQL by running the following command:

    `(venv) $ brew install postgresql`

4. Start PostgreSQL (this is actually instructing the macOS [launchd](https://en.wikipedia.org/wiki/Launchd) to start 
    Postgres every time you start your Mac):

    `(venv) $ brew services start postgresql`

5. Create a default database, and a default user, and then log into the 'psql postgres' PostgreSQL command interpreter ("postgres=#" is the command prompt, you should not have to type this in):

    _New way: November 2021, using Postgres 14.0_
    ```
   (PycharmEnvironments) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 ~ % psql postgres
   psql (14.0)
   Type "help" for help.
   
   postgres=# createdb
   postgres=# createuser -s postgres    (TODO 7/8:  CREATE ROLE postgres WITH SUPERUSER CREATEDB CREATEROLE LOGIN ENCRYPTED PASSWORD ‘stevePG’;
   postgres=# \du
                                        List of roles
      Role name  |                         Attributes                         | Member of 
    -------------+------------------------------------------------------------+-----------
     stevepodell | Superuser, Create role, Create DB, Replication, Bypass RLS | {}
    
   postgres=# create database WeVoteServerDB;
   CREATE DATABASE
   postgres=# grant all privileges on database WeVoteServerDB to postgres;
   GRANT
   postgres=# \l
                                        List of databases
          Name      |    Owner    | Encoding | Collate | Ctype |      Access privileges      
   ----------------+-------------+----------+---------+-------+-----------------------------
     WeVoteServerDB | stevepodell | UTF8     | C       | C     |                   (TODO 7/8/22 these don't match the latest setup) 
     postgres       | stevepodell | UTF8     | C       | C     | 
     template0      | stevepodell | UTF8     | C       | C     | =c/stevepodell             +
                    |             |          |         |       | stevepodell=CTc/stevepodell
     template1      | stevepodell | UTF8     | C       | C     | =c/stevepodell             +
                    |             |          |         |       | stevepodell=CTc/stevepodell
     wevoteserverdb | stevepodell | UTF8     | C       | C     | =Tc/stevepodell            +
                    |             |          |         |       | stevepodell=CTc/stevepodell+
                    |             |          |         |       | postgres=CTc/stevepodell
   (5 rows)
   postgres=#
   ```
   brew created a superuser 'stevepodell' with no password, you can add a password within psql if you wish.

   _old way ..._

    ```   
    (venv) $ createdb
    (venv) $ createuser -s postgres
    (venv) $ psql
    psql (11.1)
    Type "help" for help.
    
    admin=# 
    ```

    The `psql` command starts a PostgresSQL command session which is started in the bash terminal window. Within this 
    PostgresSQL command session type the following Postgres commands... ("admin" is just an example password, use whatever
    password you would like to go with your postgres role name.)

    ```
    admin=# ALTER USER postgres WITH PASSWORD 'admin';
    ALTER ROLE
    admin=# \du
                                       List of roles
     Role name |                         Attributes                         | Member of 
    -----------+------------------------------------------------------------+-----------
     admin     | Superuser, Create role, Create DB, Replication, Bypass RLS | {}
     postgres  | Superuser, Create role, Create DB                          | {}
    
    admin-# \q
    (venv) $
    ```

    That `\du` command confirms that we have a 'postgres' role.  The `\q` command quits psql.

6. Now you are ready to install pgAdmin4 (a powerful WYSIWYG database administration tool that is open source 
 and built by volunteers (Many thanks to the pgAdmin team!)). Run:

   `(venv) $ brew install --cask pgadmin4`
    
   This can take a few minutes to complete.  When `brew install --cask pgadmin4` finishes, it prints out `Moving App 'pgAdmin 4.app' to '/Applications/pgAdmin 4.app'.`

   The latest pgAdmin4 has a webapp architecture (it is not a compiled program).  The app you start from the Application folder is actually a 
   single purpose web server, and the UI for the app appears.  (7/8/22 needs a new )

7. Use Spotlight to find and launch the pgAdmin4 app.  Once launched, the pgAdmin4 webapp will display in a new tab within Chrome.
   On that new tab, click on the "Add new Servers" button and choose "Create > Server"
   
   <img width="800" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/CreateServerInPgAdmin2.png"> 

8. On the first tab of the "Create - Server" dialog, add into the Name field: WeVoteServer

   <img width="500" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/CreateServerDialog.png"> 

9. Switch to "Connection" tab, and enter the following information:
   * Host name: localhost
   * Port: 5432
   * Maintenance database: postgres
   * User name: postgres
   * Password: <your private password for the postgres user>  (mine is stevePG)
   * Save password: checked

    ![ScreenShot](images/CreateServerConnection2.png)

10. Press Save

11. Create the Database by right-clicking on Databases in the server tree on the left. Then select  
    Create > Database on the cascading menu
    <img width="800" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/CreateDatabase.png"> 

12. Name the new database WeVoteServerDB and press save.

    <img width="800" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/NameDatabase.png"> 
   
    <!-- owner is 'admin' in the picture, but defaulted to 'postgres' in my install -->

## Initialize an empty WeVoteServerDB

1. Create an empty log file on your computer to match the one expected by the app as configured in the environment_variables.json file:

    ```
    (venv) $ sudo mkdir /var/log/wevote/
    (venv) $ sudo touch /var/log/wevote/wevoteserver.log
    (venv) $ sudo chmod -R 0777 /var/log/wevote/
    ```

    As configured by default in our configuration code from GitHub, only errors get written to the log.
    Logging has five levels: CRITICAL, ERROR, INFO, WARN, DEBUG.
    It works as a hierarchy (i.e., INFO picks up all messages logged as INFO, ERROR and CRITICAL), and when adding logging 
    code we specify the level assigned to each message. You can change this to info items by changing the LOG_FILE_LEVEL variable 
    in the WeVoteServer/config/environment_variables.json file to "INFO".
    
    **Note:** Logging slows down Python app execution in production, so only use it for very important or very rarely used code or 
    code that is only used by the admin pages by developers.  You can also write your log files at the DEBUG level, and then they
    won't execute on the production server.

1. "Migrations are Django’s way of propagating changes you make to your software models into your local postgres database schema."
   Everytime you create a table, change a field name or description, you are changing the model, and those changes need to 
   be incorporated into the on-disk database schema.

   Run 'makemigrations' to gather all the schema information that is needed to initialize the WeVoteServer database:

    ```
    (venv) $ python manage.py makemigrations
    (venv) $ python manage.py makemigrations wevote_settings
    ```
     (January 28, 2019:  that second makemigrations for the wevote_settings table should not be necessary, but as of today, 
     it is necessary.  That second makemigrations line will be harmless, if it becomes unnecessary at some point.)
   
1. Run 'migrate'.  Django "migrate is responsible for applying and un-applying migrations."

    `(venv) $ python manage.py migrate`
 
## Set up a PyCharm run configuration

1. Set up a run configuration (this will enable the green play button, and the green debug button on the top line)
   
   Click in the "Add Configuration..." field that is to the left of the play button.

   <img src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/transparent8x8.png"> 
   <img width="900" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/InitRunConfiguration.png"> 
   
   Press the '+' sign in the upper-left corner of the dialog.  

   <img width="600" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/RunConfigurationSelectPy.png"> 

   Then select Python, and click 'Add new run configuration...'

   <img width="700" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/RunConfigBlank.png"> 

   For "Script path", add the path 
   to your `manage.py` file that will be in your project root directory, and for "Parameters" add `runserver` as the command.  
   Then press "Ok".
   
   <img width="800" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/RunConfigFilled.png"> 

1.  Run the app:  Press the triangular Run button on the top line of the ide.  Note that a run window opens at the bottom of the IDE,
    on the same line as the "Terminal" tab.
    As API calls arrive at the server, the http requests will be displayed in this runtime log.

    Python print commands, only send their output to this log.  Python logger commands send the output
    to both this runtime log, and the log file that we created a few steps back.  On the production servers in AWS, these 
    log lines can be searched using Splunk (ask Dale for Splunk access if you could use it.)

1.  Now, with the server still running, open a terminal window, and create an account for yourself to login to the 
    management pages of the WeVoteServer.
    
    At WeVote, we call end users "voters".  This new "voter" will have all the 
    rights that you (as a developer) need to log in to 
    [http://localhost:8000/admin/](http://localhost:8000/admin/).  Once logged in you can start synchronizing data (downloading ballot and issue 
    data from the master server in the cloud, to your local server).
    
   The usage is:  `python manage.py create_dev_user first_name last_name email password`

    ```
    (WeVoteServer3.7) admin$ python manage.py create_dev_user Samuel Adams samuel@adams.com ale 
    Creating developer first name=Samuel, last name=Adams, email=samuel@adams.com
    End of create_dev_user
    (WeVoteServer3.7) admin$ 
    ```
    
1.  Navigate to [http://localhost:8000/admin/](http://localhost:8000/admin/) and sign in with your new username/password  (for example mine is stevepodell/stevePG.).    

1.  Your local instance of the WeVoteServer is now setup and running (although there is no election 
    data stored in your Postgres instance, for it to serve to clients at this point).

## Import some ballot data from the live production API Server

   
**This page of instructions has covered steps 1 through 5 of the multi-page instructions, so now you can skip to step 6 to 
load some ballot data.**

Step 6:  [Set up Initial Data](README_API_INSTALL_SETUP_DATA.md)

## Optional:  Running in SSL/https mode

You only need to do this if you are going to be working on Login with Facebook or Stripe Donations

### If you have not created a secure certificate to run WebApp on your Mac in SSL/HTTPS mode, do this first

The following link takes you to a page in the WebApp docs, you will have to manually navigate back here when you are done.

[Installing Secure Certificate](https://github.com/wevote/WebApp/blob/develop/docs/working/SECURE_CERTIFICATE.md)

### Make a small necessary change to your /etc/hosts

Facebook will no longer redirect to localhost and it also won't redirect to a http link, so these changes are necessary.

Make a second alias for 127.0.0.1 with this made up (but standardized for We Vote developers) domain: `wevotedeveloper.com`

Explanation from the python-social-auth docs: "[If you define a redirect URL in Facebook setup page, be sure to not define http://127.0.0.1:8000 or http://localhost:8000 because it won’t work when testing. Instead I define http://wevotedeveloper.com and setup a mapping on /etc/hosts.](https://python-social-auth.readthedocs.io/en/latest/backends/facebook.html)"

First we have to make a small change to /etc/hosts.  This is the before:
```
    (venv2) stevepodell@StevesM1Dec2021 WeVoteServer % cat /etc/hosts
    ##
    # Host Database
    #
    # localhost is used to configure the loopback interface
    # when the system is booting.  Do not change this entry.
    ##
    127.0.0.1       localhost
    255.255.255.255 broadcasthost
    ::1             localhost
    (venv2) stevepodell@StevesM1Dec2021 WeVoteServer % 
```
Add a local domain alias `wevotedeveloper.com` for the [Facebook Valid OAuth Redirect URIs](https://developers.facebook.com/apps/1097389196952441/fb-login/settings/). 
To do this you need to add `wevotedeveloper.com` to your `127.0.0.1` line in /etc/hosts.  After the change:
```
    (venv2) stevepodell@StevesM1Dec2021 WeVoteServer % cat /etc/hosts
    ##
    # Host Database
    #
    # localhost is used to configure the loopback interface
    # when the system is booting.  Do not change this entry.
    ##
    127.0.0.1       localhost wevotedeveloper.com
    255.255.255.255 broadcasthost
    ::1             localhost
    (venv2) stevepodell@StevesM1Dec2021 WeVoteServer % 
```

You will need to elevate your privileges with sudo to make this edit to this linux system file ... ` % sudo vi /etc/hosts` You can do with any other editor that you would prefer, as long as it can be run with sudo.

Note July 2022:  The auto generated certificate that is made by runsslserver generates warnings in browsers (not really a problem),
but may stop the JavaScript builtin fetch() function from completing.  The browser extension has to use fetch.

### Server setup changes
In your environment_variables.json
replace all (6) urls that contain `http://localhost:8000/` (or 8001), with `https://wevotedeveloper.com:8000/`

(Explanation at https://github.com/teddziuba/django-sslserver)

Then start an SSL-enabled debug server:

![ScreenShot](images/RunSslServer.png)
![ScreenShot](images/RunningSslServer.png)

or if you prefer the command line ...

```
  $ python manage.py runsslserver wevotedeveloper.com:8000
```

and access the API Server Python Management app on https://wevotedeveloper.com:8000

The first time you start up the [runsslserver](https://github.com/teddziuba/django-sslserver) the app may take a full minute to respond to the first request.

That's it!

You will also need to have your WebApp running in SSL mode, on https://wevotedeveloper.com:3000

## Fixing "NET::ERR_CERT_COMMON_NAME_INVALID" errors in the DevTools ERROR Console

Find one of those failing links in the Network, and click it, to open in a new tab, then follow the
same procedure that you would follow for any invalid certificate.   The details of how you do this
changes over time, but in general on the chrome error screen that you see, follow the links for
viewing the page anyways.  Once you have done that the problem will go away.


[Back to root README](../README.md)


-----------
     
## June 14, 2021, Changes that were necessary for macOS Big Sur

**This is not list of sequential steps to complete a re-installation.  This list describes a few problems
that occurred, what was done to work around them.**

*  macOS BigSur (11.3.1) was complaining about Python 3.6.1, and the app would not work, so
   I upgraded Python to the latest 3.9.1
   
   <img width="500" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/PythonErrorOnBigSur.png"> 

*  Uninstall Python (which was previously installed with Homebrew)
   ```
   (venv) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 pkgconfig % brew uninstall --ignore-dependencies python3
   ```
   
*  Install the latest Python
    ```
    (venv) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 pkgconfig % brew install python3
   ```
   
*  Brew (re)link the python
    ```
    stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 ~ % brew link python@3.9
    ```

*  Needed link it again to clear warnings about overwriting other links
    ```
    stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 ~ % brew link --overwrite python@3.9
   ```
*  In the PyCharm IDE UI
    1)  Navigate to PyCharm/Preferences/'Project: WeVoteServer'/'Python Interpreter' and press the gear icon and set up
    a path to 3.9
    1) On the 'Python Interpreter' summary pop-up select 'WeVoteServer 3.9' (or the latest version you installed).
       
       <img width="600" src="https://raw.githubusercontent.com/wevote/WeVoteServer/develop/docs/images/PythonInterpretersList2021.png"> 

    1) Open a **new** terminal window in the IDE, and run `python --version` to double-check that it is using Python 3.9

    1) Close the older terminal windows, that will have confused paths to the older python versions.

*  Get the latest requirements.txt from git.

*  Install the latest setuptools
   ```
   (venv) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % pip3 install --upgrade setuptools   
   ```
   
*  Try to install requirements.txt in the Pycharm terminal window
    ```
    (venv) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % pip3 install -r requirements.txt
   ```
   
*  If the installation fails, run brew's doctor
    ```
    (venv) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % brew doctor
   ```
   
*  brew cleanup
    ```
    (venv) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % brew cleanup
   ```
   
*  I had an old String.h first in the path, and causing a `fatal error: 'cstddef' file not found` error in String.h
   ```
    (venv) mv /usr/local/include/String.h /usr/local/include/String.h.saveoff
   ```
   
*  This final installation of requirements.txt worked
    ```
    (venv) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % pip3 install -r requirements.txt
   ```
   
*  If problems appear with the openid package...

    Look in External Libraries/site-packages and use 'pip uninstall' to remove any libraries with 'openid' in their
    name, and then try 'pip3 install -r requirements.txt' to reload openid.

*  'pip3 install -r requirements.txt' does not reload openid, try from the command line

    Try these commands, one at a time, in this order:
    ```
    pip install -e git+git://GitHub.com/necaris/python3-openid.git@master#egg=openid
    pip install -e git+git://GitHub.com/necaris/python3-openid.git@master#egg=python3-openid
    ```
   
-----------
     
## January 27, 2023, Saving of the new "Profile Image" while Testing Facebook Sign in 
In order to speed up signin with facebook, we removed the scaling and saving of the facebook profile image from in-line in 
to having them be executed in parallel so that the sign-in occurs much quicker for the voter.

Gunicorn, the application server that the Python API Server runs in production, does not handle threads well, so instead
we run them in a queue in a seperate process.  We use the AWS SQS queue manager to queue up the processing requests that potentially could be coming in from multiple 
Voters, and execute them in a full image of the WeVote API Server.

In order to run all these AWS features locally on your Mac, do the following:

1) Download the docker CLI from https://docs.docker.com/desktop/install/mac-install/
2) Find the downloaded file, and substitute your Downloads path into following set of commands
   ```
    (venv2) WeVoteServer % sudo hdiutil attach '/Users/stevepodell/Downloads/Docker (1).dmg'
    (venv2) WeVoteServer % sudo /Volumes/Docker/Docker.app/Contents/MacOS/install
    (venv2) WeVoteServer % sudo hdiutil detach /Volumes/Docker
   ```
3) MacOS modal dialog that appears, allow docker to make some symbolic links -- allow this.
4) Once the Docker Desktop starts, and shows as running, typing 'docker -v' at the command line, to confirm that the CLI portion is running
   ```
    (venv2) stevepodell@StevesM1Dec2021 tmp % docker -v
    Docker version 20.10.21, build baeda1f
    (venv2) stevepodell@StevesM1Dec2021 tmp % 
   ```
5) Check to see if awslocal is installed
    ```
   ( venv2) stevepodell@StevesM1Dec2021 WeVoteServer % awslocal --version
    aws-cli/2.9.13 Python/3.9.11 Darwin/22.3.0 exe/x86_64 prompt/off
    (venv2) stevepodell@StevesM1Dec2021 WeVoteServer % 
   ```
6) if aws (awslocal) is not available at the command line, follow instructions at
   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html#getting-started-install-instructions
7) Check to see if you have localstack installed
    ```
    (venv2) stevepodell@StevesM1Dec2021 WeVoteServer % localstack --version
    1.3.1
    (venv2) stevepodell@StevesM1Dec2021 WeVoteServer % 
   ```
8) If you do not already have localstack installed
    ```
    pip install localstack localstack-client awscli-local
    ```
9) Start localstack
   ```
   localstack start -d
   ```
10) Wait for sqs service to launch   
11) Create a sqs queue, and copy the QueueUrl it reports to environment-variables.json
    ```
    awslocal sqs create-queue --queue-name job-queue.fifo --attributes FifoQueue=true,ContentBasedDeduplication=true
    ```
12) Make sure the QueueUrl displayed matches AWS_SQS_WEB_QUEUE_URL in the config file environment-variables.json
    It is likely to look like this...
    ```
    "AWS_SQS_WEB_QUEUE_URL":          "http://localhost:4566/000000000000/job-queue.fifo",
    ```
13) Then start the queue processing code (in a separate python server instance) by opening a terminal window and running
    ```
    python manage.py runsqsworker
    ```
14) You will see logging from the sqs worker in that terminal

Note that if you change any code, that would be needed in the instance of the API Server running under SQS, you will need to
kill the runsqsworker in the terminal window, and restart it.
