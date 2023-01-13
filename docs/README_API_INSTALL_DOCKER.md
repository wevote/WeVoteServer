# README for Installation with Docker (OSX or Linux)
[Back to root README](../README.md)

**This installation method is relatively simple and only requires Docker to be installed. This method is recommended for advanced users familiar with docker, git and python.""

## Installing WeVoteServer: Using Docker
These instructions are for OSX and Linux users.

This method utilizes Docker to create a development environment for WeVote API. It creates 2 containers: a postgres database container and a WeVote API container.

This method requires [Docker](https://docs.docker.com/get-docker/) to be installed. 


1. Clone the WeVoteServer repo

    ```
    git clone https://github.com/wevote/WeVoteServer.git
    cd WeVoteServer
    ```

2. Start development environment

    ```
    docker/dev_environment.sh start
    ```
    This command will (1) start a background postgres database container (named `wevote-db`) and create the initial WeVote database
    (if needed) and (2) run WeVote API development container in the foreground.

    Once the containers are running, you can access your local WeVote API dev environment at:
        [http://localhost:8000/](http://localhost:8000/)


[Back to root README](../README.md)
