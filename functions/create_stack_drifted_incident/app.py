import os
import datetime
from datetime import datetime, timezone
import uuid
import boto3

INCIDENT_SEVERITY = os.environ['INCIDENT_SEVERITY']

client = boto3.client('securityhub')


def lambda_handler(data, _context):
    print(data)

    timestamp = timestamp = datetime.now(
        timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    noise = str(uuid.uuid4())

    stack_name = data['Stack']['StackName']
    stack_id = data['Stack']['StackId']

    finding_id = f"{stack_id.rsplit('/', 1)[1]}-{noise}"
    region = stack_id.split(':')[3]
    account_id = stack_id.split(':')[4]

    # stack_resource_drifts = data['StackResourceDrifts']
    n_deviations = data['StackDriftDetectionStatus'].get(
        'DriftedStackResourceCount', 0)

    title = f"Stack drift in '{stack_name}'"

    description = f'''\
The single stack '{stack_name}' (not a StackSet) has drifted in account {account_id}. The number of detected deviations is {n_deviations}. 

The full drift specification is available from the CloudFormation console for stack '{stack_name}', account {account_id}, region {region}.
'''

    incident_domain = "INFRA"

    finding = {
        "SchemaVersion": "2018-10-08",
        "Id": finding_id,
        "ProductArn": f"arn:aws:securityhub:{region}:{account_id}:product/{account_id}/default",
        "GeneratorId": title,
        "AwsAccountId": account_id,
        "Types": [
            f"Software and Configuration Checks/Security Automation/Stack Drift",
        ],
        "CreatedAt": timestamp,
        "UpdatedAt": timestamp,
        "Severity": {
            "Label": INCIDENT_SEVERITY
        },
        "Title": title,
        "Description": description,
        "Remediation": {
            "Recommendation": {
                "Text": "Instructions for remediating a drifted single CloudFormation stack can be found here:",
                "Url": "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html"
            }
        },
        "Resources": [
            {
                "Type": "AwsAccountId",
                "Id": account_id,
                "Region": region,
            },
        ],
        "ProductFields": {
            "aws/securityhub/FindingId": f"arn:aws:securityhub:{region}:{account_id}:product/{account_id}/default/{finding_id}",
            "aws/securityhub/ProductName": "Default",
            "aws/securityhub/CompanyName": "Security Automation",
            "TicketDestination": "TEAM",
            "IncidentDomain": incident_domain
        },
        "VerificationState": "TRUE_POSITIVE",
        "Workflow": {
            "Status": "NEW"
        },
        "RecordState": "ACTIVE"
    }

    print(f"Creating {INCIDENT_SEVERITY} incident for {incident_domain} alarm '{title}'")
    response = client.batch_import_findings(Findings=[finding])
    if response['FailedCount'] != 0:
        print(f"The finding failed to import: '{response['FailedFindings']}'")
    else:
        print("Finding imported successfully.")

    return True
