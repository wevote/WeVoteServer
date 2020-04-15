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

-----------------

(WeVoteServerPy3.7) stevepodell@Steves-MacBook-Pro-32GB-Oct-2018 var % /usr/local/Cellar/postgresql/12.2/bin/pg_ctl -D /usr/local/var/postgres -l logfile start
pg_ctl: another server might be running; trying to start server anyway
waiting for server to start..../bin/sh: logfile: Permission denied
 stopped waiting
pg_ctl: could not start server
Examine the log output.
(WeVoteServerPy3.7) stevepodell@Steves-MacBook-Pro-32GB-Oct-2018 var % tail  /usr/local/var/log/postgres.log 
2020-04-04 09:21:51.288 PDT [1135] LOG:  starting PostgreSQL 12.2 on x86_64-apple-darwin19.3.0, compiled by Apple clang version 11.0.0 (clang-1100.0.33.17), 64-bit
2020-04-04 09:21:51.289 PDT [1135] LOG:  listening on IPv6 address "::1", port 5432
2020-04-04 09:21:51.289 PDT [1135] LOG:  listening on IPv4 address "127.0.0.1", port 5432
2020-04-04 09:21:51.290 PDT [1135] LOG:  listening on Unix socket "/tmp/.s.PGSQL.5432"
2020-04-04 09:21:51.305 PDT [1204] LOG:  database system was interrupted; last known up at 2020-04-03 21:35:28 PDT
2020-04-04 09:21:52.069 PDT [1204] LOG:  database system was not properly shut down; automatic recovery in progress
2020-04-04 09:21:52.077 PDT [1204] LOG:  redo starts at 0/166B300
2020-04-04 09:21:52.077 PDT [1204] LOG:  invalid record length at 0/166B3E8: wanted 24, got 0
2020-04-04 09:21:52.077 PDT [1204] LOG:  redo done at 0/166B3B0
2020-04-04 09:21:52.091 PDT [1135] LOG:  database system is ready to accept connections
(WeVoteServerPy3.7) stevepodell@Steves-MacBook-Pro-32GB-Oct-2018 var % 

pgadmin4 localhost/5432   postgres/postgres
```