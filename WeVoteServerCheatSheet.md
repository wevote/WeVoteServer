## A Cheat sheet, containing some commands that might help you out
Feel free to add to this!

####Stopping postgres loaded by brew, and not setup as a daemon
```
(WeVoteServerPy3.7) Steves-MacBook-Pro-32GB-Oct-2018:WeVoteServer stevepodell$ pg_ctl -D /usr/local/var/postgres11.1_1 stop -s -m fast
```

####Starting postgres loaded by brew, and not setup as a daemon
```
(WeVoteServerPy3.7) Steves-MacBook-Pro-32GB-Oct-2018:WeVoteServer stevepodell$ "/Applications/Postgres.app/Contents/Versions/9.6/bin/psql" -p5433 -d "postgres"
or
(WeVoteServerPy3.7) Steves-MacBook-Pro-32GB-Oct-2018:WeVoteServer stevepodell$ pg_ctl -D /usr/local/var/postgres11.1_1 -l logfile start
waiting for server to start.... done
server started
(WeVoteServerPy3.7) Steves-MacBook-Pro-32GB-Oct-2018:WeVoteServer stevepodell$ 
```
####Setting up ngrok to send stripe webhooks to your local python server
```
(WeVoteServerPy3.7) Steves-MacBook-Pro-32GB-Oct-2018:PycharmProjects stevepodell$ ~/PythonProjects/ngrok http 8000 -host-header="localhost:8000"

```

####launching psql and disconnecting all the postgres sessions
```
Last login: Thu Aug  3 09:13:17 on ttys004
Steves-MacBook-Pro-2017:StevesForkOfWebApp stevepodell$ "/Applications/Postgres.app/Contents/Versions/9.6/bin/psql" -p5433 -d "postgres"
psql (9.6.2)
Type "help" for help.

postgres=# SELECT * from pg_database;
    datname     | datdba | encoding | datcollate  |  datctype   | datistemplate | datallowconn | datconnlimit | datlastsysoid | datfrozenxid | datminmxid | dattablespace |               datacl                
----------------+--------+----------+-------------+-------------+---------------+--------------+--------------+---------------+--------------+------------+---------------+-------------------------------------
 postgres       |     10 |        6 | en_US.UTF-8 | en_US.UTF-8 | f             | t            |           -1 |         12668 |          858 |          1 |          1663 | 
 stevepodell    |  16384 |        6 | en_US.UTF-8 | en_US.UTF-8 | f             | t            |           -1 |         12668 |          858 |          1 |          1663 | 
 template1      |     10 |        6 | en_US.UTF-8 | en_US.UTF-8 | t             | t            |           -1 |         12668 |          858 |          1 |          1663 | {=c/postgres,postgres=CTc/postgres}
 template0      |     10 |        6 | en_US.UTF-8 | en_US.UTF-8 | t             | f            |           -1 |         12668 |          858 |          1 |          1663 | {=c/postgres,postgres=CTc/postgres}
 WeVoteServerDB |     10 |        6 | en_US.UTF-8 | en_US.UTF-8 | f             | t            |           -1 |         12668 |          858 |          1 |          1663 | 
(5 rows)

postgres=# SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'WeVoteServerDB';
 pg_terminate_backend 
----------------------
 t
 t
 t
 t
 t
 t
(6 rows)

postgres=#
```
(You may have to quit out of this session to do the next step, ^D)

####Dropping the database (all data will be destroyed)
You have to terminate all the backend connections before this will work:

