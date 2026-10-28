import os
import boto3
from aws_errors import transient_aws_errors
import json


@transient_aws_errors
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
