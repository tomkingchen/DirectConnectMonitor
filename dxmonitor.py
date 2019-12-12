import boto3
import csv
import yaml
import time

def get_vpn_gateways(ACCESS_KEY,SECRET_KEY,SESSION_TOKEN):
    ec2_client = boto3.client(
        'ec2',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )
    response = ec2_client.describe_vpn_gateways()
    return response

def get_vpc_subnets(VpcId,ACCESS_KEY,SECRET_KEY,SESSION_TOKEN):
    ec2 = boto3.resource(
        'ec2',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )
    vpc = ec2.Vpc(VpcId)
    subnets = vpc.subnets.all()
    return subnets

def get_private_subnets(ACCESS_KEY,SECRET_KEY,SESSION_TOKEN):
    priv_subnet_list = []
    ec2 = boto3.resource(
        'ec2',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )
    route_tables = ec2.route_tables.all()
    for route_table in route_tables:
        for ra in route_table.routes_attribute:
            if ra.get('DestinationCidrBlock') == '0.0.0.0/0' and ra.get('GatewayId') is None:
                for rs in route_table.associations_attribute:
                    if rs.get('SubnetId') is not None:
                        priv_subnet_list.append(rs.get('SubnetId'))
            else:
                if ra.get('GatewayId') is not None:
                    gateway_name = ra.get('GatewayId')
                    if gateway_name.startswith('vgw-'):
                        for rs in route_table.associations_attribute:
                            if rs.get('SubnetId') is not None and rs.get('SubnetId') not in priv_subnet_list:
                                priv_subnet_list.append(rs.get('SubnetId'))
    return priv_subnet_list

def dxtester_stack_exists(vpc_id,ACCESS_KEY,SECRET_KEY,SESSION_TOKEN):
    cf_client = boto3.client(
        'cloudformation',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )
    stackname = 'directconnect-beacon-instance-'+vpc_id
    try:
        response = cf_client.describe_stacks(StackName=stackname)
    except Exception as e:
        print("[WARNING] Stack",stackname,"does not exist.")
        return False
    return True

def get_dxtester_ip(vpc_id,ACCESS_KEY,SECRET_KEY,SESSION_TOKEN):
    cf_client = boto3.client(
        'cloudformation',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )
    dxtester_ip = ""
    stackname = 'directconnect-beacon-instance-'+vpc_id
    try:
        response = cf_client.describe_stacks(StackName=stackname)
        # Get beacon ec2 instance IP from stack output
        outputs = response["Stacks"][0]["Outputs"]
        for output in outputs:
            if output["OutputKey"] == "EC2IP":
                dxtester_ip = output["OutputValue"]
    except Exception as e:
        print("[ERROR]",str(e))
        return None
    return dxtester_ip


def update_dxtester_stack(vpc_id,subnets,ACCESS_KEY,SECRET_KEY,SESSION_TOKEN):
    cf_client = boto3.client(
        'cloudformation',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )
    stackname = 'directconnect-beacon-instance-'+vpc_id
    sgname = 'sec-http-dxbeacon-'+vpc_id
    servername = 'network-dx-beacon-'+vpc_id
    # Get template body
    with open("./ec2.yaml") as file:
        template_body = file.read()
    try:
        # Check if there are more than 2 private subnets
        if len(subnets) >= 2:
            stackdata = cf_client.update_stack(
                StackName=stackname,
                Parameters=[
                    {
                        "ParameterKey": "VPCId",
                        "ParameterValue": vpc_id
                    },
                    {
                        "ParameterKey": "ServerName",
                        "ParameterValue": servername
                    },
                    {
                        "ParameterKey": "SecurityGroupName",
                        "ParameterValue": sgname
                    },
                    {
                        "ParameterKey": "VPCSubnetId",
                        "ParameterValue": subnets[0]
                    }
                ],
                TemplateBody=template_body
            )
            print("[INFO] Successfully updated cfn stack",stackdata)
    except Exception as e:
        print("[ERROR]",str(e))


def create_dxtester_stack(vpc_id,subnets,ACCESS_KEY,SECRET_KEY,SESSION_TOKEN):
    cf_client = boto3.client(
        'cloudformation',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )
    stackname = 'directconnect-beacon-instance-'+vpc_id
    sgname = 'sec-http-dxbeacon-'+vpc_id
    servername = 'network-dx-beacon-'+vpc_id
    # Get template body
    with open("./ec2.yaml") as file:
        template_body = file.read()
    try:
        # Check if there are more than 2 private subnets
        if len(subnets) >= 2:
            stackdata = cf_client.create_stack(
                StackName=stackname,
                Parameters=[
                    {
                        "ParameterKey": "VPCId",
                        "ParameterValue": vpc_id
                    },
                    {
                        "ParameterKey": "ServerName",
                        "ParameterValue": servername
                    },
                    {
                        "ParameterKey": "SecurityGroupName",
                        "ParameterValue": sgname
                    },
                    {
                        "ParameterKey": "VPCSubnetId",
                        "ParameterValue": subnets[0]
                    }
                ],
                #To load template from S3 use TemplateURL='https://s3.amazonaws.com/bucketName/stackName.yaml', need to setup cross account s3 access beforehand
                TemplateBody=template_body
            )
            print("[INFO] Successfully created cfn stack",stackdata)
    except Exception as e:
        print("[ERROR]",str(e))

