import os
import boto3
from aws_errors import transient_aws_errors
import json


@transient_aws_errors
def lambda_handler(data, _context):

    print(data)

    stack_drift_detection_id = data['StackDriftDetectionId']

    client = boto3.client('cloudformation')

    response = client.describe_stack_drift_detection_status(
        StackDriftDetectionId=stack_drift_detection_id
    )

    response = json.loads(json.dumps(response, default=str))

    return response
