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

