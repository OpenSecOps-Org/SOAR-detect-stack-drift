import os
import boto3

SKIP_THESE_STACKS = os.environ['SKIP_THESE_STACKS']
SKIP_LIST = [stack.strip() for stack in SKIP_THESE_STACKS.split(',')]


def lambda_handler(data, _context):

    print(data)

    stackset_name = data['StackSet']['StackSetName']

    if stackset_name in SKIP_LIST:
        print(f"Skipping stack set {stackset_name}.")
        return

    client = boto3.client('cloudformation')

    response = client.detect_stack_set_drift(
        StackSetName=stackset_name,
        OperationPreferences={
            'RegionConcurrencyType': 'PARALLEL',
            'FailureTolerancePercentage': 90,
            'MaxConcurrentPercentage': 100
        },
        CallAs='SELF'
    )

    return response['OperationId']
