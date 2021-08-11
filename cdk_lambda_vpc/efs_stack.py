from aws_cdk import core
import aws_cdk.aws_ec2 as ec2
from aws_cdk import aws_efs as efs

EC2_KEY_NAME = 'awspersonal'
EC2_WHITELIST_IPS = [
    "82.24.204.83/32",
    "159.48.53.199/32"
]


class EFSStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.az = 'us-east-1b'
        self.vpc_cidr_start = '10.2.0.0'
        self.vpc_cidr = f'{self.vpc_cidr_start}/16'

        # create VPC
        # If you run this without subnet_configuration=[] it creates 2 public subnets and 2 isolated subnets
        self.vpc = ec2.Vpc(
            self, 'efs-vpc', cidr=self.vpc_cidr, nat_gateways=0, enable_dns_support=True, subnet_configuration=[
                ec2.SubnetConfiguration(
                    name='public-subnet',
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=26
                ),
                ec2.SubnetConfiguration(
                    name='efs-subnet',
                    subnet_type=ec2.SubnetType.ISOLATED,
                    cidr_mask=26
                )
            ],
            enable_dns_hostnames=True)

        self.subnet_id_to_subnet_map = {}
        self.route_table_id_to_route_table_map = {}
        self.security_group_id_to_group_map = {}
        self.instance_id_to_instance_map = {}

        self.create_efs(self.vpc)
        self.create_mgmt_ec2()

    def create_efs(self, vpc, id=1):
        # Create Security Group to connect to EFS
        self.efs_sg = ec2.SecurityGroup(
            self,
            id="efsSecurityGroup",
            vpc=vpc,
            security_group_name=f"efs_sg_{id}",
            description="Security Group to connect to EFS from the VPC"
        )

        self.efs_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(2049),
            description="Allow EC2 instances within the same VPC to connect to EFS"
        )

        self.efs_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4('10.0.0.0/16'),
            connection=ec2.Port.tcp(2049),
            description="Allow EC2 instances within the lambda VPC to connect to EFS"
        )

        # Create the EFS filesystem
        self.efs_share = efs.FileSystem(
            self,
            "elasticFileSystem",
            file_system_name=f"high-performance-storage",
            vpc=vpc,
            security_group=self.efs_sg,
            encrypted=False,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            removal_policy=core.RemovalPolicy.DESTROY
        )

        # Create EFS ACL
        efs_acl = efs.Acl(
            owner_gid="1000",
            owner_uid="1000",
            permissions="0750"
        )

        # Create EFS POSIX user
        efs_user = efs.PosixUser(
            gid="1000",
            uid="1000"
        )

        # Create EFS access point
        self.efs_ap = efs.AccessPoint(
            self,
            "efsDefaultAccessPoint",
            path=f"/",
            file_system=self.efs_share,
            posix_user=efs_user,
            create_acl=efs_acl
        )

    def create_mgmt_ec2(self):
        instance_name = "efs-mgmt-box"
        instance_type = "t2.micro"
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
        
        sudo yum install -y amazon-efs-utils
        mkdir efs/ && sudo mount -t efs fs-c590c371 efs/
        """
