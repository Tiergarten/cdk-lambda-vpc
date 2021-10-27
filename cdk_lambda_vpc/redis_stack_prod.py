from aws_cdk import core
import aws_cdk.aws_ec2 as ec2
from aws_cdk.aws_elasticache import CfnReplicationGroup, CfnSubnetGroup
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_sns as sns
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm
from aws_cdk import aws_autoscaling, aws_autoscalingplans, aws_applicationautoscaling, aws_cloudwatch

EC2_KEY_NAME = 'awspersonal'
EC2_WHITELIST_IPS = [
    "82.24.204.83/32",
    "159.48.53.199/32"
]


class RedisStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id='vpc-0981d256693b6ff86')

        self.create_redis()
        self.create_mgmt_ec2()

    def create_redis(self):
        private_subnets_ids = [ps.subnet_id for ps in self.vpc.isolated_subnets]

        # create a new security group
        sec_group = ec2.SecurityGroup(
            self,
            "sec-group-redis",
            vpc=self.vpc,
            allow_all_outbound=False,
        )

        sec_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            description="Allow Redis inbound",
            connection=ec2.Port.tcp(6379)
        )

        cache_subnet_group = CfnSubnetGroup(
            scope=self,
            id=f"redis_cache_subnet_group",
            subnet_ids=private_subnets_ids,
            description="subnet group for redis",
        )

        self.maintenance_topic = sns.Topic(self, id='maintenance_topic', topic_name='maintenance_topic')

        self.redis = CfnReplicationGroup(
            self,
            'redis-cluster',
            replication_group_id='hcache',
            replication_group_description='Hot cache for recent data',
            engine='redis',
            replicas_per_node_group=0,
            cache_node_type='cache.r5.large',
            num_node_groups=2,
            cache_subnet_group_name=cache_subnet_group.ref,
            security_group_ids=[sec_group.security_group_id],
            notification_topic_arn=self.maintenance_topic.topic_arn
        )

        connection_string = f'{self.redis.attr_configuration_end_point_address}:{self.redis.attr_configuration_end_point_port}'
        aws_ssm.StringParameter(
            self,
            'cluster-host-id',
            parameter_name='/hcache/connection_string',
            string_value=connection_string
        )

        aws_ssm.StringParameter(
            self,
            'cluster-evict-trades',
            parameter_name='/hcache/evict_trades_after_minutes',
            string_value='30'
        )

        aws_ssm.StringParameter(
            self,
            'cluster-evict-orders',
            parameter_name='/hcache/evict_orderbooks_after_minutes',
            string_value='5'
        )

        # aws application-autoscaling register-scalable-target --service-namespace elasticache --resource-id replication-group/hcache --scalable-dimension elasticache:replication-group:NodeGroups --min-capacity 1 --max-capacity 20


    def create_mgmt_ec2(self):
        instance_name = "efs-mgmt-box"
        instance_type = "r4.xlarge"
        ec2_ami_name = "amzn2-ami-hvm-2.0.20200520.1-x86_64-gp2"

        # create a new security group
        sec_group = ec2.SecurityGroup(
            self,
            "sec-group-allow-ssh",
            vpc=self.vpc,
            allow_all_outbound=True,
        )

        # add a new ingress rule to allow port 22 to internal hosts
        for ip in EC2_WHITELIST_IPS:
            sec_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(ip),
                description="Allow SSH connection",
                connection=ec2.Port.tcp(22)
            )

        # define a new ec2 instance
        ec2_instance = ec2.Instance(
            self,
            "ec2-instance",
            instance_name=instance_name,
            instance_type=ec2.InstanceType(instance_type),
            machine_image=ec2.MachineImage().lookup(name=ec2_ami_name),
            vpc=self.vpc,
            security_group=sec_group,
            key_name=EC2_KEY_NAME,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType('PUBLIC'))
        )

