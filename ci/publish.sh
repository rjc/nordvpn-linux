#!/usr/bin/env bash
set -euxo

PACKAGE=${1}

source "${CI_PROJECT_DIR}"/ci/archs.sh
source "${CI_PROJECT_DIR}"/ci/repository_name.sh "${PACKAGE}"

echo "Publishing repo"
case "${PACKAGE}" in
    "deb")
        pulp-admin deb repo publish run --repo-id="${REPOSITORY}"
        ;;
    "rpm")
        for arch in "${ARCHS[@]}"; do
            pulp-admin rpm repo publish run --repo-id="${REPOSITORY}"-"${ARCHS_RPM[$arch]}"
        done
        ;;
esac
echo "Repo published"
