#!/bin/bash

TAG=$(cat kinto/plugins/admin/VERSION)
SRC_DIR="kinto-admin-${TAG}"
TARBALL_NAME="${SRC_DIR}.tar.gz"

# download and unzip release
# TODO: error handling (404 error, can't unzip tarball, etc)
cd kinto/plugins/admin/
curl -L https://github.com/Kinto/kinto-admin/archive/refs/tags/v${TAG}.tar.gz --output $TARBALL_NAME
tar -xf $TARBALL_NAME && rm $TARBALL_NAME

# build kinto-admin bundle
cd $SRC_DIR
npm ci
export SINGLE_SERVER=1
npm run build

# move build and delete source
rm -rf ../build
mv -f build ../
cd ../ && rm -rf $SRC_DIR