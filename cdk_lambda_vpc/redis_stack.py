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

        self.az = 'us-east-1b'
        self.vpc_cidr_start = '10.2.0.0'
        self.vpc_cidr = f'{self.vpc_cidr_start}/16'

        # create VPC
        # If you run this without subnet_configuration=[] it creates N public subnets and N isolated subnets
        # where N is availibility zones (max_azs param)
        self.vpc = ec2.Vpc(
            self, 'my-vpc', cidr=self.vpc_cidr, nat_gateways=0, enable_dns_support=True, max_azs=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name='public-subnet',
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=26
                ),
                ec2.SubnetConfiguration(
                    name='redis-subnet',
                    subnet_type=ec2.SubnetType.ISOLATED,
                    cidr_mask=26
                )
            ],
            enable_dns_hostnames=True)

        self.subnet_id_to_subnet_map = {}
        self.route_table_id_to_route_table_map = {}
        self.security_group_id_to_group_map = {}
        self.instance_id_to_instance_map = {}

        self.create_mgmt_ec2()
        self.create_redis()

    def create_autoscaler_lambda_role(self):
        autoscaler_role = iam.Role(self, 'autoscaler-role', role_name='autoscaler-role',
                 assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'))

        elasticache_full_access_policy = iam.ManagedPolicy.from_aws_managed_policy_name('AmazonElastiCacheFullAccess')
        lambda_policy = iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole')

        autoscaler_role.add_managed_policy(elasticache_full_access_policy)
        autoscaler_role.add_managed_policy(lambda_policy)

    def create_autoscale_sns(self):
        """
        https://axemind.medium.com/aws-cdk-python-lambda-cloudwatch-alarm-1dcc93bdbc8d

        https://stackoverflow.com/a/63178997

        """
        self.capacity_topic = sns.Topic(self, id='capacity_alarm_topic', topic_name='capacity_alarm_topic')

        """
        Percentage of the memory available for the cluster that is in use excluding memory used for overhead and COB. 
        This is calculated using used_memory-mem_not_counted_for_evict/maxmemory from Redis INFO.
        """
        alarm_scale_up = cw.Alarm(self,
                                 'hcache_capacity_alarm_scale_up',
                                 alarm_name='hcache_capacity_alarm_scale_up',
                                 metric=cw.Metric(
                                    namespace="AWS/ElastiCache",
                                     metric_name="DatabaseMemoryUsageCountedForEvictPercentage",
                                     dimensions={
                                         "ReplicationGroupId": "hcache",
                                     },
                                     period=core.Duration.minutes(5),
                                     statistic="Average"
                                 ),
                                 evaluation_periods=1,
                                 threshold=70,
                                 comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD
        )

        alarm_scale_up.add_alarm_action(cw_actions.SnsAction(self.capacity_topic))

        alarm_scale_down = cw.Alarm(self,
                                  'hcache_capacity_alarm_scale_down',
                                  alarm_name='hcache_capacity_alarm_scale_down',
                                  metric=cw.Metric(
                                      namespace="AWS/ElastiCache",
                                      metric_name="DatabaseMemoryUsageCountedForEvictPercentage",
                                      dimensions={
                                          "ReplicationGroupId": "hcache",
                                      },
                                      period=core.Duration.minutes(5),
                                      statistic="Average"
                                  ),
                                  evaluation_periods=1,
                                  threshold=10,
                                  comparison_operator=cw.ComparisonOperator.LESS_THAN_THRESHOLD
                                  )

        alarm_scale_down.add_alarm_action(cw_actions.SnsAction(self.capacity_topic))

    def create_redis(self):
        private_subnets_ids = [ps.subnet_id for ps in self.vpc.isolated_subnets]
        # Forcing these into the same subnet so we stay in the same AZ
        redis_stack.py = [private_subnets_ids[0]]

        # create a new security group
        sec_group = ec2.SecurityGroup(
            self,
            "sec-group-redis",
            vpc=self.vpc,
            allow_all_outbound=False,
        )

        sec_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc_cidr),
            description="Allow Redis inbound",
            connection=ec2.Port.tcp(6379)
        )

        cache_subnet_group = CfnSubnetGroup(
            scope=self,
            id=f"redis_cache_subnet_group",
            subnet_ids=private_subnets_ids,  # TODO: add list of subnet ids here
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
        """
        st = aws_applicationautoscaling.CfnScalableTarget(
            self,
            'hcache-st',
            min_capacity=1,
            max_capacity=15,
            resource_id='replication-group/hcache',
            scalable_dimension='elasticache:replication-group:NodeGroups',
            service_namespace='elasticache',
            role_arn='arn:aws:iam::972734064061:role/aws-service-role/elasticache.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_ElastiCacheRG'
        )
        """


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

        """
        To be run on box:
        wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
        sh Miniconda3-latest-Linux-x86_64.sh
        
        sudo yum install -y git htop
        sudo yum group install -y "Development Tools"
        sudo yum install -y postgresql-devel.x86_64
        
        git clone https://github.com/bmoscon/cryptofeed.git
        cd cryptofeed
        git checkout e922af60530df4b145238bcbbfad5358ddf8be4b
        git apply ~/kirby/cryptofeed.patch
        pip install -r requirements.txt
        pip install msgpack lz4 redis-py-cluster
        python setup.py develop
        
        python -i
        > c = RedisCluster(host='rerg3oy5yr6dnkz.cb4jbc.clustercfg.use1.cache.amazonaws.com', 
            port=6379, skip_full_coverage_check=True)
            
        # TODO: What are the implications of skipping 'coverage check' ?
        """


