# Working with WeVoteServer

## Staying Synchronized with Latest Code

If you are returning to work on WeVoteServer after a few weeks or months, these are the steps:

Pull the latest code from the repository. Then:

    $ cd /Users/<YOUR NAME HERE>/PythonProjects/WeVoteServer/
    $ source /Users/<YOUR NAME HERE>/PythonEnvironments/WeVoteServer3.4/bin/activate
    $ pip install -r requirements.txt
    $ python manage.py makemigrations
    $ python manage.py migrate
    
Compare your local version of "config/environment_variables.json" with the master template version 
"[config/environment_variables-template.json](config/environment_variables-template.json)" and add or remove entries.

## Daily Commands

### API Endpoints - Start up the Django server

Here are some commands we use quite a lot:

    $ cd /Users/<YOUR NAME HERE>/PythonProjects/WeVoteServer/
    $ source /Users/<YOUR NAME HERE>/PythonEnvironments/WeVoteServer3.4/bin/activate
    $ python manage.py runserver

Find API admin tools here [http://localhost:8000/admin](http://localhost:8000/admin)

Find documentation for all of the APIs here [http://localhost:8000/apis/v1/docs](http://localhost:8000/apis/v1/docs)

### Test Data

In order to effectively work with WeVoteServer, you will need election data. We have made it easy to set up your 
database with initial data that will help you do development. Visit the Admin Menu 
[http://localhost:8000/admin](http://localhost:8000/admin) on your local machine and click the
"Import Test Data" link. The first time this runs, it can take 60-120 seconds.

### Web App - Startup the Web App servers

Open a new terminal/console, and do the following:

    cd /Users/<YOUR NAME HERE>/PythonProjects/WeVoteServer/web_app
    npm run build:dev

Wait for the first compilation is successful, then in another terminal/console, start the 
node.js server in development mode.

    cd /Users/<YOUR NAME HERE>/PythonProjects/WeVoteServer/web_app
    npm run start:dev

Visit the Web App in a browser
[http://127.0.0.1:9090/](http://127.0.0.1:9090/) or [http://localhost:9090/](http://localhost:9090/)

## Coding Standards

Please use descriptive full word variable names.

* In the lifecycle of most projects, fixing bugs and maintaining current features end up taking 
50%+ of total engineering time.
* Our goal is to create a code base that is easy to understand, making fixing bugs and maintaining 
current features as painless as possible. We will have many engineers working with this code, 
and we want to be welcoming to engineers who are new to the project.
* Short variable names can often create confusion, where a new engineer needs to spend time 
figuring out what a short variable name actually means. (Ex/ “per” or “p” instead of “person”.) 
For this project please use descriptive full word variable names.
* Fellow engineers should be able to zoom around the code and not get stopped with riddles created by short names.

## Checking In Code - Please Run Tests

Before checking in your code:

Request access to the We Vote team so you can check in code. Email: Dale.McGrew@WeVoteUSA.org

Please make sure to run our tests before checking in any code (Still not working in Python3 yet):

    source venv/bin/activate
    cd WeVoteServer
    python manage.py test
