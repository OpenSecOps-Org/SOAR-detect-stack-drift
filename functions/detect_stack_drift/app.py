import os
import boto3
from aws_errors import transient_aws_errors


@transient_aws_errors
def lambda_handler(data, _context):

    stack_name = data['Stack']['StackName']

    client = boto3.client('cloudformation')

    response = client.detect_stack_drift(StackName=stack_name)

    return response['StackDriftDetectionId']
