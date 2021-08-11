"""
Build a new VPC:
 - lambda-vpc: 10.1.0.0/16 (10.0.0.0, 10.0.255.255) => 65536 hosts

Create a public subnet/24 => 255 hosts with a route to an internet gateway

Create N private subnets/26 => 64 hosts each
 - Create a NAT gateway in public subnet for each one
 - Create route from subnet -> Nat gateway

Based on https://github.com/abkunal/custom-vpc-cdk
"""


from aws_cdk import core
from aws_cdk.aws_ec2 import Vpc, CfnRouteTable, RouterType, CfnRoute, CfnInternetGateway, CfnVPCGatewayAttachment, \
    CfnSubnet, CfnSubnetRouteTableAssociation, CfnSecurityGroup, CfnInstance

from netaddr import IPNetwork
from aws_cdk.aws_ec2 import RouterType, CfnSecurityGroup, CfnNatGateway, CfnEIP


PREALLOCATED_EIP_LIST = [
            'eipalloc-0af1e42ea007b7c4b',
            'eipalloc-07dbb519fedab2d84',
            'eipalloc-07505b09067c6ddb4',
            'eipalloc-06dfba9ebc0610458',
            'eipalloc-08b8608be603b7081'
        ]

N_SUBNETS = 5


class LambdaVpcStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.az = 'us-east-1b'
        self.vpc_cidr_start = '10.1.0.0'
        self.vpc_cidr = f'{self.vpc_cidr_start}/16'

        # create VPC
        self.vpc = Vpc(
            self, 'lambda-vpc', cidr=self.vpc_cidr, nat_gateways=0, subnet_configuration=[], enable_dns_support=True,
            enable_dns_hostnames=True,
        )

        self.internet_gateway = self.attach_internet_gateway()

        self.subnet_id_to_subnet_map = {}
        self.route_table_id_to_route_table_map = {}
        self.security_group_id_to_group_map = {}
        self.instance_id_to_instance_map = {}

        self.pre_allocated_eips = PREALLOCATED_EIP_LIST

        self.private_start_cidr = None
        self.public_subnet_id = self.create_public_subnet()
        for i in range(0, N_SUBNETS):
            self.create_lambda_access_route(i)

    def create_public_subnet(self):
        """
        Create a public subnet with a route to the internet gateway
        """
        # Create public subnet
        subnet_id = f'lambda_vpc_public'
        cidr = f'{self.vpc_cidr_start}/24'

        # Set starting cidr range for private subnets
        self.private_start_cidr = str(IPNetwork(cidr).next()).replace('/24', '/26')

        self.subnet_id_to_subnet_map[subnet_id] = CfnSubnet(
            self, subnet_id, vpc_id=self.vpc.vpc_id, cidr_block=cidr,
            availability_zone=self.az, tags=[{'key': 'Name', 'value': subnet_id}],
            map_public_ip_on_launch=True
        )

        # Create route table
        route_table_id = f'route_lambda_vpc_public'
        self.route_table_id_to_route_table_map[route_table_id] = CfnRouteTable(
            self, route_table_id, vpc_id=self.vpc.vpc_id, tags=[{'key': 'Name', 'value': route_table_id}]
        )

        # Add route to table
        route_params = {
            'destination_cidr_block': '0.0.0.0/0',
            'gateway_id': self.internet_gateway.ref,
            'route_table_id': self.route_table_id_to_route_table_map[route_table_id].ref
        }
        CfnRoute(self, f'{route_table_id}-route', **route_params)

        # Assign route to subnet
        CfnSubnetRouteTableAssociation(
            self, f'{subnet_id}-{route_table_id}', subnet_id=self.subnet_id_to_subnet_map[subnet_id].ref,
            route_table_id=self.route_table_id_to_route_table_map[route_table_id].ref
        )
        return subnet_id

    def create_lambda_access_route(self, n):
        """
        Create NAT gateway in public subnet using EIP from self.pre_allocated_eips[n]
        Create private subnet with route to NAT Gateway

        """
        # Create NAT Gateway
        nat_gateway_id = f'lambda_vpc_natgw_{n}'
        nat_gateway_instance = CfnNatGateway(self, id=nat_gateway_id,
                                             subnet_id=self.subnet_id_to_subnet_map[self.public_subnet_id].ref,
                                             allocation_id=self.pre_allocated_eips[n])

        # Create private subnet
        subnet_id = f'lambda_vpc_private_{n}'
        cidr = str(IPNetwork(self.private_start_cidr).next(n))
        self.subnet_id_to_subnet_map[subnet_id] = CfnSubnet(
            self, subnet_id, vpc_id=self.vpc.vpc_id, cidr_block=cidr,
            availability_zone=self.az, tags=[{'key': 'Name', 'value': subnet_id}],
            map_public_ip_on_launch=False
        )

        # Create route table
        route_table_id = f'route_lambda_vpc_private_{n}'
        self.route_table_id_to_route_table_map[route_table_id] = CfnRouteTable(
            self, route_table_id, vpc_id=self.vpc.vpc_id, tags=[{'key': 'Name', 'value': route_table_id}]
        )

        # Add route to table
        route_params = {
            'destination_cidr_block': '0.0.0.0/0',
            'nat_gateway_id': nat_gateway_instance.ref,
            'route_table_id': self.route_table_id_to_route_table_map[route_table_id].ref,
        }
        CfnRoute(self, f'{route_table_id}-route-{n}', **route_params)

        # Assign route to subnet
        CfnSubnetRouteTableAssociation(
            self, f'{subnet_id}-{route_table_id}', subnet_id=self.subnet_id_to_subnet_map[subnet_id].ref,
            route_table_id=self.route_table_id_to_route_table_map[route_table_id].ref
        )

    def attach_internet_gateway(self) -> CfnInternetGateway:
        """ Create and attach internet gateway to the VPC """
        internet_gateway = CfnInternetGateway(self, 'internet-gateway')
        CfnVPCGatewayAttachment(self, 'internet-gateway-attachment', vpc_id=self.vpc.vpc_id,
                                internet_gateway_id=internet_gateway.ref)

        return internet_gateway


