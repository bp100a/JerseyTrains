#!/usr/bin/env bash

# Validates the current STAGE alias
#
# Usage:
#   validate_build.sh
#

# perform some simple validations

aws lambda invoke --invocation-type RequestResponse --function-name JerseyTrains --qualifier STAGE --region us-east-1 --payload file://tests/data/SetHomeStation.JSON SetHomeStation.out
if ! grep -q 'Your home station has been set to' SetHomeStation.out; then
   cat SetHomeStation.out
   exit 1
fi

aws lambda invoke --invocation-type RequestResponse --function-name JerseyTrains --qualifier STAGE --region us-east-1 --payload file://tests/data/GetHomeStation.JSON GetHomeStation.out
if ! grep -q 'Your current home station is' GetHomeStation.out; then
   cat GetHomeStation.out
   exit 2
fi

# nothing wrong, clean exit
exit 0
