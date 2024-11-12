# Import required modules
Import-Module Posh-SSH

# Prompt user for switch IP address and credentials
$SwitchIP = Read-Host "Enter IP Address of Switch"
$Credential = Get-Credential -Message "Enter Credentials"

# Define variables
$commandToSend = "abc fhjkdshjkf"

# Create SSH session to switch
$sshSession = New-SSHSession -ComputerName $SwitchIP -Credential $Credential

# Send the command to each port
1..48 | ForEach-Object {
    $port = $_
    $configCommands = @(
        "enable",
        "configure terminal",
        "interface fastEthernet0/$port",
        $commandToSend,
        "end",
            )

    # Send each command to the switch
    foreach ($cmd in $configCommands) {
        $response = Invoke-SSHCommand -SSHSession $sshSession -Command $cmd
        Write-Output $response.Output
    }

    # Wait 5 seconds before proceeding to the next port
    Start-Sleep -Seconds 5
}

# Close the SSH session
Remove-SSHSession -SSHSession $sshSession