Then in pgAdmin 4,
1) Select the WeVoteServerDB and right-click and drop
2) Then select Databases and right-click create ‘WeVoteServerDB’
3) Then in Terminal, recreate the database (it will be empty)
```
(WeVoteServer3.6) Steves-MacBook-Pro-2017:WeVoteServer stevepodell$ python manage.py migrate
```
####Nasty upgrade to postgres 12.2 (I did not attempt save the existing db on my local)
There has to be a better way to do this, but this is what I went through...
```
  165  brew install postgresql
  173  ls -la  /usr/local/Cellar/postgresql/12.2/bin/pg_ctl
  178  brew services start postgresql
  179  brew services restart postgresql
  184  lsof -i -P | grep -i "listen" | grep postgres
  189  brew services list
  190  ps aux | grep /usr/local/var/postgresl
  198  ls /usr/local/var/log/postgres.log
  199  tail /usr/local/var/log/postgres.log
  200  ls /usr/local/var/postgres
  205  cd /usr/local/var
  207  sudo mkdir postgres
  212  sudo chown stevepodell:admin postgres
  213  ls -la
  217  psql -l
  218  postgres --version
  219  initdb /usr/local/var/postgres
```    (WeVoteServerPy3.7) stevepodell@Steves-MacBook-Pro-32GB-Oct-2018 var % !215                          
    pg_ctl -D /usr/local/var/postgres -l /usr/local/var/postgres/server.log start
    pg_ctl: another server might be running; trying to start server anyway
    waiting for server to start.... stopped waiting
    pg_ctl: could not start server
    Examine the log output.
    (WeVoteServerPy3.7) stevepodell@Steves-MacBook-Pro-32GB-Oct-2018 var % tail /usr/local/var/postgres/server.log
    2020-04-03 21:34:14.414 PDT [13229] FATAL:  lock file "postmaster.pid" already exists
    2020-04-03 21:34:14.414 PDT [13229] HINT:  Is another postmaster (PID 13133) running in data directory "/usr/local/var/postgres"?
    (WeVoteServerPy3.7) stevepodell@Steves-MacBook-Pro-32GB-Oct-2018 var % !lsof
    lsof -i -P | grep post
    postgres  13133 stevepodell    5u  IPv6 0x9139afcc2c95ec77      0t0  TCP localhost:5432 (LISTEN)
    postgres  13133 stevepodell    6u  IPv4 0x9139afcc08c6d697      0t0  TCP localhost:5432 (LISTEN)
    postgres  13133 stevepodell   10u  IPv6 0x9139afcc016b2ecf      0t0  UDP localhost:57308->localhost:57308
    postgres  13135 stevepodell   10u  IPv6 0x9139afcc016b2ecf      0t0  UDP localhost:57308->localhost:57308
    postgres  13136 stevepodell   10u  IPv6 0x9139afcc016b2ecf      0t0  UDP localhost:57308->localhost:57308
    postgres  13137 stevepodell   10u  IPv6 0x9139afcc016b2ecf      0t0  UDP localhost:57308->localhost:57308
    postgres  13138 stevepodell   10u  IPv6 0x9139afcc016b2ecf      0t0  UDP localhost:57308->localhost:57308
    postgres  13139 stevepodell   10u  IPv6 0x9139afcc016b2ecf      0t0  UDP localhost:57308->localhost:57308
    postgres  13140 stevepodell   10u  IPv6 0x9139afcc016b2ecf      0t0  UDP localhost:57308->localhost:57308
    (WeVoteServerPy3.7) stevepodell@Steves-MacBook-Pro-32GB-Oct-2018 var % 
