[![Coverage Status](https://coveralls.io/repos/wevote/WeVoteServer/badge.svg?branch=master&service=github)](https://coveralls.io/github/wevote/WeVoteServer?branch=master)

# WeVoteServer

This repository includes:  

1) A web app client  
2) API server that powers this client. 

You can see our current wireframe mockup for a San Francisco ballot here:
http://start.wevoteusa.org/

## Join Us
Join our Google Group here to discuss the WeVoteServer application (creating a social ballot):
https://groups.google.com/forum/#!forum/wevoteengineering

You may join our Google Group here for questions about election related data (importing and exporting):
https://groups.google.com/forum/#!forum/electiondata

## 1) We Vote Mobile Application

Front end development of the application.

### Features

* Compilation with webpack
* React and jsx
* react-router
* Stylesheets can be CSS, LESS, SASS, Stylus or mixed
* Embedded resources like images or fonts use DataUrls if appropriate
* A simple flag loads a react component (and dependencies) on demand.
* Development
  * Development server
  * Optionally Hot Module Replacement development server (LiveReload for Stylesheets and React components enabled)
  * Uses SourceUrl for performance, but you may switch to SourceMaps easily
* Production
  * Server example for prerendering for React components
  * Initial data inlined in page
  * Long Term Caching through file hashes enabled
  * Generate separate css file to avoid FOUC
  * Minimized CSS and javascript
* Also supports coffee-script files if you are more a coffee-script person.
* You can also require markdown or text files for your content.

### Local Installation

Install Homebrew for package management:

    http://brew.sh/

