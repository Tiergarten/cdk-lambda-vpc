#!/usr/bin/env python3

from aws_cdk import core
from cdk_lambda_vpc.combined_stack import CombinedStack
from cdk_lambda_vpc.lambda_stack import LambdaStack

import config

app = core.App()

CombinedStack(app, "combined-vpc",
              ec2_whitelist_ips=config.EC2_WHITELIST_IPS,
              ec2_key_name=config.EC2_KEY_NAME,
              eip_list=config.PREALLOCATED_EIP_LIST,
              env=config.env_dev)

CombinedStack(app, "combined-vpc-no-eips",
              ec2_whitelist_ips=config.EC2_WHITELIST_IPS,
              ec2_key_name=config.EC2_KEY_NAME,
              env=config.env_dev)

LambdaStack(app, 'lambda', env=config.env_dev)

app.synth()

