$configPath = 'HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Configuration'
$out = @()
Get-ChildItem $configPath -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    $props = $_ | Get-ItemProperty -ErrorAction SilentlyContinue
    if ($props.PSObject.Properties.Name -contains 'Scaling') {
        $out += "$($_.Name) => Scaling=$($props.Scaling)"
    }
}
$out | Out-File "C:\Users\chemg0d\Desktop\nv_scaling.txt" -Encoding UTF8
Write-Host "Done. Found $($out.Count) keys."
Write-Host ($out -join "`n")
pause
