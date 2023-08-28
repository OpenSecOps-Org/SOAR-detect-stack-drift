Deploys in the Organization account, in each region used.

The Step Function state machine is triggered at 00:00 UTC every Monday. It will retrieve the lists of stacks and stack sets for the region, then detect drift on them, creating incidents when it encounters drift.


## Deployment

First log in to your AWS organisation using SSO and a profile that gives you
AWSAdministratorAccess to the AWS Organizations admin account.

```console
aws sso login --profile <profile-name>
```

Then type:

```console
./deploy
```

