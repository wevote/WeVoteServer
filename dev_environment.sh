#!/usr/bin/env sh

usage() {
	echo ""
	echo "Summary: Create or remove WeVoteServer development environment"
	echo "  This script provides a way to easily setup a postgres database"
	echo "  server and WeVote API server inside docker containers."
	echo ""
	echo "Usage: $0 <command>"
	echo " where <command> can be:"
	echo "    create     - Creates and runs WeVote API server in the foreground"
	echo "    delete     - Stops the containers (if running) and removes all resources,"
	echo "                 except for database storage volume."
	echo "    deletedb   - Removes database data (stored in docker volume.) "
	echo "                 WARNING: this permanetly removes all wevote database data!"
	exit 1
}


which docker >/dev/null 2>&1
if [ $? -ne 0 ]; then
       echo "ERROR: You must have docker installed on your system."
       echo ""
       echo "Please see https://docs.docker.com/get-docker/ for installation instructions."
       echo ""
       exit 1
fi


CMD=$1
if [ -z "$CMD" ]; then
	usage
fi

DOCKER_API_NAME="wevote-api"
DOCKER_DB_NAME="wevote-db"
DOCKER_API_TAG="${DOCKER_API_NAME}:latest"
DOCKER_DB_TAG="${DOCKER_DB_NAME}:latest"
DOCKER_NETWORK="wevote"
DOCKER_DB_VOLUME="wevote-postgres-data"
DB_NAME="wevotedb"

if [ "$CMD" = "create" ]; then

	if [ -z "$(docker network ls | grep $DOCKER_NETWORK)" ]; then
		echo "Creating docker network.."
		docker network create $DOCKER_NETWORK
	fi

	if [ -z "$(docker ps | grep $DOCKER_DB_NAME)" ]; then
		echo "Creating wevote database container.."
		# build db docker container
		docker build -t $DOCKER_DB_TAG \
			-f docker/Dockerfile.db docker

		# create volume for postgres data
		if [ -z "$(docker volume ls | grep $DOCKER_DB_VOLUME)" ]; then
			docker volume create $DOCKER_DB_VOLUME
		fi
		# start docker container for postgres db
		docker run --network=$DOCKER_NETWORK \
			-d --name=$DOCKER_DB_NAME \
			-v $DOCKER_DB_VOLUME:/var/lib/postgresql/data \
			$DOCKER_DB_TAG

		# create dev database (sleep to make sure pg is started)
		echo "Ensuring the development database exists.."
		sleep 3
		docker exec $DOCKER_DB_NAME psql -U postgres -c "CREATE DATABASE $DB_NAME"
	fi

	# build API docker container
	docker build -t $DOCKER_API_TAG -f docker/Dockerfile.api .

	if [ ! -e config/environment_variables.json ]; then
		echo "Creating develop configuration file in config/environment_variables.json..."
		cp config/environment_variables-template.json config/environment_variables.json
		# configure database name
		sed -i "s/WeVoteServerDB/$DB_NAME/" config/environment_variables.json
		# configure database host to use docker container name
		sed -E -i "s/(DATABASE_HOST.*\":.*)\"\"/\1\"${DOCKER_DB_NAME}\"/" config/environment_variables.json
		
	fi

	# run docker container in foreground
	docker run --network=$DOCKER_NETWORK \
		-p 127.0.0.1:8000:8000 \
		--name=$DOCKER_API_NAME \
		-e DATABASE_HOST=$DOCKER_DB_NAME \
		-v $(pwd):/wevote \
		-it --rm \
		$DOCKER_API_TAG

elif [ "$CMD" = "delete" ]; then
	echo "Removing WeVote developer environment.."

	if [ ! -z "$(docker ps | grep $DOCKER_API_NAME)" ]; then
		echo "Stopping wevote-api container.."
		docker stop $DOCKER_API_NAME
	fi

	echo "Removing wevote-api container.."
	docker rm $DOCKER_API_NAME 2>/dev/null

	if [ ! -z "$(docker ps | grep $DOCKER_DB_NAME)" ]; then
		echo "Stopping postgresql container.."
		docker stop $DOCKER_DB_NAME
	fi

	echo "Removing postgresql container.."
	docker rm $DOCKER_DB_NAME 2>/dev/null

	echo "Removing wevote docker network.."
	docker network rm $DOCKER_NETWORK 2>/dev/null

elif [ "$CMD" = "deletedb" ]; then
	echo "Removing postgres data volume.."
	docker volume rm $DOCKER_DB_VOLUME
else
	echo "ERROR: Invalid command $CMD"
	usage
fi
