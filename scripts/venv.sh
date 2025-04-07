#!/bin/bash

python3.13 -m venv .venv
source .venv/bin/activate

# On Windows run:
# .venv\Scripts\Activate

# Load environment variables from the .env file
export $(grep -v '^#' .env.devel | xargs)

poetry install --no-root

export KMP_DUPLICATE_LIB_OK=TRUE

which python3
