#!/bin/bash -e

GIT_REPO="${git_repo}"

PREV_DIR=$(pwd)

# Checking-in env pipeline code to new repo
TEMP_DIR=$(mktemp -d)
SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
cd $TEMP_DIR
cp -r $SCRIPTPATH/../* .
cp $SCRIPTPATH/../.gitignore .

git init
git add .gitignore config terraform group_root
git commit -m "Project factory pipeline, first commit. [skip ci]"
git branch -M main
git remote add origin $GIT_REPO
git push -u origin main
rm -rf $TEMP_DIR
cd "$PREV_DIR"

cat <<EOF
The source code repository of your IAC pipeline has been initialized. You can 
start using it by cloning its git repository:

  git clone $GIT_REPO

EOF