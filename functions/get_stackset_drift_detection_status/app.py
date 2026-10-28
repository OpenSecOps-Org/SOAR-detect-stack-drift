import os
import boto3
from aws_errors import transient_aws_errors
import json


@transient_aws_errors
def lambda_handler(data, _context):

    print(data)

    operation_id = data['OperationId']
    stackset_name = data['StackSet']['StackSetName']

    client = boto3.client('cloudformation')

    response = client.describe_stack_set_operation(
        StackSetName=stackset_name,
        OperationId=operation_id,
        CallAs='SELF'
    )

    response = json.loads(json.dumps(response, default=str))

    return response['StackSetOperation']
