import os
import boto3

SKIP_THESE_STACKS = os.environ['SKIP_THESE_STACKS']
SKIP_LIST = [stack.strip() for stack in SKIP_THESE_STACKS.split(',')]


def lambda_handler(data, _context):

    print(data)

    stack_name = data['Stack']['StackName']

    if stack_name in SKIP_LIST:
        print(f"Skipping stack {stack_name}.")
        return

    client = boto3.client('cloudformation')

    response = client.detect_stack_drift(StackName=stack_name)

    return response['StackDriftDetectionId']
