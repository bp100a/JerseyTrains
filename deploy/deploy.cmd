:: Using the AWS CLI (with credentials pre-loaded) upload the zipfile we created
aws lambda update-function-code --function-name JerseyTrains --zip-file fileb://../lambda_deploy/JerseyTrains.zip
