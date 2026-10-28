"""
The Lambdas: CloudFormation drift detection throttles readily when a Map runs it for every stack. Throttling
and other transient AWS errors leave the Lambdas as AWSTransientError, which the state machine retries.
Other errors keep their own name and are not retried.
"""

import importlib
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

from aws_errors import AWSTransientError

STACK = {'StackName': 'example-stack',
         'StackId': 'arn:aws:cloudformation:eu-north-1:111111111111:stack/example-stack/abc'}
STACK_SET = {'StackSetName': 'example-stack-set'}

# Lambda -> (the CloudFormation call it makes, its input)
CLOUDFORMATION = {
    'get_stacks_and_stacksets': ('list_stacks', {}),
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
