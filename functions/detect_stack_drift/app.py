import os
import boto3


def lambda_handler(data, _context):

    stack_name = data['Stack']['StackName']

    client = boto3.client('cloudformation')

    response = client.detect_stack_drift(StackName=stack_name)

    return response['StackDriftDetectionId']
