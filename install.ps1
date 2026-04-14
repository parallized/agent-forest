param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsFromUser
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (Get-Command py -ErrorAction SilentlyContinue) {
    $command = "py"
    $commandArgs = @("-3")
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $command = "python"
    $commandArgs = @()
}
else {
    Write-Error "Python 3 is required to install Agent Forest."
}

$scriptPath = Join-Path $RootDir "scripts\install_agent_forest.py"
& $command @commandArgs $scriptPath @ArgsFromUser
exit $LASTEXITCODE
