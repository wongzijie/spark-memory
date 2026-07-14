[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("go", "reboot", "stop")]
    [string]$Action
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$EnvFile = Join-Path $ProjectRoot ".env"
$ComposeProject = "spark-memory-m1"

function Get-LocalEnvValue {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Test-Path -LiteralPath $EnvFile)) {
        throw "Missing $EnvFile. Copy .env.example to .env and configure it first."
    }
    foreach ($line in Get-Content -LiteralPath $EnvFile) {
        if ($line -match "^$([regex]::Escape($Name))=(.*)$") {
            return $Matches[1]
        }
    }
    throw "Missing $Name in $EnvFile."
}

function Invoke-SparkCompose {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & docker compose -p $ComposeProject @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed with exit code $LASTEXITCODE."
    }
}

function Wait-SparkApi {
    $apiPort = "8000"
    try {
        $configuredPort = Get-LocalEnvValue -Name "API_PORT"
        if (-not [string]::IsNullOrWhiteSpace($configuredPort)) {
            $apiPort = $configuredPort
        }
    } catch {
        # API_PORT is optional; Compose also defaults to 8000.
    }
    $readyUrl = "http://127.0.0.1:$apiPort/health/ready"
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        try {
            $response = Invoke-RestMethod -Uri $readyUrl -TimeoutSec 2
            if ($response.status -eq "ready") {
                return
            }
        } catch {
            if ($attempt -eq 60) {
                throw "Spark Memory API did not become ready at $readyUrl."
            }
        }
        Start-Sleep -Seconds 1
    }
}

function Set-SparkAdmin {
    $email = Get-LocalEnvValue -Name "SPARK_ADMIN_EMAIL"
    $password = Get-LocalEnvValue -Name "SPARK_ADMIN_PASSWORD"
    $password | & docker compose -p $ComposeProject exec -T api `
        python -m app.cli configure-admin --email $email --password-stdin
    if ($LASTEXITCODE -ne 0) {
        throw "Could not configure the local Spark Memory administrator."
    }
}

$previousLocation = Get-Location
try {
    Set-Location -LiteralPath $ProjectRoot
    switch ($Action) {
        "go" {
            Invoke-SparkCompose -Arguments @("up", "-d", "--build")
            Wait-SparkApi
            Set-SparkAdmin
            Write-Host "Spark Memory is running: http://localhost:3000"
        }
        "reboot" {
            Invoke-SparkCompose -Arguments @("up", "-d", "--build", "--force-recreate")
            Wait-SparkApi
            Set-SparkAdmin
            Write-Host "Spark Memory restarted: http://localhost:3000"
        }
        "stop" {
            Invoke-SparkCompose -Arguments @("down")
            Write-Host "Spark Memory stopped. Local database volumes were preserved."
        }
    }
} finally {
    Set-Location -LiteralPath $previousLocation
}
