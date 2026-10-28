import os
import random
import boto3
from aws_errors import transient_aws_errors
import json

# Stacks to skip
SKIP_THESE_STACKS = os.environ['SKIP_THESE_STACKS']
SKIP_LIST = [stack.strip() for stack in SKIP_THESE_STACKS.split(',')]

# Stack prefixes to skip
SKIP_PREFIXES = os.environ.get('SKIP_PREFIXES', 'INFRA-')
SKIP_PREFIX_LIST = [prefix.strip() for prefix in SKIP_PREFIXES.split(',')]

# The lists pass through the state machine, whose state data is limited to 256 KB
PAYLOAD_BUDGET = 200_000


def skipped(name):
    return name in SKIP_LIST or any(name.startswith(prefix) for prefix in SKIP_PREFIX_LIST)


@transient_aws_errors
def lambda_handler(data, _context):

    client = boto3.client('cloudformation')

    # Every page; only the fields the later steps use
    stacks = [{'StackName': stack['StackName'], 'StackId': stack['StackId']}
              for page in client.get_paginator('list_stacks').paginate(
                  StackStatusFilter=['CREATE_COMPLETE',
                                     'UPDATE_COMPLETE',
                                     'IMPORT_COMPLETE',
                                     ])
              for stack in page['StackSummaries']
              if not skipped(stack['StackName'])]

    stack_sets = [{'StackSetName': stack_set['StackSetName']}
                  for page in client.get_paginator('list_stack_sets').paginate(Status='ACTIVE', CallAs='SELF')
                  for stack_set in page['Summaries']
                  if not skipped(stack_set['StackSetName'])]

    # Too many stacks for one run: a random selection, so that the others are checked in later runs
    budget = PAYLOAD_BUDGET - len(json.dumps({'Stacks': [], 'StackSets': stack_sets}))
    if len(json.dumps(stacks)) > budget:
        random.shuffle(stacks)
        selected, size = [], 2
        for stack in stacks:
            size += len(json.dumps(stack)) + 2
            if size > budget:
                break
            selected.append(stack)
        print(f"{len(stacks) - len(selected)} of {len(stacks)} stacks are not checked this run")
        stacks = selected

    return {
        'Stacks': stacks,
        'StackSets': stack_sets
    }
