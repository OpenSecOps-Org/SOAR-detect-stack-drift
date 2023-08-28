import os
import boto3


def lambda_handler(data, _context):

    print(data)

    stackset_name = data['StackSet']['StackSetName']

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
