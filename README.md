
# CDK Patterns 

## Overview

CDK Sandbox / snippets - not for production use

## Permissions
from: https://alexanderzeitler.com/articles/minimal-iam-permission-for-aws-cdk-deployment/  
"grant full access for all resources and their actions if the action has been triggered by CloudFormation (or CDK)"  
  
I've modified this to include describe:ec2 perms to identify vpc info
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "cloudformation:*"
            ],
            "Resource": "*",
            "Effect": "Allow"
        },
        {
            "Condition": {
                "ForAnyValue:StringEquals": {
                    "aws:CalledVia": [
                        "cloudformation.amazonaws.com"
                    ]
                }
            },
            "Action": "*",
            "Resource": "*",
            "Effect": "Allow"
        },
        {
            "Action": "s3:*",
            "Resource": "arn:aws:s3:::cdktoolkit-stagingbucket-*",
            "Effect": "Allow"
        },
        {
            "Action": "ec2:Describe*",
            "Resource": "*",
            "Effect": "Allow"
        },
        {
            "Action": "ec2:describe*",
            "Resource": "*",
            "Effect": "Allow"
        }
    ]
}
```
