"""
The Lambdas: CloudFormation drift detection throttles readily when a Map runs it for every stack. Throttling
and other transient AWS errors leave the Lambdas as AWSTransientError, which the state machine retries.
Other errors keep their own name and are not retried.
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

from aws_errors import AWSTransientError

STACK = {'StackName': 'example-stack',
         'StackId': 'arn:aws:cloudformation:eu-north-1:111111111111:stack/example-stack/abc'}
STACK_SET = {'StackSetName': 'example-stack-set'}

# Lambda -> (the CloudFormation call it makes, its input)
CLOUDFORMATION = {
    'detect_stack_drift': ('detect_stack_drift', {'Stack': STACK}),
    'get_stack_drift_detection_status': ('describe_stack_drift_detection_status',
                                         {'StackDriftDetectionId': 'detection-1'}),
    'describe_stack_resource_drifts': ('describe_stack_resource_drifts', {'Stack': STACK}),
    'detect_stackset_drift': ('detect_stack_set_drift', {'StackSet': STACK_SET}),
    'get_stackset_drift_detection_status': ('describe_stack_set_operation',
                                            {'StackSet': STACK_SET, 'OperationId': 'operation-1'}),
    'describe_stackset_resource_drifts': ('list_stack_instances', {'StackSet': STACK_SET}),
}
# Lambda -> its input; both import a finding into Security Hub through a module-level client
INCIDENTS = {
    'create_stack_drifted_incident': {'Stack': STACK, 'StackDriftDetectionStatus': {}},
    'create_stackset_drifted_incident': {'StackSet': STACK_SET, 'StackSetOperation': {}},
}


def client_error(code, status=400):
    return botocore.exceptions.ClientError(
        {'Error': {'Code': code, 'Message': code}, 'ResponseMetadata': {'HTTPStatusCode': status}}, 'op')


def app(name):
    return importlib.import_module(f'functions.{name}.app')


def run_cloudformation(name, error):
    call, data = CLOUDFORMATION[name]
    client = MagicMock()
    getattr(client, call).side_effect = error
    module = app(name)
    with patch.object(module.boto3, 'client', return_value=client):
        return module.lambda_handler(data, None)


def run_incident(name, error):
    client = MagicMock()
    client.batch_import_findings.side_effect = error
    module = app(name)
    with patch.object(module, 'client', client):
        return module.lambda_handler(INCIDENTS[name], None)


TRANSIENT = [client_error('Throttling'), client_error('ThrottlingException'),
             client_error('InternalFailure', 500)]
PERMANENT = [client_error('ValidationError'), client_error('AccessDenied', 403)]


@pytest.mark.parametrize('name', CLOUDFORMATION)
@pytest.mark.parametrize('error', TRANSIENT, ids=lambda e: e.response['Error']['Code'])
def test_throttled_cloudformation_calls_are_retried(name, error):
    with pytest.raises(AWSTransientError):
        run_cloudformation(name, error)


@pytest.mark.parametrize('name', CLOUDFORMATION)
@pytest.mark.parametrize('error', PERMANENT, ids=lambda e: e.response['Error']['Code'])
def test_other_cloudformation_errors_keep_their_own_name(name, error):
    with pytest.raises(botocore.exceptions.ClientError) as raised:
        run_cloudformation(name, error)
    assert not isinstance(raised.value, AWSTransientError)


@pytest.mark.parametrize('name', INCIDENTS)
@pytest.mark.parametrize('error', [client_error('TooManyRequestsException', 429),
                                   client_error('LimitExceededException', 429),
                                   client_error('InternalException', 500)],
                         ids=lambda e: e.response['Error']['Code'])
def test_a_throttled_incident_import_is_retried(name, error):
    with pytest.raises(AWSTransientError):
        run_incident(name, error)


@pytest.mark.parametrize('name', INCIDENTS)
def test_a_refused_incident_import_keeps_its_own_name(name):
    with pytest.raises(botocore.exceptions.ClientError) as raised:
        run_incident(name, client_error('InvalidAccessException', 401))
    assert not isinstance(raised.value, AWSTransientError)


@pytest.mark.parametrize('name', INCIDENTS)
def test_imports_the_incident(name):
    assert run_incident(name, None) is True


# ---------------------------------------------------------------------------
# get_stacks_and_stacksets: every page, only what later steps use, within the payload limit
# ---------------------------------------------------------------------------

def stack(name):
    return {'StackName': name, 'StackId': f'arn:aws:cloudformation:eu-north-1:111111111111:stack/{name}/abc',
            'StackStatus': 'CREATE_COMPLETE', 'CreationTime': '2026-01-01T00:00:00Z', 'TemplateDescription': 'x'}


def listing_client(stack_pages, stack_set_pages, error=None):
    client = MagicMock()
    paginators = {
        'list_stacks': MagicMock(**{'paginate.return_value': [{'StackSummaries': p} for p in stack_pages]}),
        'list_stack_sets': MagicMock(**{'paginate.return_value': [{'Summaries': p} for p in stack_set_pages]}),
    }
    if error:
        paginators['list_stacks'].paginate.side_effect = error
    client.get_paginator.side_effect = lambda operation: paginators[operation]
    return client, paginators


def list_all(client):
    module = app('get_stacks_and_stacksets')
    with patch.object(module.boto3, 'client', return_value=client):
        return module.lambda_handler({}, None)


def test_lists_every_page_of_stacks_and_stack_sets():
    client, paginators = listing_client([[stack('a'), stack('INFRA-skipped')], [stack('b')]],
                                        [[{'StackSetName': 's1', 'Status': 'ACTIVE'}], [{'StackSetName': 's2'}]])
    result = list_all(client)
    assert result == {'Stacks': [{'StackName': 'a', 'StackId': stack('a')['StackId']},
                                 {'StackName': 'b', 'StackId': stack('b')['StackId']}],
                      'StackSets': [{'StackSetName': 's1'}, {'StackSetName': 's2'}]}
    paginators['list_stacks'].paginate.assert_called_once_with(
        StackStatusFilter=['CREATE_COMPLETE', 'UPDATE_COMPLETE', 'IMPORT_COMPLETE'])
    paginators['list_stack_sets'].paginate.assert_called_once_with(Status='ACTIVE', CallAs='SELF')


def test_stays_within_the_state_machine_payload_limit(capsys):
    """Too many stacks for one run: a random selection, so the others are checked in later runs."""
    module = app('get_stacks_and_stacksets')
    stacks = [stack(f'stack-{i:05d}-' + 'x' * 100) for i in range(2000)]
    client, _ = listing_client([stacks], [[{'StackSetName': 's1'}]])
    result = list_all(client)
    assert len(json.dumps(result)) <= module.PAYLOAD_BUDGET
    assert result['StackSets'] == [{'StackSetName': 's1'}]
    names = {s['StackName'] for s in result['Stacks']}
    assert 0 < len(names) < len(stacks) and names <= {s['StackName'] for s in stacks}
    assert 'not checked this run' in capsys.readouterr().out


@pytest.mark.parametrize('error, transient', [(client_error('Throttling'), True),
                                              (client_error('AccessDenied', 403), False)])
def test_listing_errors(error, transient):
    client, _ = listing_client([], [], error=error)
    with pytest.raises(AWSTransientError if transient else botocore.exceptions.ClientError) as raised:
        list_all(client)
    assert isinstance(raised.value, AWSTransientError) == transient
