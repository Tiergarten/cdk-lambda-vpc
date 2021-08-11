from aws_cdk import core


env_dev = core.Environment(account="972734064061", region="us-east-1")
#env_prod = core.Environment(...

EC2_KEY_NAME = 'awspersonal'
EC2_WHITELIST_IPS = [
    "82.24.204.83/32",
    "159.48.53.199/32"
]
PREALLOCATED_EIP_LIST = [
            'eipalloc-0af1e42ea007b7c4b',
            'eipalloc-07dbb519fedab2d84',
            'eipalloc-07505b09067c6ddb4',
            'eipalloc-06dfba9ebc0610458',
            'eipalloc-08b8608be603b7081'
        ]
N_SUBNETS = 5
