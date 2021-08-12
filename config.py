from aws_cdk import core


env_dev = core.Environment(account="972734064061", region="us-east-1")
#env_prod = core.Environment(...

EC2_KEY_NAME = 'awspersonal'
EC2_WHITELIST_IPS = [
    "82.24.204.83/32",
    "159.48.53.199/32"
]
PREALLOCATED_EIP_LIST = [
            'eipalloc-0967e632d36df641e',
            'eipalloc-09a469e32ca650d30',
            'eipalloc-0bbe02074d59f42f3',
            'eipalloc-0bcad3cccbf9a5ae5',
            'eipalloc-057f9076151e73657'
        ]
N_SUBNETS = 5
