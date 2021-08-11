from aws_cdk import (
    core,
    aws_lambda as _lambda,
)
import aws_cdk.aws_ec2 as ec2
from aws_cdk import aws_efs as efs


class LambdaStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_name='combined-vpc-no-eips/efs-vpc')

        # https://github.com/mthenw/awesome-layers
        layer = _lambda.LayerVersion.from_layer_version_arn(
            self,
            "requests",
            "arn:aws:lambda:us-east-1:770693421928:layer:Klayers-python38-requests:20"
        )

        # TODO: fix this
        #ap = efs.AccessPoint.from_access_point_id(self, 'ap_id', access_point_id='runtimes-access-point')
        #fs = _lambda.FileSystem.from_efs_access_point(ap, '/mnt/efs')

        # Defines an AWS Lambda resource
        my_lambda = _lambda.Function(
            self, 'HelloHandler',
            runtime=_lambda.Runtime.PYTHON_3_8,
            code=_lambda.Code.asset('cdk_lambda_vpc/lambda'),
            handler='hello.handler',
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[vpc.private_subnets[0], vpc.private_subnets[1]]),
            layers=[
                layer
            ],
            timeout=core.Duration.minutes(5)
        )
