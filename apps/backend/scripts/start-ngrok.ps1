# Expose local Django (port 8001) for Flutterwave webhooks.
#
# 1. Add to apps/backend/.env:
#      NGROK_AUTHTOKEN=<from https://dashboard.ngrok.com/get-started/your-authtoken>
#      NGROK_DOMAIN=choosy-embark-grapple.ngrok-free.dev   # optional reserved domain
#      FLUTTERWAVE_WEBHOOK_SECRET=efs-sandbox-wh-2026
# 2. Run: .\scripts\start-ngrok.ps1
# 3. Open http://127.0.0.1:4040 and copy the HTTPS forwarding URL

$ErrorActionPreference = "Stop"
$BackendRoot = Split-Path $PSScriptRoot -Parent
$EnvFile = Join-Path $BackendRoot ".env"
$Port = if ($env:NGROK_PORT) { $env:NGROK_PORT } else { "8001" }

function Read-DotEnvValue([string]$Name) {
    if (-not (Test-Path $EnvFile)) { return $null }
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match "^\s*#") { continue }
        if ($line -match "^\s*$Name\s*=\s*(.+)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

function Read-DotEnvKeys {
    if (-not (Test-Path $EnvFile)) { return @() }
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match "^\s*([A-Z0-9_]+)\s*=") { $Matches[1] }
    }
}

$token = $env:NGROK_AUTHTOKEN
if (-not $token) { $token = Read-DotEnvValue "NGROK_AUTHTOKEN" }
if (-not $token) { $token = Read-DotEnvValue "GROK_AUTHTOKEN" }

$placeholder = (-not $token) -or ($token -match "your_token|dashboard\.ngrok\.com")
if ($placeholder) {
    Write-Host ""
    Write-Host "NGROK_AUTHTOKEN is missing or still a placeholder in apps/backend/.env" -ForegroundColor Red
    Write-Host ""
    Write-Host "Found keys in .env:" (Read-DotEnvKeys -join ", ")
    Write-Host ""
    Write-Host "Add your REAL token (starts with 2, about 40+ chars):"
    Write-Host "  NGROK_AUTHTOKEN=2xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    Write-Host ""
    Write-Host "Get it from: https://dashboard.ngrok.com/get-started/your-authtoken"
    Write-Host ""
    exit 1
}

$ngrok = Join-Path $env:APPDATA "npm\node_modules\ngrok\bin\ngrok.exe"
if (-not (Test-Path $ngrok)) { $ngrok = "ngrok" }

Write-Host "Configuring ngrok authtoken..."
& $ngrok config add-authtoken $token | Out-Null

$webhookSecret = Read-DotEnvValue "FLUTTERWAVE_WEBHOOK_SECRET"
$ngrokDomain = $env:NGROK_DOMAIN
if (-not $ngrokDomain) { $ngrokDomain = Read-DotEnvValue "NGROK_DOMAIN" }

Write-Host ""
Write-Host "Starting tunnel -> http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host ""
if ($ngrokDomain) {
    Write-Host "Reserved ngrok domain: https://$ngrokDomain" -ForegroundColor Cyan
    Write-Host "Flutterwave webhook URL:" -ForegroundColor Yellow
    Write-Host "  https://$ngrokDomain/webhooks/flutterwave/"
} else {
    Write-Host "After ngrok starts, open: http://127.0.0.1:4040" -ForegroundColor Cyan
    Write-Host "Copy the HTTPS URL and set Flutterwave webhook to:"
    Write-Host "  https://YOUR-SUBDOMAIN.ngrok-free.app/webhooks/flutterwave/" -ForegroundColor Yellow
}
if ($webhookSecret) {
    Write-Host ""
    Write-Host "Flutterwave secret hash (must match .env):" -ForegroundColor Cyan
    Write-Host "  $webhookSecret"
}
Write-Host ""
Write-Host "Note: MoMo checkout auto-polls charge status; webhooks are optional for local testing."
Write-Host "Press Ctrl+C to stop ngrok."
Write-Host ""

if ($ngrokDomain) {
    & $ngrok http --url=$ngrokDomain $Port
} else {
    & $ngrok http $Port
}
