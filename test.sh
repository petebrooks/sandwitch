#!/bin/bash

set -x

echo "Is this on???"

# Check if poetry is available
command -v poetry
if [ $? -ne 0 ]; then
    echo "poetry is not available"
    exit 1
fi

python --version
poetry --version

ls ~/Downloads/y2party/vids/composites/composites
ls ~/Downloads/y2party/vids/composites

poetry run python sandwitch/main.py ~/Downloads/y2party/vids/composites ~/Downloads/y2party/vids/composites/composites --verbose "$@"
