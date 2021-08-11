#!/usr/bin/env python3

from aws_cdk import core

from cdk_lambda_vpc.lambda_vpc_stack import LambdaVpcStack
from cdk_lambda_vpc.efs_stack import EFSStack

env_dev = core.Environment(account="972734064061", region="us-east-1")

app = core.App()
LambdaVpcStack(app, "lambda-vpc", env=env_dev)
EFSStack(app, "efs-vpc", env=env_dev)

app.synth()

