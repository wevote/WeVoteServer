# README for Installation with Docker (OSX or Linux)
[Back to root README](../README.md)

**This installation method only requires Docker to be installed and running. All dependencies (libraries or Python modules) reside within the docker containers. These instructions are intended for advanced users familiar with docker, git and python.""

## Installing WeVoteServer: Using Docker
These instructions are for OSX and Linux users.

This method requires [Docker](https://docs.docker.com/get-docker/) to be installed. 


1. Clone your WeVoteServer fork

    ```
    git clone https://github.com/wevote/WeVoteServer.git
    cd WeVoteServer
    ```

2. (Optional) Start WeVote Localstack

    Some parts of the WeVote API service utilize AWS services such as SQS. If you are developing this part of the WeVote API code, you can run a local AWS stack in a container to minimick real AWS services for testing. To start the localstack container, use the following command:
    ```
    docker/dev_environment.sh localstack
    ```

3. Start development environment

    ```
    docker/dev_environment.sh start
    ```
    This command will start a background postgres database container (named `wevote-db`) that will host your development database. It will also build and launch the WeVote API container. The WeVote API container will run in the foreground, where you can monitor the service logs while developing. This command may take a few minutes to build the API container the first time it is run.

    Once the WeVote API container is running, you can access your local WeVote API dev environment at:
        [http://localhost:8000/](http://localhost:8000/)

    When you are done developing, press Control-C to stop your local WeVote API container in the running terminal. To shut down the database container (and localstack container, if running), you can use the following command:
    ```
    docker/dev_environment.sh stop
    ```
    Once stopped, there will be no running WeVote API resources. To delete the underlying containers (except Postgres database volume), use the following command:
    ```
    docker/dev_environment.sh delete
    ```
    The WeVote API Postgres database is stored in a separate docker volume. To completely remove the database volume, use the following command:
    ```
    docker/dev_environment.sh deletedb
    ```

[Back to root README](../README.md)
