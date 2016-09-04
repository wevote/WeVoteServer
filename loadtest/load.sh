#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
locust -f $DIR/WeVoteLocust.py -H http://localhost:8000 -c 100 -r 10 -n 1000 --no-web --print-stats WeVoteLocust
