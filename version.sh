#!/bin/bash

set -e

cd "$(dirname "$0")"
NAME=$(basename $PWD)
SOURCE=$(git config remote.origin.url | sed -e 's|git@|https://|g' | sed -e 's|github.com:|github.com/|g' | sed 's|\.git||g')
VERSION=$(git describe --always --tag)
COMMIT="$(git log --pretty=format:'%H' -n 1)"

cat > version.json <<HERE
{"name":"${NAME}","version":"${VERSION}","source":"${SOURCE}","commit":"${COMMIT}"}
HERE
