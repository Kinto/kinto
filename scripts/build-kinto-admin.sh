#!/bin/bash
VERSION=$(cat kinto/plugins/admin/VERSION)
TAG="v${VERSION}"
TARBALL_NAME="${TAG}.tar.gz"
SRC_DIR="kinto-admin-${VERSION}"

# download and unzip release
# TODO: error handling (404 error, can't unzip tarball, etc)
cd kinto/plugins/admin/
curl -OL https://github.com/Kinto/kinto-admin/archive/refs/tags/${TAG}.tar.gz
tar -xf $TARBALL_NAME && rm $TARBALL_NAME

# build kinto-admin bundle
pushd $SRC_DIR
npm ci
export SINGLE_SERVER=1
npm run build
popd

# move build and delete source
TARGET_DIR=./build
rm -rf $TARGET_DIR
mv $SRC_DIR/build $TARGET_DIR
rm -rf $SRC_DIR