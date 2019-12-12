$csv = Import-Csv -Path "beacon-ec2.csv" -Header 'AccountID','VpcID','EC2IP'

# Example PRTG Sensor Parameters, RawType is CASE SENSITIVE!!!
$ExampleDevice = Get-Device -Name "example-device"
$ExampleHttpParameter = New-SensorParameters -Device $ExampleDevice -RawType http
$ExampleHttpParameter.httpurl = "http://"
$ExampleHttpParameter.timeout = 10
$ExampleHttpParameter.Interval = "00:00:15"
$ExamplePingParameter = New-SensorParameters -Device $ExampleDevice -RawType ping
$ExamplePingParameter.count = 2
$ExamplePingParameter.Interval = "00:00:15"


ForEach($item in $csv){
    $beaconIP = $($item.EC2IP)
    $beaconName = "dxtester-"+$($item.AccountID)+"-"+$($item.VpcID)
    $BeaconDevice = Get-Device -Name $beaconName
    If ($BeaconDevice -eq $null){
        Get-Group -Name "AWS Direct Connect Monitors" |Add-Device -Name $beaconName -Host $beaconIP
        Get-Device -Name $beaconName | Add-Sensor $ExampleHttpParameter
        Get-Device -Name $beaconName | Add-Sensor $ExamplePingParameter
    }else{
        Write-Host "$beaconName has already been created." -ForegroundColor DarkYellow
        If ($BeaconDevice.Host -ne $beaconIP){
            Write-Host "Update $beaconName IP address" -ForegroundColor Green
            Get-Device -Name $beaconName | Set-ObjectProperty Host $beaconIP
        }
    }
}