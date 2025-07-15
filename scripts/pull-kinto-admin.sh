#!/bin/bash
set -euo pipefail

VERSION=$(cat kinto/plugins/admin/VERSION)
TAG="v${VERSION}"

# download and unzip release
echo "Download kinto-admin release ${TAG}"
curl -OL "https://github.com/Kinto/kinto-admin/releases/download/${TAG}/kinto-admin-release.tar"
rm -r ./kinto/plugins/admin/build || echo "admin/build folder doesn't exist yet"
mkdir ./kinto/plugins/admin/build
tar -xf kinto-admin-release.tar -C ./kinto/plugins/admin/build && rm kinto-admin-release.tar
echo "Extracted version $(cat ./kinto/plugins/admin/build/VERSION)"
