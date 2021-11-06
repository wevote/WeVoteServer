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
in a later setup (2021)
```
(PycharmEnvironments) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % postgres --version
postgres (PostgreSQL) 14.0
(PycharmEnvironments) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % psql --version
psql (PostgreSQL) 14.0
(PycharmEnvironments) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % 
```

#### Setting up ngrok to send stripe webhooks to your local python server
```
(WeVoteServerPy3.7) Steves-MacBook-Pro-32GB-Oct-2018:PycharmProjects stevepodell$ ~/PythonProjects/ngrok http 8000 -host-header="localhost:8000"

```
A very useful http inspector is made available by ngrok at [http://127.0.0.1:4040/inspect/http](http://127.0.0.1:4040/inspect/http)

Then go to the Stripe console, and 

#### launching psql and disconnecting all the postgres sessions
```
(PycharmEnvironments) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 WeVoteServer % psql
psql (12.3)
Type "help" for help.

stevepodell=# SELECT * from pg_database;
  oid  |    datname     | datdba | encoding | datcollate |  datctype   | datistemplate | datallowconn | datconnlimit | datlastsysoid | datfrozenxid | datminmxid | dattablespace |                    datacl                    
-------+----------------+--------+----------+------------+-------------+---------------+--------------+--------------+---------------+--------------+------------+---------------+----------------------------------------------
 13690 | postgres       |     10 |        6 | C          | en_US.UTF-8 | f             | t            |           -1 |         13689 |          479 |          1 |          1663 | 
 16384 | stevepodell    |     10 |        6 | C          | en_US.UTF-8 | f             | t            |           -1 |         13689 |          479 |          1 |          1663 | 
     1 | template1      |     10 |        6 | C          | en_US.UTF-8 | t             | t            |           -1 |         13689 |          479 |          1 |          1663 | {=c/stevepodell,stevepodell=CTc/stevepodell}
 13689 | template0      |     10 |        6 | C          | en_US.UTF-8 | t             | f            |           -1 |         13689 |          479 |          1 |          1663 | {=c/stevepodell,stevepodell=CTc/stevepodell}
 94769 | WeVoteServerDB |  16385 |        6 | C          | en_US.UTF-8 | f             | t            |           -1 |         13689 |          479 |          1 |          1663 | 
(5 rows)

stevepodell=# SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'WeVoteServerDB';
 pg_terminate_backend 
----------------------
 t
 t
 t
 t
 t
 t
 t
(7 rows)

stevepodell=# 

```
(You may have to quit out of this session to do the next step, ^D)

#### Dropping the database (all data will be destroyed)
You have to terminate all the backend connections before this will work:

Then in pgAdmin 4,
1) Select the WeVoteServerDB and right-click and drop
2) Then select Databases and right-click create ‘WeVoteServerDB’
3) Then in Terminal, recreate the database (it will be empty)
```
(WeVoteServer3.6) Steves-MacBook-Pro-2017:WeVoteServer stevepodell$ python manage.py migrate
```
#### Nasty upgrade to postgres 12.2 (I did not attempt save the existing db on my local)
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
```    
```    
    (WeVoteServerPy3.7) stevepodell@Steves-MacBook-Pro-32GB-Oct-2018 var % !215                          
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
