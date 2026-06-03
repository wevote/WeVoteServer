# README for Installation with Docker
[Back to root README](../README.md)

Only [Docker Desktop](https://docs.docker.com/get-docker/) is required.

[WSL 2](https://learn.microsoft.com/en-us/windows/wsl/compare-versions#comparing-wsl-1-and-wsl-2) users should follow [this guide](https://docs.docker.com/desktop/wsl/) as well.

## Installation

### 1. Clone your WeVoteServer fork (replace wevote with your github username)

  ```
  git clone https://github.com/wevote/WeVoteServer.git
  cd WeVoteServer
  ```

### 2. Create an environment file called `.env` to provide required settings. Example:

  ```
  DATABASE_PASSWORD=MyDBpassword
  DJANGO_SUPERUSER_EMAIL=email@test.com
  DJANGO_SUPERUSER_PASSWORD=MyAdminPassword

  # You can optionally override the default values for database user and name
  # DATABASE_USER=postgres
  # DATABASE_NAME=wevoteserverdb
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

To stop and remove all containers and saved data (including database data), run the following command. Only do this if you want to completely remove your development environment or start over from scratch.
```
docker compose down -v
```
You can also remove the wevote docker network:
```
docker network rm wevote
```

## PgAdmin
#### 1. Access PgAdmin Container
Go to `localhost:8080` in your local web browser to access the `PgAdmin` container UI.
### 2. Register New Server
1. Select `Add New Server` on the homepage.  
<img width="692" height="135" alt="582966431-c6ad5816-26dc-4b5d-a745-c2bbcb0cefbc" src="https://github.com/user-attachments/assets/c0772396-ac83-4537-9a10-8bcfcf5a7c7c" />

3. Server name is `environment_variables.json` value for `DATABASE_NAME`
<img width="696" height="547" alt="582966836-f78e03dc-4a91-4a70-a0c8-740fd57a9bbd" src="https://github.com/user-attachments/assets/579b6665-60c2-4fa3-b727-3b885e95366a" />

5. Set up server connection
* Host name/address: `db` _(or the contianer name set here: https://github.com/mjacquot1/WeVoteServer/blob/61ccbd45ba9c87960269ea65dc0e8eeca6f0bf03/compose.yaml#L4_
* Port: `5432` 
* Maintenance database: `postgres`
* Username: `environment_variables.json` value for `DATABASE_USER`
* Password: Whatever password was used when setup up your postgres superuser as in these instructions: https://github.com/mjacquot1/WeVoteServer/blob/develop/docs/README_API_INSTALL_POSTGRES_MAC.md
<img width="704" height="560" alt="image" src="https://github.com/user-attachments/assets/b94a3349-2bb7-40c4-b38c-994223dd93c7" />

_If necessary, run `ALTER USER  postgres  WITH PASSWORD '<your-password-here>';` for a password change_

6. Click Save

### Debugging docker image with VS Code 
**Prerequisites**
* debugpy must be installed in the Docker container.
* Port 5678 must be exposed and accessible so that VS Code can attach to the debugger.
* Add the following configuration to your .vscode/launch.json file:
```
    {
      "name": "Attach to Docker",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "/wevote/code"
        }
      ],
      "justMyCode": false,
      "django": true
    }
```
<img width="787" height="80" alt="image" src="https://github.com/user-attachments/assets/15c7301d-4451-434a-ad34-c43711dfd968" />

**Attaching the Debugger**
- Open the project in VS Code.
- Navigate to Run and Debug from the left-hand sidebar.
- From the debug configuration dropdown, select Attach to Docker.
- Click Start Debugging (or press F5) to attach VS Code to the Docker container.
- Set breakpoints in the desired source files.
- Trigger the application flow or API request you want to debug. Execution will pause at the configured breakpoints, allowing you to inspect variables, evaluate expressions, and step through the code.
<img width="1635" height="383" alt="image" src="https://github.com/user-attachments/assets/966e4bbb-9603-4f87-ac6f-faac50956a49" />

## Resources

1. Docker Compose
    
    - [CLI](https://docs.docker.com/compose/reference/)

    - [Networking](https://docs.docker.com/compose/networking/)

2. PostgreSQL

    - [Official Docker Image](https://hub.docker.com/_/postgres)

[Back to root README](../README.md)
