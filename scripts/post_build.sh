#! /bin/bash
s3_bucket=ae-lambda-deploy
s3_key=complaint_counter
s3_uri=s3://$s3_bucket/$s3_key

aws s3 cp $s3_key $s3_uri --recursive

aws cloudformation deploy \
    --stack-name CurtisLaGripe \
    --template-file CurtisLaGripe.yml \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides S3BucketParameter=$s3_bucket S3KeyParameter=$s3_key
