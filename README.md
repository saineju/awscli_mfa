# Get MFA enabled credentials for AWS cli

If you have properly enforced MFA on your account, it will require MFA also on cli access. An example of such role would be something like this:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowListingUsersAndMfaVirtualDevices",
            "Effect": "Allow",
            "Action": [
                "iam:ListUsers",
                "iam:ListVirtualMFADevices"
            ]
            "Resource": "*"
        },
        {
            "Sid": "AllowlUsersToListTheirMfaDevices",
            "Effect": "Allow",
            "Action": "iam:ListMFADevices",
            "Resource": [
                "arn:aws:iam::*:mfa/*",
                "arn:aws:iam::*:user/${aws:username}"
            ]
        },
        {
            "Sid": "AllowUsersToManageTheirOwnMfa",
            "Effect": "Allow",
            "Action": [
                "iam:CreateVirtualMFADevice",
                "iam:DeleteVirtualMFADevice",
                "iam:EnableMFADevice",
                "iam:ResyncMFADevice"
            ],
            "Resource": [
                "arn:aws:iam::*:mfa:/${aws:username}",
                "arn:aws:iam::*user:/${aws:username}"
            ]
        },
        {
            "Sid": "AllowMfaDeactivateOnlyWhenUsingMfa",
            "Effect": "Allow",
            "Action": "iam:DeactivateMFADevice",
            "Resource": [
                "arn:aws:iam::*:mfa/${aws:username}",
                "arn:aws:iam::*:user/${aws:username}"
            ],
            "Condition": {
                "Bool": {
                    "aws:MultiFactorAuthPresent": "true"
                }
            }
        },
        {
            "Sid": "BlocMostActionsWithoutMfaToken",
            "Effect": "Deny",
            "NotAction": [
                "iam:CreateVirtualMFADevice",
                "iam:EnableMFADevice",
                "iam:ListMFADevices",
                "iam:ListUsers",
                "iam:ListVirtualMFADevices",
                "iam:ResyncMFADefice",
                "iam:ChangePassword"
            ],
            "Resource": "*",
            "Condition": {
                "BoolIfExists": {
                    "aws:MultiFactorAuthPresent": "false"
                }
            }
        }
    ]
}
```

The above policy limits user actions to enabling MFA device and changing their password when they log in without MFA token. Note that it is important to not allow users to deactivate MFA without
MFA, as this would allow possible attacker to just deactivate the MFA device if they gain access to the account.

**DISCLAIMER**: If you want to test the above policy, please do so with one account only, as the policy might contain some errors. Naturally after verifying that it does work properly you should
activate that to at least administrative level users.


## MFA helper script
While you can enable MFA with command

```
aws sts get-session-token --serial-number arn-of-the-mfa-device --token-code code-from-token
```

I found that to be quite cumbersome when using several profiles daily, so I decided to write a small wrapper script with which I can easily get the credentials to `~/.aws/credentials` -file.

### Usage
Make sure that you have the required python modules installed:

```
pip3 install -r requirements.txt
```

You just run the script with parameter `-p <profile_name>` to get MFA token for `<profile_name>`. The script asks for OTP token and creates a new profile to your credentials file that is by default
named <profile_name>-mfa, eg. if you have profile `prod` the mfa enabled profile would be `prod-mfa`. If the mfa enabled profile exists already, the script will update details there. Note that the 
script also supports the environment variable `AWS_PROFILE`, but the `-p` switch will have preceedence over this. If neither is present, the script will use `default` -profile.

The script writes the credential details, but also the timestamp indicating when the token expires, so if you run the script again before the expiration, it will not fetch new token. The script also
supports custom location for credentials file, adding the OTP token as command line parameter and assigning custon name for the mfa enabled profile.

Full script help:
```
Usage: mfa_credentials.py [-h] [-p [PROFILE]] [-o [OTP]] [-c [CREDENTIALS]] [-n [NAME]]

Get temporary awscli credentials with MFA

optional arguments:
  -h, --help            show this help message and exit
  -p [PROFILE], --profile [PROFILE]
                        Which AWS profile do you want to use for deploying (defaults to "default")
  -o [OTP], --otp [OTP]
                        OTP token
  -c [CREDENTIALS], --credentials [CREDENTIALS]
                        AWS credentials configuration file
  -n [NAME], --name [NAME]
                        Name for profile to use for temporary credentials, (defaults to <profile>-mfa e.g. default-mfa)
```
