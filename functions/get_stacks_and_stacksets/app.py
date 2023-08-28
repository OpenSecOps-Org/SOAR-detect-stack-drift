import os
import boto3
import json


def lambda_handler(data, _context):

    client = boto3.client('cloudformation')

    response = client.list_stacks(
        StackStatusFilter=['CREATE_COMPLETE',
                           'UPDATE_COMPLETE',
                           'IMPORT_COMPLETE',
                           ]
    )
    stacks = json.loads(json.dumps(response['StackSummaries'], default=str))

    response = client.list_stack_sets(
        Status='ACTIVE',
        CallAs='SELF'
    )
    stack_sets = json.loads(json.dumps(response['Summaries'], default=str))

    return {
        'Stacks': stacks,
        'StackSets': stack_sets
    }
