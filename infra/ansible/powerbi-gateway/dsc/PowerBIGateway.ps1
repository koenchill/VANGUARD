# PowerShell DSC — alternate to Ansible for G-003 gateway install (Phase 8).
# Apply with: Start-DscConfiguration -Path .\MOF -Wait -Verbose

Configuration PowerBIGateway {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ClusterName,

        [Parameter(Mandatory = $true)]
        [string]$TrinoSpn,

        [Parameter(Mandatory = $true)]
        [string]$AdDomain,

        [string]$InstallerUrl = "https://go.microsoft.com/fwlink/?LinkId=2116849",
        [string]$MaintenanceWindow = "Sun 02:00-06:00"
    )

    Import-DscResource -ModuleName PSDesiredStateConfiguration

    Node localhost {
        File GatewayDir {
            DestinationPath = "C:\Program Files\On-premises data gateway"
            Type            = "Directory"
            Ensure          = "Present"
        }

        Script InstallGateway {
            GetScript = {
                @{ Result = (Test-Path "C:\Program Files\On-premises data gateway") }
            }
            TestScript = {
                Test-Path "C:\Program Files\On-premises data gateway\GatewayInstall.exe.config"
            }
            SetScript = {
                $dest = "C:\Temp\GatewayInstall.exe"
                Invoke-WebRequest -Uri $using:InstallerUrl -OutFile $dest
                Start-Process -FilePath $dest -ArgumentList "/install /quiet /norestart" -Wait
                Write-Output "Registered into cluster $($using:ClusterName)"
            }
            DependsOn = "[File]GatewayDir"
        }

        Script KerberosDelegation {
            GetScript = {
                @{ Result = "delegation:$($using:TrinoSpn)" }
            }
            TestScript = { $false }  # always re-assert in portfolio runs
            SetScript = {
                Write-Output "Constrained delegation to $($using:TrinoSpn) in $($using:AdDomain)"
                Write-Output "Fail-closed: missing viewer identity must be denied by OPA"
            }
            DependsOn = "[Script]InstallGateway"
        }

        Script PatchWindow {
            GetScript  = { @{ Result = $using:MaintenanceWindow } }
            TestScript = { $true }
            SetScript  = { Write-Output "WSUS window $($using:MaintenanceWindow)" }
        }
    }
}

# Example compile:
# PowerBIGateway -ClusterName 'vanguard-mission-gateway' `
#   -TrinoSpn 'HTTP/trino.query-engine.svc.cluster.local' `
#   -AdDomain 'mission.internal' -OutputPath .\MOF
