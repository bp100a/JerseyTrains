#!/usr/bin/env bash

# Validates the current STAGE alias
#
# Usage:
#   validate_build.sh
#

# perform some simple validations

aws lambda invoke --invocation-type RequestResponse --function-name JerseyTrains --qualifier STAGE --region us-east-1 --payload file://tests/data/SetHomeStation.JSON SetHomeStation.out
if ! grep -q 'Your home station has been set to' SetHomeStation.out; then
   echo SetHomeStation.out
   exit 1
fi

# nothing wrong, clean exit
exit 0
