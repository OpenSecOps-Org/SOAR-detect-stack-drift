import os
import boto3
import json

# Stacks to skip
SKIP_THESE_STACKS = os.environ['SKIP_THESE_STACKS']
SKIP_LIST = [stack.strip() for stack in SKIP_THESE_STACKS.split(',')]

# Stack prefixes to skip
SKIP_PREFIXES = os.environ.get('SKIP_PREFIXES', 'INFRA-')
SKIP_PREFIX_LIST = [prefix.strip() for prefix in SKIP_PREFIXES.split(',')]

def lambda_handler(data, _context):

    client = boto3.client('cloudformation')

    response = client.list_stacks(
        StackStatusFilter=['CREATE_COMPLETE',
                           'UPDATE_COMPLETE',
                           'IMPORT_COMPLETE',
                           ]
    )
    # Serialize to JSON and back to handle datetime objects, then filter out the stacks
    stacks = [stack for stack in json.loads(json.dumps(response['StackSummaries'], default=str))
              if not (stack['StackName'] in SKIP_LIST or 
                      any(stack['StackName'].startswith(prefix) for prefix in SKIP_PREFIX_LIST))]

    response = client.list_stack_sets(
        Status='ACTIVE',
        CallAs='SELF'
    )
    # Serialize to JSON and back to handle datetime objects, then filter out the stack sets
    stack_sets = [stack_set for stack_set in json.loads(json.dumps(response['Summaries'], default=str))
                  if not (stack_set['StackSetName'] in SKIP_LIST or 
                          any(stack_set['StackSetName'].startswith(prefix) for prefix in SKIP_PREFIX_LIST))]

    return {
        'Stacks': stacks,
        'StackSets': stack_sets
    }
