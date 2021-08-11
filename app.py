#!/usr/bin/env python3

from aws_cdk import core

from cdk_lambda_vpc.lambda_vpc_stack import LambdaVpcStack
from cdk_lambda_vpc.efs_stack import EFSStack
from cdk_lambda_vpc.combined_stack import CombinedStack
from cdk_lambda_vpc.lambda_stack import LambdaStack

env_dev = core.Environment(account="972734064061", region="us-east-1")

app = core.App()
CombinedStack(app, "combined-vpc", env=env_dev)
LambdaStack(app, 'lambda', env=env_dev)

app.synth()

