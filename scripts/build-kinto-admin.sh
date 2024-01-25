#!/bin/bash
set -euo pipefail

VERSION=$(cat kinto/plugins/admin/VERSION)
TAG="v${VERSION}"
TARBALL_NAME="${TAG}.tar.gz"
SRC_DIR="kinto-admin-${VERSION}"

# download and unzip release
cd kinto/plugins/admin/
curl -OL "https://github.com/Kinto/kinto-admin/archive/refs/tags/${TAG}.tar.gz"
tar -xf "${TARBALL_NAME}" && rm "${TARBALL_NAME}"

# build kinto-admin bundle
pushd "${SRC_DIR}"
npm ci
export ASSET_PATH="/v1/admin/"
# kinto-admin <= 2.1.1
export SINGLE_SERVER=1
# kinto-admin >= 2.1.2
export KINTO_ADMIN_SINGLE_SERVER=1
npm run build
popd

# move build and delete source
TARGET_DIR=./build
rm -rf "${TARGET_DIR}"
mv "${SRC_DIR}/build" "${TARGET_DIR}"
rm -rf "${SRC_DIR}"
