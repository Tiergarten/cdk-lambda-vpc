
# Welcome to your CDK Python project!

## Usage
`pip install -r requirements.txt`  
`cdk deploy combined-vpc`

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

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