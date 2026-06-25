# PowerShell launcher for Windows native agent hooks without Git Bash.
# Claude Code manual setup can merge commands from hooks/hooks.windows.example.json.
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginRoot = Split-Path -Parent $Root
$DataDir = if ($env:POWERMEM_DATA_DIR) { $env:POWERMEM_DATA_DIR } else { Join-Path $HOME ".powermem" }

function Import-PowerMemEnvFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }
        if ($line -match '^(?:export\s+)?([^=\s]+)=(.*)$') {
            $name = $matches[1]
            $value = $matches[2].Trim()
            if (
                ($value.StartsWith('"') -and $value.EndsWith('"')) -or
                ($value.StartsWith("'") -and $value.EndsWith("'"))
            ) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

Import-PowerMemEnvFile (Join-Path $DataDir "runtime.env")
Import-PowerMemEnvFile (Join-Path $PluginRoot "config\runtime.env")

$arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'amd64' }
$exe = Join-Path $Root "bin\powermem-hook-windows-$arch.exe"
if (-not (Test-Path $exe)) {
    $exe = Join-Path $Root "bin\powermem-hook-windows-amd64.exe"
}
if (-not (Test-Path $exe)) {
    exit 0
}
& $exe @args
exit $LASTEXITCODE
