#!/usr/bin/env bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
./botctl.sh setup
./botctl.sh restart
./botctl.sh atop
