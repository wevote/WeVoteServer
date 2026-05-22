# README for Installation with Docker with SSL
[Back to root README](../README.md)

Only [Docker Desktop](https://docs.docker.com/get-docker/) is required.

[WSL 2](https://learn.microsoft.com/en-us/windows/wsl/compare-versions#comparing-wsl-1-and-wsl-2) users should follow [this guide](https://docs.docker.com/desktop/wsl/) as well.

## Installation

### 1. Clone your WeVoteServer fork (replace wevote with your github username)

  ```
  git clone https://github.com/wevote/WeVoteServer.git
  cd WeVoteServer
  ```

### 2. Create an environment file called `.env` to provide required settings. Suggested initial values:

  ```
DATABASE_PASSWORD=admin
DJANGO_SUPERUSER_EMAIL=anyone@wevoteeducation.org
DJANGO_SUPERUSER_PASSWORD=admin
DATABASE_USER=postgres
DATABASE_NAME=wevoteserverdb
  ```

### 3. Create Docker network
We will run all WeVote docker containers in an isolated docker network. Since the backend (WeVoteServer) and frontend (WebApp) both use docker compose (which typically manages docker networks for us), we must manually create this shared network to avoid conflicts. Even if you are not planning on running your own frontend, this step must still be completed.
```
docker network create wevote
```

### 4. Starting the containers

To start the WeVote API service and dependencies, use one of these commands. If you are just getting started, we recommend using the first (foreground) method below. These commands assume you are in the `WeVoteServer` folder created in Step 1 above.

#### 1. Start in the foreground (for debugging/logs):
```
docker compose up
```
This command builds, (re)creates, and starts all services, and aggregates their logs in your terminal. **Press `Ctrl+C` to stop the containers gracefully.**

#### 2. Start in the background (detached mode):
```
docker compose up -d
```
The `-d` (detached) flag runs containers in the background, leaving them running after you exit the terminal. Once started in detached state, use this command to stop the containers:
```
docker compose down
```

Once the containers are running, you can now access the API at [http://localhost:8000/](http://localhost:8000/)

### 5. Remove containers and data

To stop and remove all containers and saved data (including all of your database data), run the following command. Only do this if you want to completely remove your development environment or start over from scratch.  You may need to do this if you manually dropped tables or the database, because Docker will not recreate parts, only the whole.
```
docker compose down -v
```
You can also remove the wevote docker network:
```
docker network rm wevote
```

### 6. Rebuild all the layers -- needed if you work on the entrypoint, compose.yaml, or Dockerfile.dev
The changes you makein entrypoint, compose.yaml, Dockerfile.dev, requirements.txt, .env, environment_variables.json
will not go into effect in your containers unless you rebuild all the layers with the following command:
```
docker compose build --no-cache
```

## Resources

1. Docker Compose
    
    - [CLI](https://docs.docker.com/compose/reference/)

    - [Networking](https://docs.docker.com/compose/networking/)

2. PostgreSQL

    - [Official Docker Image](https://hub.docker.com/_/postgres)

3. Pgadmin4
2026-05-14 21:55:46,305: ERROR  pgadmin:        400 Bad Request: The CSRF session token is missing.

[Back to root README](../README.md)
