$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$postgresExe = 'C:\Program Files\PostgreSQL\18\bin\postgres.exe'
$dataPath = Join-Path $projectRoot '.local\postgres'
if ((Test-Path -LiteralPath $dataPath) -and (Test-Path -LiteralPath $postgresExe)) {
    $connection = Test-NetConnection -ComputerName 127.0.0.1 -Port 55432 -WarningAction SilentlyContinue
    if (-not $connection.TcpTestSucceeded) {
        Start-Process -FilePath $postgresExe -ArgumentList @('-D', ('"' + $dataPath + '"'), '-p', '55432', '-h', '127.0.0.1') -WindowStyle Hidden -RedirectStandardError (Join-Path $projectRoot '.local\postgres-start.log')
    }
}
$pythonExe = (Get-Command python).Source
Start-Process -FilePath $pythonExe -ArgumentList @('backend/manage.py', 'runserver', '127.0.0.1:8000', '--noreload') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot '.local\django.log') -RedirectStandardError (Join-Path $projectRoot '.local\django-error.log')
$nodeExe = (Get-Command node).Source
Start-Process -FilePath $nodeExe -ArgumentList @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot '.local\vite.log') -RedirectStandardError (Join-Path $projectRoot '.local\vite-error.log')
Write-Output 'Local application: http://127.0.0.1:5173'
Write-Output 'Log files are in .local. Demo credentials are in .local/demo-credentials.txt.'
