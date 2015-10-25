# README for Web App Installation
[Back to root README](README.md)

## Features

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

## Local Installation Instructions

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

## Installation via Vagrant

If you want to run a remote version of this server, install [vagrant](https://vagrantup.com)

``` text
vagrant up
vagrant ssh
cd /vagrant
```

NOTE:  

```
On Windows vagrant up should be run with administrative priviledges (e.g. from an elevated prompt opened via the 
right click 'Run as administrator' context menu action) to allow symlinking. Otherwise the box will fail! 
The included vagrant.bat handles this automatically. If an ssh executable is not found on the system path, 
and git is installed, vagrant.bat will attempt to fallback to the ssh executable installed with git 
via the included vagrant-bin/ssh.bat script.
```

## Development server

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


## Hot Module Replacement development server

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

It automatically recompiles when files are changed. When a hot-replacement-enabled file is changed 
(i. e. stylesheets or React components) the module is hot-replaced. If Hot Replacement is 
not possible the page is refreshed.

Hot Module Replacement has a performance impact on compilation.


## Production compilation and server

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

The production setting builds two configurations: one for the client (`build/public`) and 
one for the serverside prerendering (`build/prerender`).


## Legacy static assets

Assets in `public` are also served.


## Build visualization

After a production build you may want to visualize your modules and chunks tree.

Use the [analyse tool](http://webpack.github.io/analyse/) with the file at `build/stats.json`.


## Loaders and file types

Many file types are preconfigured, but not every loader is installed. If you get an error like 
`Cannot find module "xxx-loader"`, you'll need to install the loader with `npm install xxx-loader --save` and 
restart the compilation.


## Common changes to the configuration

### Add more entry points

(for a multi page app)

1. Add an entry point to `/web_app/make-webpack-config.js` (`var entry`).
2. Add a new top-level react component in `app` (`xxxRoutes.js`, `xxxStoreDescriptions.js`, `xxxStores.js`).
3. (Optional) Enable `commonsChunk` in `webpack-production.config.js` and add `<script src="COMMONS_URL"></script>` 
to `app/prerender.html`.
4. Modify the server code to require, serve and prerender the other entry point.
5. Restart compilation.

### Switch devtool to SourceMaps

Change `devtool` property in `/web_app/webpack-dev-server.config.js` and `/web_app/webpack-hot-dev-server.config.js` 
to `"source-map"` (better module names) or `"eval-source-map"` (faster compilation).

SourceMaps have a performance impact on compilation.

### Enable SourceMaps in production

1. Uncomment the `devtool` line in `/web_app/webpack-production.config.js`.
2. Make sure that the folder `/web_app/build/public/debugging` is access controlled, i. e. by password.

SourceMaps have a performance impact on compilation.

SourceMaps contains your un-minimized source code, so you need to restrict access to `build\public\debugging`.

[Back to root README](README.md)
