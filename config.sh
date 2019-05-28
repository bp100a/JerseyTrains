#!/bin/sh

# Exit script if you try to use an uninitialized variable.
set -o nounset

# Exit script if a statement returns a non-true return value.
set -o errexit

mkdir configuration
cd configuration

# generate a configuration file from environment variables
# (overwrite bogus file that already exists)
echo \"\"\"secret values known only to DevOps\"\"\" > prod_config.py
echo "BUILD_NUMBER =" $CIRCLE_BUILD_NUM >> prod_config.py
echo "REDIS_HOST =" \"$REDIS_HOST\" >> prod_config.py
echo "REDIS_PORT =" $REDIS_PORT >> prod_config.py
echo "REDIS_PASSWORD =" \"$REDIS_PASSWORD\" >> prod_config.py
echo "USERNAME = " \"$NJT_USERNAME\" >> prod_config.py
echo "APIKEY = " \"$NJT_APIKEY\" >> prod_config.py
echo "HOSTNAME =" \"$NJT_URL\" >> prod_config.py

# generate a configuration file from environment variables
# (overwrite bogus file that already exists)
echo \"\"\"secret values known only to DevOps\"\"\" > config.py
echo "BUILD_NUMBER =" $CIRCLE_BUILD_NUM >> config.py
echo "REDIS_HOST ="\"bogus.redis.endpoint\" >> config.py
echo "REDIS_PORT =" $REDIS_PORT >> config.py
echo "REDIS_PASSWORD ="\"bogus.redis.password\" >> config.py
echo "USERNAME = " \"$NJT_USERNAME\" >> config.py
echo "APIKEY = " \"$TEST_NJT_APIKEY\" >> config.py
echo "HOSTNAME =" \"$TEST_NJT_URL\" >> config.py

cd ..
