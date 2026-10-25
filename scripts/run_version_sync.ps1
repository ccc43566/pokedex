$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$docker = if ($dockerCommand) { $dockerCommand.Source } else {
    Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe'
}
$source = Join-Path $projectRoot 'apps\api\src\pokedex_api\sync\version_sprites.py'
Set-Location $projectRoot
Get-Content -Raw -LiteralPath $source | & $docker compose exec -T -e VERSION_SPRITE_CONCURRENCY=16 -e VERSION_SPRITE_SKIP_MATERIALIZE=1 api python -u -
if ($LASTEXITCODE -ne 0) { throw "Version sprite sync failed with exit code $LASTEXITCODE" }