```
#### Adding a new "app" (directory of Python classes) to the WeVoteServer

For example to add the apple "app" at WeVoteServer/apple
1) Make the subdirectory, and copy or create preliminary files in the directory
2) Make sure that there is __init__.py, it can be completely empty. In this example it would be at WeVoteServer/apple/__init__.py
3) Assuming that the "app" has a database table, create the column layout in the models file in a class that extends "models.Model"
We have dozens of Manager files and dozens of Model files that have classes that unnecessarily 
extend 'model.Models' and for each of these classes Django's ORM creates a useless empty table with
just an id field.  Consider extending 'models.Manager' or in almost all cases the class can be defined without
extending anything... 'class ClassName:'
4) Add your new app to the list in INSTALLED_APPS (within WeVoteServer/config/base.py)
5) Generate the Migrations directory for your app, (in this example it is at WeVoteServer/apple/migrations) by typing in a terminal window ... (substitue your app name for apple!)
    ```
     python manage.py makemigrations apple
    ```
6) And finally, update the local database with your new table by typing
    ```
    python manage.py migrate
    ```
-----------
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var % brew info postgresql
    postgresql: stable 12.3 (bottled), HEAD
    Object-relational database system
    https://www.postgresql.org/
    /usr/local/Cellar/postgresql/12.3_2 (3,220 files, 37.8MB) *
      Poured from bottle on 2020-05-25 at 16:48:04
    From: https://github.com/Homebrew/homebrew-core/blob/master/Formula/postgresql.rb
    ==> Dependencies
    Build: pkg-config ✔
    Required: icu4c ✔, krb5 ✔, openssl@1.1 ✔, readline ✔
    ==> Options
    --HEAD
            Install HEAD version
    ==> Caveats
    To migrate existing data from a previous major version of PostgreSQL run:
      brew postgresql-upgrade-database
    
    To have launchd start postgresql now and restart at login:
      brew services start postgresql
    Or, if you don't want/need a background service you can just run:
      pg_ctl -D /usr/local/var/postgres start
    ==> Analytics
    install: 158,231 (30 days), 478,530 (90 days), 1,202,071 (365 days)
    install-on-request: 152,427 (30 days), 458,235 (90 days), 1,127,160 (365 days)
    build-error: 0 (30 days)
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var % 

    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var % brew switch postgresql 12.3_2
    Cleaning /usr/local/Cellar/postgresql/12.3_2
    392 links created for /usr/local/Cellar/postgresql/12.3_2
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var % 


----

    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var-9.6 % echo 'export PATH="/usr/local/opt/icu4c/bin:$PATH"' >> ~/.zshrc
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var-9.6 % echo 'export PATH="/usr/local/opt/icu4c/sbin:$PATH"' >> ~/.zshrc
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var-9.6 % brew install node                                               
    Warning: node 14.4.0 is already installed, it's just not linked
    You can use `brew link node` to link this version.
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var-9.6 % brew link node
    Linking /usr/local/Cellar/node/14.4.0... 
    Error: Could not symlink bin/node
    Target /usr/local/bin/node
    already exists. You may want to remove it:
      rm '/usr/local/bin/node'
    
    To force the link and overwrite all conflicting files:
      brew link --overwrite node
    
    To list all files that would be deleted:
      brew link --overwrite --dry-run node
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var-9.6 % brew link --overwrite node
    Linking /usr/local/Cellar/node/14.4.0... 33 symlinks created
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var-9.6 % 
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var-9.6 %  export LDFLAGS="-L/usr/local/opt/icu4c/lib"
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var-9.6 % export CPPFLAGS="-I/usr/local/opt/icu4c/include"
    export PKG_CONFIG_PATH="/usr/local/opt/icu4c/lib/pkgconfig"
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var-9.6 % /usr/local/Cellar/postgresql/12.3_2/bin/postgres "-D" "/usr/local/var/postgres"
    dyld: Library not loaded: /usr/local/opt/icu4c/lib/libicui18n.66.dylib
      Referenced from: /usr/local/Cellar/postgresql/12.3_2/bin/postgres
      Reason: image not found
    zsh: abort      /usr/local/Cellar/postgresql/12.3_2/bin/postgres "-D" 
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 var-9.6 % 


  300  ls -la /usr/local/Homebrew/Library/Taps/homebrew/homebrew-core/Formula/ic*
  301  cd /usr/local/Homebrew/Library/Taps/homebrew/homebrew-core/Formula/
  302  git log --follow icu4c.rb
  303  git checkout -b icu4c-66  22fb699a417093cd1440857134c530f1e3794f7d
  304  brew reinstall ./icu4c.rb
  305  brew switch icu4c 66.1
  306  ls -la /usr/local/Homebrew/Library/Taps/homebrew/homhistory

-----
The next day

    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % node -v
    dyld: Library not loaded: /usr/local/opt/icu4c/lib/libicui18n.67.dylib
      Referenced from: /usr/local/bin/node
      Reason: image not found
    zsh: abort      node -v
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % 
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % which node
    /usr/local/bin/node
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % 

-----

    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % node -v
    dyld: Library not loaded: /usr/local/opt/icu4c/lib/libicui18n.67.dylib
      Referenced from: /usr/local/bin/node
      Reason: image not found
    zsh: abort      node -v
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % which node
    /usr/local/bin/node
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % homebrew uninstall node
    zsh: command not found: homebrew
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % brew uninstall node 
    Error: Refusing to uninstall /usr/local/Cellar/node/14.4.0
    because it is required by yarn, which is currently installed.
    You can override this and force removal with:
      brew uninstall --ignore-dependencies node
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % brew uninstall --ignore-dependencies node
    Uninstalling /usr/local/Cellar/node/14.4.0... (4,659 files, 60.8MB)
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % node 
    zsh: command not found: node
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % brew install node                      
    Updating Homebrew...
    ==> Auto-updated Homebrew!
    Updated 2 taps (homebrew/core and homebrew/cask).
    ==> New Formulae
    mandown                                                                                                                                pandoc-include-code
    ==> Updated Formulae
    gradle ✔                   aws-sdk-cpp                cheat                      ettercap                   git-delta                  gtkmm3                     kubectx                    nauty                      pqiv                       teleport
    hbase ✔                    awscli                     clutter-gtk                evince                     gitg                       gtksourceview3             kubeless                   netdata                    predictionio               tepl
    openjdk ✔                  awscli@1                   conan                      exiv2                      gitlab-runner              gtksourceview4             kumactl                    netlify-cli                prefixsuffix               terragrunt
    abcmidi                    babel                      curl                       exploitdb                  glade                      gtksourceviewmm3           kustomize                  ngt                        proj                       topgrade
    ace                        balena-cli                 curl-openssl               faudio                     gleam                      gtkspell3                  lcm                        node                       pwntools                   vala
    ack                        baobab                     devspace                   fceux                      gnome-latex                gtranslator                libchamplain               node@12                    qalculate-gtk              vim
    afl-fuzz                   bazel                      diamond                    fdupes                     gnome-recipes              gucharmap                  libdazzle                  nushell                    re2                        vte3
    aliyun-cli                 bit                        digdag                     file-roller                gnumeric                   gupnp-tools                libgweather                okteto                     semgrep                    yaegi
    amtk                       bmake                      django-completion          gatsby-cli                 gobby                      homebank                   libpeas                    opentsdb                   simple-scan
    angular-cli                borgmatic                  docfx                      gdcm                       goffice                    inxi                       lxc                        orientdb                   siril
    anjuta                     broot                      docker-compose             gdl                        grafana                    jenkins                    maxwell                    osm-gps-map                spice-gtk
    arduino-cli                caddy                      docker-compose-completion  gedit                      gsmartcontrol              kamel                      meilisearch                osmosis                    sqlmap
    atlassian-cli              cargo-c                    dvc                        geeqie                     gspell                     kcptun                     mlpack                     pdfpc                      step
    aws-cdk                    cartridge-cli              dynare                     ghex                       gtk+3                      klavaro                    mmark                      pdftk-java                 swi-prolog
    aws-iam-authenticator      cbmc                       easy-tag                   ginac                      gtk-mac-integration        komposition                nailgun                    phpstan                    telegraf
    ==> Deleted Formulae
    lumo                                                                                                                                   unravel
    ==> Updated Casks
    anydo                 clipgrab              feed-the-beast        grandtotal            ledger-live           meshlab               pagico                rubitrack-pro         sketch                tagspaces             tuple                 wrike
    avocode               cloudapp              firefox               hey                   lehreroffice          microsoft-edge        polymail              sensei                slack                 tencent-meeting       vimr                  zalo
    baidunetdisk          customshortcuts       flipper               icq                   loaf                  middle                preform               serial                snagit                thunderbird           wechatwork            zappy
    bitwarden             dosbox-x              fsnotes               iglance               local                 mmex                  quickkeyextension     shift                 soundsource           timing                winclone              zoho-docs
    blitz                 dynobase              garagebuy             iriunwebcam           loom                  mountain-duck         rectangle             shutter-encoder       splashtop-business    tinkerwell            wireshark             zoom-for-it-admins
    blizz                 electerm              gloomhaven-helper     kite                  macupdater            nordvpn-teams         responsively          simply-fortran        sqleditor             tinymediamanager      wireshark-chmodbpf
    breaktimer            elpass                glyphs                kiwi-for-g-suite      macx-dvd-ripper-pro   obyte                 ring                  sipgate-softphone     stats                 tor-browser           workflowy
    busycal               energia               gpxsee                kui                   memory                ocenaudio             rsyncosx              sizzy                 stoplight-studio      trojan-qt5            wormhole
    
    ==> Downloading https://homebrew.bintray.com/bottles/icu4c-67.1.catalina.bottle.tar.gz
    Already downloaded: /Users/stevepodell/Library/Caches/Homebrew/downloads/e045a709e2e21df31e66144a637f0c77dfc154f60183c89e6b04afa2fbda28ba--icu4c-67.1.catalina.bottle.tar.gz
    ==> Downloading https://homebrew.bintray.com/bottles/node-14.5.0.catalina.bottle.tar.gz
    ==> Downloading from https://akamai.bintray.com/91/91096144949902e76d46a3c0cfa26f5f55665da838f77ac96c58c416940d28d0?__gda__=exp=1593646104~hmac=ff39acf4c27ac2382867802d13d4754806aff1d7b1046ee26ae6aa811064d94a&response-content-disposition=attachment%3Bfilename%3D%22nod
    ######################################################################## 100.0%
    ==> Installing dependencies for node: icu4c
    ==> Installing node dependency: icu4c
    ==> Pouring icu4c-67.1.catalina.bottle.tar.gz
    ==> Caveats
    icu4c is keg-only, which means it was not symlinked into /usr/local,
    because macOS provides libicucore.dylib (but nothing else).
    
    If you need to have icu4c first in your PATH run:
      echo 'export PATH="/usr/local/opt/icu4c/bin:$PATH"' >> ~/.zshrc
      echo 'export PATH="/usr/local/opt/icu4c/sbin:$PATH"' >> ~/.zshrc
    
    For compilers to find icu4c you may need to set:
      export LDFLAGS="-L/usr/local/opt/icu4c/lib"
      export CPPFLAGS="-I/usr/local/opt/icu4c/include"
    
    For pkg-config to find icu4c you may need to set:
      export PKG_CONFIG_PATH="/usr/local/opt/icu4c/lib/pkgconfig"
    
    ==> Summary
    🍺  /usr/local/Cellar/icu4c/67.1: 258 files, 71.2MB
    ==> Installing node
    ==> Pouring node-14.5.0.catalina.bottle.tar.gz
    Warning: The post-install step did not complete successfully
    You can try again using `brew postinstall node`
    ==> Caveats
    Bash completion has been installed to:
      /usr/local/etc/bash_completion.d
    ==> Summary
    🍺  /usr/local/Cellar/node/14.5.0: 4,659 files, 61.0MB
    Removing: /Users/stevepodell/Library/Caches/Homebrew/node--14.4.0.catalina.bottle.tar.gz... (16.3MB)
    ==> Caveats
    ==> icu4c
    icu4c is keg-only, which means it was not symlinked into /usr/local,
    because macOS provides libicucore.dylib (but nothing else).
    
    If you need to have icu4c first in your PATH run:
      echo 'export PATH="/usr/local/opt/icu4c/bin:$PATH"' >> ~/.zshrc
      echo 'export PATH="/usr/local/opt/icu4c/sbin:$PATH"' >> ~/.zshrc
    
    For compilers to find icu4c you may need to set:
      export LDFLAGS="-L/usr/local/opt/icu4c/lib"
      export CPPFLAGS="-I/usr/local/opt/icu4c/include"
    
    For pkg-config to find icu4c you may need to set:
      export PKG_CONFIG_PATH="/usr/local/opt/icu4c/lib/pkgconfig"
    
    ==> node
    Bash completion has been installed to:
      /usr/local/etc/bash_completion.d
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % 
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % echo $PATH
    /Users/stevepodell/PycharmEnvironments/WeVoteServerPy3.7.2/bin:/usr/local/opt/icu4c/sbin:/usr/local/opt/icu4c/bin:/usr/local/opt/ruby/bin:/Users/stevepodell/.gvm/vertx/current/bin:/Users/stevepodell/.gvm/springboot/current/bin:/Users/stevepodell/.gvm/lazybones/current/bin:/Users/stevepodell/.gvm/jbake/current/bin:/Users/stevepodell/.gvm/groovyserv/current/bin:/Users/stevepodell/.gvm/groovy/current/bin:/Users/stevepodell/.gvm/griffon/current/bin:/Users/stevepodell/.gvm/grails/current/bin:/Users/stevepodell/.gvm/gradle/current/bin:/Users/stevepodell/.gvm/glide/current/bin:/Users/stevepodell/.gvm/gaiden/current/bin:/Users/stevepodell/.gvm/crash/current/bin:/opt/local/bin:/opt/local/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Library/Apple/usr/bin:/usr/local/git/bin:/usr/local/opt/ruby/bin:/Users/stevepodell/.gvm/vertx/current/bin:/Users/stevepodell/.gvm/springboot/current/bin:/Users/stevepodell/.gvm/lazybones/current/bin:/Users/stevepodell/.gvm/jbake/current/bin:/Users/stevepodell/.gvm/groovyserv/current/bin:/Users/stevepodell/.gvm/groovy/current/bin:/Users/stevepodell/.gvm/griffon/current/bin:/Users/stevepodell/.gvm/grails/current/bin:/Users/stevepodell/.gvm/gradle/current/bin:/Users/stevepodell/.gvm/glide/current/bin:/Users/stevepodell/.gvm/gaiden/current/bin:/Users/stevepodell/.gvm/crash/current/bin:/opt/local/bin:/opt/local/sbin
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % 
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % node -v
    v14.5.0
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 jwt % 

---
    stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 build % npm rebuild node-sass  
    stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 build % 

--- 
### 7/10/20 After a reboot
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % pg_ctl -D /usr/local/var/postgres -l /usr/local/var/postgres/server.log start
    dyld: Library not loaded: /usr/local/opt/icu4c/lib/libicui18n.66.dylib
      Referenced from: /usr/local/Cellar/postgresql/12.3_2/bin/postgres
      Reason: image not found
    no data was returned by command ""/usr/local/Cellar/postgresql/12.3_2/bin/postgres" -V"
    The program "postgres" is needed by pg_ctl but was not found in the
    same directory as "/usr/local/Cellar/postgresql/12.3_2/bin/pg_ctl".
    Check your installation.
    (WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % 




------
(WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % brew services start postgresql
Service `postgresql` already started, use `brew services restart postgresql` to restart.
(WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % brew services restart postgresql
Stopping `postgresql`... (might take a while)
==> Successfully stopped `postgresql` (label: homebrew.mxcl.postgresql)
==> Successfully started `postgresql` (label: homebrew.mxcl.postgresql)
(WeVoteServerPy3.7.2) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % ps -aux

----------

(WeVoteServerPy3.8) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % python manage.py sqlmigrate apple 0001_initial   
Running
BEGIN;
--
-- Create model AppleUser
--
CREATE TABLE "apple_appleuser" ("id" serial NOT NULL PRIMARY KEY, "voter_device_id" varchar(255) NOT NULL, "voter_we_vote_id" varchar(255) NOT NULL, "user_code" varchar(255) NOT NULL, "email" varchar(255) NULL, "first_name" varchar(255) NULL, "middle_name" varchar(255) NULL, "last_name" varchar(255) NULL, "apple_platform" varchar(32) NULL, "apple_os_version" varchar(32) NULL, "apple_model" varchar(32) NULL, "date_created" timestamp with time zone NOT NULL, "date_last_referenced" timestamp with time zone NOT NULL);
COMMIT;
(WeVoteServerPy3.8) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer %

----------
(WeVoteServerPy3.8) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % ./ngrok http https://localhost:8000 -host-header="localhost:8000" 

Certificate side at https://developer.apple.com/account/resources/identifiers/serviceId/edit/558W8996A7

https://2e17b805919a.ngrok.io/apis/v1/

./ngrok http http://localhost:8000 -host-header="localhost:8000" 

https://9f876040d5c8.ngrok.io/apis/v1/appleSignInOauthRedirectDestination

Django runs http.  Redirect locally to http, not to https.
./ngrok http http://localhost:8000 -host-header="localhost:8000" 

'{"name":{"firstName":"Steve","lastName":"Podell"},"email":"stevepodell@yahoo.com"}'