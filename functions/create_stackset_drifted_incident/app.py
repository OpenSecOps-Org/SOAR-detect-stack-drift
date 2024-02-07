import os
import datetime
from datetime import datetime, timezone
import uuid
import boto3

REGION = os.environ['REGION']
ACCOUNT_ID = os.environ['ACCOUNT_ID']
INCIDENT_SEVERITY = os.environ['INCIDENT_SEVERITY']

client = boto3.client('securityhub')


def lambda_handler(data, _context):
    print(data)

    timestamp = timestamp = datetime.now(
        timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    noise = str(uuid.uuid4())

    stackset_name = data['StackSet']['StackSetName']

    finding_id = f"{stackset_name}-{noise}"

    region = REGION
    account_id = ACCOUNT_ID

    # summaries = data['Summaries']

    details = data['StackSetOperation'].get(
        'StackSetDriftDetectionDetails', {})
    total = details.get('TotalStackInstancesCount', 'N/A')
    drifted = details.get('DriftedStackInstancesCount', 'N/A')
    in_sync = details.get('InSyncStackInstancesCount', 'N/A')
    failed = details.get('FailedStackInstancesCount', 'N/A')

    title = f"Stack Set drift for '{stackset_name}'"

    description = f'''\
The stack set '{stackset_name}' is not IN_SYNC:

    * Total number of templates: {total}
    * Drifted: {drifted}
    * In sync: {in_sync}
    * Failed:  {failed}
    
The full drift specification is available from the CloudFormation console for stack set '{stackset_name}' in account {account_id}, region {region}.
'''

    incident_domain = "INFRA"

    finding = {
        "SchemaVersion": "2018-10-08",
        "Id": finding_id,
        "ProductArn": f"arn:aws:securityhub:{region}:{account_id}:product/{account_id}/default",
        "GeneratorId": title,
        "AwsAccountId": account_id,
        "Types": [
            f"Software and Configuration Checks/Security Automation/Stack Set Drift",
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
                "Text": "Instructions for remediating a drifted CloudFormation stack set can be found here:",
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
            "aws/securityhub/FindingId": f"arn:aws:securityhub:{region}:{account_id}:product/{account_id}/default/{stackset_name}",
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
