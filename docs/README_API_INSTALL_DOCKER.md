# README for Installation with Docker
[Back to root README](../README.md)

Only [Docker Desktop](https://docs.docker.com/get-docker/) is required.

[WSL 2](https://learn.microsoft.com/en-us/windows/wsl/compare-versions#comparing-wsl-1-and-wsl-2) users should follow [this guide](https://docs.docker.com/desktop/wsl/) as well.

## Installation

1. Clone your WeVoteServer fork

    ```
    git clone https://github.com/wevote/WeVoteServer.git
    cd WeVoteServer
    ```

2. Set environment variables in `.env`

    ```
    # read/write database settings
    DATABASE_PASSWORD="secret"
    DATABASE_HOST="host.docker.internal"   

    # read-only database settings
    DATABASE_PASSWORD_READONLY="secret"
    DATABASE_HOST_READONLY="host.docker.internal"   

    # analytics database settings
    DATABASE_PASSWORD_ANALYTICS="secret"
    DATABASE_HOST_ANALYTICS="host.docker.internal"   

    # api
    DJANGO_SUPERUSER_EMAIL="dev@test.com"
    DJANGO_SUPERUSER_PASSWORD="secret"

    # db
    POSTGRES_PASSWORD="secret" 
    ```

3. Configure PostgreSQL in `config.sql` by creating a config file in the root directory (WeVoteServer)

    ```sql
    ALTER SYSTEM SET listen_addresses = '*';
    ```
    This setting allows other containers to access the database

4. [Open the following ports](https://www.wikihow.com/Open-Ports), if they are not already open:

    - 4566 to access AWS
    
    - 5432 to access the database

    - 8000 to access the API

5. Create and start containers

    ```
    docker compose up --detach
    ```
    Use the `--profile` flag, if you need AWS
    ```
    docker compose --profile optional up --detach
    ```

6. Create a local account to access the local WeVoteServer by running:
   - ```docker ps ``` and identify the container ID of the wevote-api
   - ```docker exec -it {container id} /bin/bash ``` to access the container's terminal
   - ```python manage.py create_dev_user first_name last_name email password ``` with appropriate replacements

7. Access the API at [http://localhost:8000/](http://localhost:8000/) and login to the WeVoteServer using credentials from step 6.


8. To stop and remove containers run:

    ```
    docker compose down
    ```
    Or use the `--volumes` flag to remove volumes
    ```
    docker compose down --volumes
    ```

## Resources

1. Docker Compose
    
    - [CLI](https://docs.docker.com/compose/reference/)

    - [Networking](https://docs.docker.com/compose/networking/)

2. Docker Desktop

    - [Why does Docker Desktop for Linux run a VM?](https://docs.docker.com/desktop/faqs/linuxfaqs/#why-does-docker-desktop-for-linux-run-a-vm)

3. PostgreSQL

    - [Config](https://www.postgresql.org/docs/12/config-setting.html#CONFIG-SETTING-SQL-COMMAND-INTERACTION)

    - [Official Docker Image](https://hub.docker.com/_/postgres)

[Back to root README](../README.md)
