param(
    [Parameter(Mandatory = $true)]
    [string]$ApplicationPath
)

$ErrorActionPreference = 'Stop'

if (!(Test-Path -LiteralPath $ApplicationPath -PathType Leaf)) {
    throw "Application executable not found: $ApplicationPath"
}
if (!(Get-Command winapp -ErrorAction SilentlyContinue)) {
    throw 'WinApp CLI is required. Install Microsoft.WinAppCli before running this check.'
}

# Use Qt's native Windows platform plugin so the app exposes a real HWND/UIA tree.
$env:QT_QPA_PLATFORM = 'windows'
$ResolvedPath = (Resolve-Path -LiteralPath $ApplicationPath).Path
$AppProcess = Start-Process -FilePath $ResolvedPath `
    -WorkingDirectory (Split-Path -Parent $ResolvedPath) `
    -PassThru

try {
    $RequiredNames = @(
        'Arduino board type',
        'Arduino serial port',
        'Selected PIC target',
        'Connect programmer',
        'Open HEX file',
        'Program PIC from selected HEX file',
        'Operation status'
    )

    # Give the packaged app one bounded startup window, then check every required
    # control by its accessible name using the skill's cross-framework UIA search.
    $Deadline = (Get-Date).AddSeconds(30)
    $Ready = $false
    do {
        $Output = (& winapp ui search $RequiredNames[0] -a "$($AppProcess.Id)" 2>&1 | Out-String)
        $ExitCode = $LASTEXITCODE
        if ($ExitCode -eq 0 -and $Output -match [regex]::Escape($RequiredNames[0])) {
            $Ready = $true
            break
        }
        Start-Sleep -Milliseconds 750
    } while ((Get-Date) -lt $Deadline -and !$AppProcess.HasExited)
    if (!$Ready) {
        throw "The app did not expose its main UIA tree. Last result: $Output"
    }
    Write-Output "UIA found: $($RequiredNames[0])"

    foreach ($Name in ($RequiredNames | Select-Object -Skip 1)) {
        $Output = (& winapp ui search $Name -a "$($AppProcess.Id)" 2>&1 | Out-String)
        if ($LASTEXITCODE -ne 0 -or $Output -notmatch [regex]::Escape($Name)) {
            throw "UI Automation could not find accessible control '$Name'. Result: $Output"
        }
        Write-Output "UIA found: $Name"
    }
}
finally {
    if (!$AppProcess.HasExited) {
        Stop-Process -Id $AppProcess.Id -Force -ErrorAction SilentlyContinue
        $AppProcess.WaitForExit(5000)
    }
}
