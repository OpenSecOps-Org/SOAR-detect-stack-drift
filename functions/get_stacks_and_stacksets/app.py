import os
import boto3
import json

SKIP_THESE_STACKS = os.environ['SKIP_THESE_STACKS']
SKIP_LIST = [stack.strip() for stack in SKIP_THESE_STACKS.split(',')]


def lambda_handler(data, _context):

    client = boto3.client('cloudformation')

    response = client.list_stacks(
        StackStatusFilter=['CREATE_COMPLETE',
                           'UPDATE_COMPLETE',
                           'IMPORT_COMPLETE',
                           ]
    )
    # Serialize to JSON and back to handle datetime objects, then filter out the stacks that are in the SKIP_LIST
    stacks = [stack for stack in json.loads(json.dumps(response['StackSummaries'], default=str))
              if stack['StackName'] not in SKIP_LIST]

    response = client.list_stack_sets(
        Status='ACTIVE',
        CallAs='SELF'
    )
    # Serialize to JSON and back to handle datetime objects, then filter out the stack sets that are in the SKIP_LIST
    stack_sets = [stack_set for stack_set in json.loads(json.dumps(response['Summaries'], default=str))
                  if stack_set['StackSetName'] not in SKIP_LIST]

    return {
        'Stacks': stacks,
        'StackSets': stack_sets
    }
