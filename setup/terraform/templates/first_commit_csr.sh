#!/bin/bash -e

IAC_PROJECT="${cicd_project}"
GIT_REPO="${git_repo}"

PREV_DIR=$(pwd)

# Checking-in env pipeline code to new repo
TEMP_DIR=$(mktemp -d)
SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
cd $TEMP_DIR
gcloud source repos clone "$GIT_REPO" --project=$IAC_PROJECT
cd $GIT_REPO
git checkout -b main
cp -r $SCRIPTPATH/../* .
cp $SCRIPTPATH/../.gitignore .
git add .gitignore config terraform group_root
git commit -m "Project factory pipeline, first commit. [skip ci]"
git push origin main
rm -rf $TEMP_DIR
cd "$PREV_DIR"

cat <<EOF
The source code repository of your IAC pipeline has been initialized. You can 
start using it by cloning its git repository:

  gcloud source repos clone "$GIT_REPO" --project=$IAC_PROJECT

You can browse the factory source code repository from this URL:

  https://source.cloud.google.com/$IAC_PROJECT/$GIT_REPO/

EOF