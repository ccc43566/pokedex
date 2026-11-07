param(
    [ValidateRange(1, 64)][int]$Concurrency = 12,
    [ValidateRange(0, 2147483647)][int]$Limit = 0
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$docker = if ($dockerCommand) { $dockerCommand.Source } else {
    Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe'
}
$source = Join-Path $projectRoot 'apps\api\src\pokedex_api\sync\version_sprites.py'
Set-Location $projectRoot
$arguments = @('compose', 'exec', '-T', '-e', "VERSION_SPRITE_CONCURRENCY=$Concurrency", '-e', 'VERSION_SPRITE_SKIP_MATERIALIZE=1')
if ($Limit -gt 0) { $arguments += @('-e', "VERSION_SPRITE_LIMIT=$Limit") }
$arguments += @('api', 'python', '-u', '-')
Get-Content -Raw -LiteralPath $source | & $docker @arguments
if ($LASTEXITCODE -ne 0) { throw "Version sprite sync failed with exit code $LASTEXITCODE" }
