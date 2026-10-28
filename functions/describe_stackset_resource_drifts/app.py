import os
import boto3
from aws_errors import transient_aws_errors
import json


@transient_aws_errors
def lambda_handler(data, _context):

    print(data)

    stackset_name = data['StackSet']['StackSetName']

    client = boto3.client('cloudformation')

    response = client.list_stack_instances(
        StackSetName=stackset_name,
        CallAs='SELF'
    )

    drifts = response['Summaries']
    drifts = json.loads(json.dumps(drifts, default=str))

    print(drifts)

    return drifts
