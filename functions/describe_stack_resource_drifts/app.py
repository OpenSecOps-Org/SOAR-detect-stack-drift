import os
import boto3
import json


def lambda_handler(data, _context):

    print(data)

    stack_name = data['Stack']['StackName']

    client = boto3.client('cloudformation')

    response = client.describe_stack_resource_drifts(
        StackName=stack_name,
        StackResourceDriftStatusFilters=[
            'MODIFIED', 'DELETED', 'NOT_CHECKED'
        ]
    )

    drifts = response['StackResourceDrifts']
    drifts = json.loads(json.dumps(drifts, default=str))

    print(drifts)

    return drifts
