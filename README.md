# DirectConnectMonitor
AWS Direct Connect Monitor

The script deploys a EC2 instance into each AWS VPC that has subnets connect to company's on premise network.

## Deploy DX Monitor Instances
Log into your Master AWS Account.

Distribute `NetworkMonitorRole.yaml` with CloudFormation StackSet.

Run dxteser.py with Python3. The script creates a EC2 instance in target AWS account with connection to your on premise network. The target accounts should be provided in `account.csv` file. The CSV content looks like below.
```
accountid
123456789011
123456789012
```
The script checks existing stacks and output the instances IP to `beacon-ec2.csv`. The CSV file then can be used to create/update PRTG sensors.

## Create or Update PRTG Sensors
Install PrtgAPI from https://github.com/lordmilko/PrtgAPI.

Run `Connect-PrtgServer -Server prtg.contoso.com` to connect to PRTG

Run `add-dxmonitors.ps1` against `beacon-ec2.csv` to create or update the PRTG sensors.

## NetworkMonitorRole.yaml
Stack to provision the Cross Account Role in all target accounts. The role is distributed by CloudFormation StackSet. Change this template to add or revoke permissions.


## ec2.yaml
Stack to provision the beacon EC2 instance. The instace hosts a simple http site and allows for HTTP and ICMP sensor monitoring from PRTG