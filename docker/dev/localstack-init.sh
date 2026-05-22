#!/bin/bash
set -e

awslocal sqs create-queue \
  --queue-name job-queue.fifo \
  --attributes FifoQueue=true,ContentBasedDeduplication=true

awslocal s3 mb s3://wevote-images
awslocal s3 mb s3://wevote-temporary
