#!/usr/bin/env sh

# dev env settings
DOCKER_API_NAME="wevote-api"
DOCKER_DB_NAME="wevote-db"
DOCKER_LOCALSTACK_NAME="wevote-localstack"
DOCKER_API_TAG="${DOCKER_API_NAME}:latest"
DOCKER_DB_TAG="${DOCKER_DB_NAME}:latest"
DOCKER_LOCALSTACK_TAG="localstack/localstack"
DOCKER_NETWORK="wevote"
DOCKER_DB_VOLUME="wevote-postgres-data"
DB_NAME="wevotedb"

set -e

# determine base WeVoteServer directory
BASEDIR=$(cd $(dirname $0)/..; pwd)

usage() {
	echo ""
	echo "Summary: Create or remove WeVoteServer development environment"
	echo "  This script provides a way to easily setup a postgres database"
	echo "  server and WeVote API server inside docker containers."
	echo ""
	echo "Usage: $0 <command>"
	echo " where <command> can be:"
	echo "    start      - Creates and starts WeVote API development environment"
	echo "    stop       - Stops all WeVote API development containers"
	echo "    delete     - Stops and removes all WeVote API development resources,"
	echo "                 except for database storage volume."
	echo "    deletedb   - Removes database storage volume (docker volume.) "
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


create_wevote_docker_network() {
	if [ -z "$(docker network ls | grep $DOCKER_NETWORK)" ]; then
		echo "Creating WeVote docker network.."
		docker network create $DOCKER_NETWORK
	fi
}

start_wevote_localstack() {
	if [ -z "$(docker container ls -a | grep $DOCKER_LOCALSTACK_NAME)" ]; then
		echo "Creating wevote localstack container.."

		# start docker container for postgres db
		docker run --network=$DOCKER_NETWORK \
			-d --name=$DOCKER_LOCALSTACK_NAME \
			$DOCKER_LOCALSTACK_TAG
	else
		echo "Wevote localstack container already exists, checking if running.."
		if [ -z "$(docker ps | grep $DOCKER_LOCALSTACK_NAME)" ]; then
			echo "Starting wevote localstack container..."
			docker start $DOCKER_LOCALSTACK_NAME
		fi
	fi
}

start_wevote_db() {
	if [ -z "$(docker container ls -a | grep $DOCKER_DB_NAME)" ]; then
		echo "Creating wevote database container.."
		# build db docker container
		docker build -t $DOCKER_DB_TAG \
			-f $BASEDIR/docker/Dockerfile.db $BASEDIR/docker

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
		echo "Waiting for database container to start..."
		sleep 3
		echo "Creating wevote db ($DB_NAME)..."
		docker exec $DOCKER_DB_NAME psql -U postgres -c "CREATE DATABASE $DB_NAME" || true
	else
		echo "Wevote database container already exists, checking if running.."
		if [ -z "$(docker ps | grep $DOCKER_DB_NAME)" ]; then
			echo "Starting wevote database container..."
			docker start $DOCKER_DB_NAME
		fi
	fi
}

build_wevote_api() {
	# build API docker container
	docker build --pull -t $DOCKER_API_TAG -f docker/Dockerfile.api $BASEDIR
	if [ ! -e $BASEDIR/config/environment_variables.json ]; then
		echo "Creating developer configuration file in config/environment_variables.json..."
		cat $BASEDIR/config/environment_variables-template.json | \
			sed "s/WeVoteServerDB/$DB_NAME/" | \
			sed -E "s/(DATABASE_HOST.*\":.*)\"\"/\1\"${DOCKER_DB_NAME}\"/" \
			> $BASEDIR/config/environment_variables.json
	fi
}

run_wevote_api() {
	# run docker container in foreground
	docker run --network=$DOCKER_NETWORK \
		-p 127.0.0.1:8000:8000 \
		--name=$DOCKER_API_NAME \
		-e DATABASE_HOST=$DOCKER_DB_NAME \
		-v $BASEDIR:/wevote \
		-it --rm \
		$DOCKER_API_TAG
}

stop_all() {
	echo "Stopping any running WeVote API containers.."
	for container in $DOCKER_API_NAME $DOCKER_DB_NAME $DOCKER_LOCALSTACK_NAME; do
		if [ ! -z "$(docker ps | grep $container)" ]; then
			docker stop $container
		fi
	done
}
remove_all() {
	echo "Removing WeVote API containers.."
	for container in $DOCKER_API_NAME $DOCKER_DB_NAME $DOCKER_LOCALSTACK_NAME; do
		docker rm $container 2>/dev/null || true
	done
	echo "Removing wevote docker network.."
	docker network rm $DOCKER_NETWORK 2>/dev/null || true
}

if [ "$CMD" = "start" ]; then
	create_wevote_docker_network
	start_wevote_db
	start_wevote_localstack
	build_wevote_api
	run_wevote_api
elif [ "$CMD" = "stop" ]; then
	stop_all
elif [ "$CMD" = "delete" ]; then
	stop_all
	remove_all
elif [ "$CMD" = "deletedb" ]; then
	echo "Removing postgres data volume.."
	docker volume rm $DOCKER_DB_VOLUME 2>/dev/null || true
else
	echo "ERROR: Invalid command $CMD"
	usage
fi