# Main function
def main():
    # Empty ec2 csv file
    open('beacon-ec2.csv', 'w').close()
    # Get account list
    account_ids = []
    account_csv_file = csv.DictReader(open("accounts.csv"))
    for row in account_csv_file:
        account_ids.append(row["accountid"])

    for account_id in account_ids:
        role_arn_example_string = "arn:aws:iam::accountidhere:role/NetworkMonitorCrossAccountRole"
        role_arn = role_arn_example_string.replace("accountidhere", account_id)
        # Assume Role in the target account
        sts_connection = boto3.client('sts')
        acct_target = sts_connection.assume_role(
            RoleArn = role_arn,
            RoleSessionName = "cross_acct_session"
        )
        ACCESS_KEY = acct_target['Credentials']['AccessKeyId']
        SECRET_KEY = acct_target['Credentials']['SecretAccessKey']
        SESSION_TOKEN = acct_target['Credentials']['SessionToken']
        print("[INFO] ------ Successfully connected to account",account_id,"------")

        vpc_list = []
        virtual_gateways = get_vpn_gateways(ACCESS_KEY,SECRET_KEY,SESSION_TOKEN)

        # Get VPC Ids associated with the virtual private gateway
        for virtual_gateway in virtual_gateways["VpnGateways"]:
            vgwId = virtual_gateway["VpnGatewayId"]
            vpcAttach = virtual_gateway["VpcAttachments"]
            try:
                vpc_list.append(vpcAttach[0]["VpcId"])
                print("[INFO]",vgwId,"is attached to",vpcAttach[0]["VpcId"])
            except Exception as e:
                print("[WARNING] VGW",vgwId,"is NOT attached to VPC")
        if not vpc_list:
            print("[WARNING] This account has no VPC with VGWs")
        else: 
            print("[INFO] VPCs with VGW:",vpc_list)
            # Get subnets within the VPC and create cfn stack if found
            for vpc in vpc_list:
                subnets = []
                vpc_subnet_list = []
                vpc_private_subnets = []

                subnets = get_vpc_subnets(vpc,ACCESS_KEY,SECRET_KEY,SESSION_TOKEN)
                if not subnets:
                    print("[WARNING]",vpc,"does not have subnets")
                else: 
                    for subnet in subnets:
                        # Make sure there is enough IP for allocation
                        if subnet.available_ip_address_count > 10:
                            vpc_subnet_list.append(subnet.id)
                        else:
                            pass
                    # Get Private subnets from the all subnet list
                    all_priv_subnets = get_private_subnets(ACCESS_KEY,SECRET_KEY,SESSION_TOKEN)
                    if not all_priv_subnets:
                        print("[WARNING] Account does not have any private subnets.")
                    else:
                        # Compare the all subnet list with all private subnet list
                        for privsubnet in all_priv_subnets:
                            if privsubnet in vpc_subnet_list:
                                vpc_private_subnets.append(privsubnet)
                            else:
                                pass
                        if not vpc_private_subnets:
                            print("[WARNING] No internal subnets found for",vpc)
                        else:
                            print("[INFO]",vpc,"has interal subnets:",vpc_private_subnets)
                            if dxtester_stack_exists(vpc,ACCESS_KEY,SECRET_KEY,SESSION_TOKEN):
                                print("[INFO] Cloudformation stack for VPC",vpc,"already exists")
                                update_dxtester_stack(vpc,vpc_private_subnets,ACCESS_KEY,SECRET_KEY,SESSION_TOKEN)
                                # Get private IP of the ec2 instance
                                ec2_ip = get_dxtester_ip(vpc,ACCESS_KEY,SECRET_KEY,SESSION_TOKEN)
                                # Write accountid, vpcid, ec2 ip to csv file
                                print("[INFO] Writing instance IP to file")
                                with open('beacon-ec2.csv','a') as csvfile:
                                    csvwriter = csv.writer(csvfile, delimiter=',')
                                    csvwriter.writerow([account_id,vpc,ec2_ip])
                            else:
                                print("[INFO] Start creating Cloudformation stack for VPC",vpc)
                                create_dxtester_stack(vpc,vpc_private_subnets,ACCESS_KEY,SECRET_KEY,SESSION_TOKEN)
                        
if __name__ == "__main__":
    main()