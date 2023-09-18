Deploys in the Organization account, in each region used.

The Step Function state machine is triggered at 00:00 UTC every Monday. It will retrieve the lists of stacks and stack sets for the region, then detect drift on them, creating incidents when it encounters drift.


## Deployment

First make sure that your SSO setup is configured with a default profile giving you AWSAdministratorAccess
to your AWS Organizations administrative account. This is necessary as the AWS cross-account role used 
during deployment only can be assumed from that account.

```console
aws sso login
```

Then type:

```console
./deploy
```
