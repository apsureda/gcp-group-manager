#!/bin/bash -e

IAC_PROJECT="${cicd_project}"
PREV_DIR=$(pwd)
TEMP_DIR=$(mktemp -d)
SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"

cd $SCRIPTPATH/..
# Copy scripts and templates
tar cf - scripts templates | (cd $SCRIPTPATH/builders/factory ; tar xf -)
cd $SCRIPTPATH/builders/factory
gcloud builds submit . --config=cloudbuild.yaml --project=$IAC_PROJECT
rm -rf scripts templates
cd "$PREV_DIR"