Install [node.js](https://nodejs.org) - Make sure you are using NodeJS v4.1.2 or higher.

    brew install node
    brew update

Clone the repo to your local machine.

``` shell
cd WeVoteServer/web_app
npm install
```

### Installation via Vagrant

If you want to run a remote version of this server, install [vagrant](https://vagrantup.com)

``` text
vagrant up
vagrant ssh
cd /vagrant
```

NOTE:  

```
On Windows vagrant up should be run with administrative priviledges (e.g. from an elevated prompt opened via the right click 'Run as administrator' context menu action) to allow 
symlinking. Otherwise the box will fail! The included vagrant.bat handles this automatically. If an ssh executable is not found on the system path, and git is installed, 
vagrant.bat will attempt to fallback to the ssh executable installed with git via the included vagrant-bin/ssh.bat script.
```

### Development server

``` text
# start the webpack-dev-server
cd WeVoteServer/web_app
npm run build:dev
# wait for the first compilation is successful

# In another terminal/console, start the node.js server in development mode
cd WeVoteServer/web_app
npm run start:dev

# open this url in your browser
http://127.0.0.1:9090/
```

The configuration is `webpack-dev-server.config.js`.

It automatically recompiles and refreshes the page when files are changed.

Also check the [webpack-dev-server documentation](http://webpack.github.io/docs/webpack-dev-server.html).


### Hot Module Replacement development server

``` text
# start the webpack-dev-server in HMR mode
npm run hot-dev-server
# wait for the first compilation is successful

# In another terminal/console, start the node.js server in development mode
npm run start:dev

# open this url in your browser
http://127.0.0.1:9090/
```

The configuration is `/web_app/webpack-hot-dev-server.config.js`.

It automatically recompiles when files are changed. When a hot-replacement-enabled file is changed (i. e. stylesheets or React components) the module is hot-replaced. If Hot Replacement is not possible the page is refreshed.

Hot Module Replacement has a performance impact on compilation.


### Production compilation and server

``` text
# build the client bundle and the prerendering bundle
npm run build:prod

# start the node.js server in production mode
npm run start:dev

# open this url in your browser
http://127.0.0.1:9090/
```

The configuration is `/web_app/webpack-production.config.js`.

The server is at `/web_app/lib/server.js`

The production setting builds two configurations: one for the client (`build/public`) and one for the serverside prerendering (`build/prerender`).


### Legacy static assets

Assets in `public` are also served.


### Build visualization

After a production build you may want to visualize your modules and chunks tree.

Use the [analyse tool](http://webpack.github.io/analyse/) with the file at `build/stats.json`.


### Loaders and file types

Many file types are preconfigured, but not every loader is installed. If you get an error like `Cannot find module "xxx-loader"`, you'll need to install the loader with `npm install xxx-loader --save` and restart the compilation.


### Common changes to the configuration

#### Add more entry points

(for a multi page app)

1. Add an entry point to `/web_app/make-webpack-config.js` (`var entry`).
2. Add a new top-level react component in `app` (`xxxRoutes.js`, `xxxStoreDescriptions.js`, `xxxStores.js`).
3. (Optional) Enable `commonsChunk` in `webpack-production.config.js` and add `<script src="COMMONS_URL"></script>` to `app/prerender.html`.
4. Modify the server code to require, serve and prerender the other entry point.
5. Restart compilation.

#### Switch devtool to SourceMaps

Change `devtool` property in `/web_app/webpack-dev-server.config.js` and `/web_app/webpack-hot-dev-server.config.js` to `"source-map"` (better module names) or `"eval-source-map"` (faster compilation).

SourceMaps have a performance impact on compilation.

#### Enable SourceMaps in production

1. Uncomment the `devtool` line in `/web_app/webpack-production.config.js`.
2. Make sure that the folder `/web_app/build/public/debugging` is access controlled, i. e. by password.

SourceMaps have a performance impact on compilation.

SourceMaps contains your un-minimized source code, so you need to restrict access to `build\public\debugging`.

#### Coffeescript

Coffeescript is not installed/enabled by default to not disturb non-coffee developer, but you can install it easily:

1. `npm install coffee-redux-loader --save`
2. In `make-webpack-config.js` add `".coffee"` to the `var extensions = ...` line.


## 2) Python API Server

### Setup - Dependencies

NOTE: We are running Django version 1.8
NOTE: We are running Python version 2.7.6

Once you have cloned this repository to your local machine, set up a virtual environment:

    cd /path_to_dev_environment/WeVoteServer/
    virtualenv venv
    source venv/bin/activate

We recommend running this within your virtual environment:

**NOTE: Before beginning on a Linux environment** 

DO:

    sudo apt-get install python-psycopg2 
    sudo apt-get install python-dev
    pip install psycopg2 

THEN:

    pip install django-toolbelt
    pip install --upgrade pip
    pip install -r requirements.txt


### Setup - Install the Postgres database

#### METHOD 1
For Mac, download the DMG from http://postgresapp.com/

Run this on your command line:

    export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/9.4/bin

Start up the command line for postgres (there is an 'open psql' button/navigation item if you installed postgresapp.
Run these commands:

    create role postgres;
    alter role postgres with login;

#### METHOD 2

Install Postgres:

    $ sudo port install postgresql94
    $ sudo port install postgresql94-server

#### METHOD 3 (linux Ubuntu)

Follow these [instructions](https://help.ubuntu.com/community/PostgreSQL)

#### THEN 

Follow these instructions:

    http://gknauth.blogspot.com/2014/01/postgresql-93-setup-after-initial.html

#### FINALLY

We recommend installing pgAdmin3 as a WYSIWYG database administration tool.
NOTE: You may need to turn off the restriction in "Security & Privacy" on "unidentified developers"
to allow this tool to be installed.
See: http://blog.tcs.de/program-cant-be-opened-because-it-is-from-an-unidentified-developer/

In pgadmin add a server. You can use your sign in name as the server name.


### Setup - Environment Variables Configuration - config/environment_variables.json

WeVoteServer is currently configured (in manage.py) to look for a "config/local.py" file (configured in the
"config/settings.py" file). When we run this on a production server, we will startup with a production settings
file like "production_heroku.py".

Copy "environment_variables-template.json" to "environment_variables.json". You will configure many variables for your
local environment in this file. New variables needed by WeVoteServer will be added to
"environment_variables-template.json" from time to time, so please check for updates by comparing your local version
with the template file.

#### LOG_FILE
Create a file on your computer to match the one expected in the environment_variables.json file:

    sudo mkdir /var/log/wevote/
    sudo touch /var/log/wevote/wevoteserver.log
    sudo chmod -R 0777 /var/log/wevote/

As configured in github, only errors get written to the log.
Logging has five levels: CRITICAL, ERROR, INFO, WARN, DEBUG.
It works as a hierarchy (i.e. INFO picks up all messages logged as INFO, ERROR and CRITICAL), and when logging we
specify the level assigned to each message. You can change this to info items by changing this:

    LOG_FILE_LEVEL = logging.INFO

#### GOOGLE_CIVIC_API_KEY
If you are going to connect to Google Civic API, add your key to this variable.
TODO: Describe the process of getting a Google Civic API Key


### Setup - Database Creation

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

### Setup - Heroku Configuration

We use Heroku for publishing a public version anyone can play with , and you can publish a public version too. Here are the instructions:
https://devcenter.heroku.com/articles/getting-started-with-django

In the config/setting.py file, search for "Heroku". There are comments that tell you which parts of the settings file to comment or uncomment to get a version running on Heroku.

### Test that WeVoteServer is running

Start up the webserver:

    python manage.py runserver

Find documentation for all of the APIs here:

    http://localhost:8000/apis/vi/docs


### Coding Standards

Please use descriptive full word variable names.

* In the lifecycle of most projects, fixing bugs and maintaining current features end up taking 50%+ of total engineering time.
* Our goal is to create a code base that is easy to understand, making fixing bugs and maintaining current features as painless as possible. We will have many engineers working with this code, and we want to be welcoming to engineers who are new to the project.
* Short variable names can often create confusion, where a new engineer needs to spend time figuring out what a short variable name actually means. (Ex/ “per” or “p” instead of “person”.) For this project please use descriptive full word variable names.
* Fellow engineers should be able to zoom around the code and not get stopped with riddles created by short names.
