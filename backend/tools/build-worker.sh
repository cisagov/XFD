#!/bin/bash
# Builds worker docker image.
# If testing out tasks locally, you must run this command after making
# any changes to the worker. This command is also run automatically
# at the beginning of ./deploy-worker.sh.

set -e

docker build --platform linux/amd64 -t crossfeed-worker -f Dockerfile.worker .

docker build --platform linux/amd64 -t pe-worker -f Dockerfile.pe .
