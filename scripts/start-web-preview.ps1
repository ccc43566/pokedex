$ErrorActionPreference = 'Stop'
$pokedexRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'activate-dev.ps1')
$pokedexPreviousBackend = $env:POKEDEX_DEV_API_BACKEND
$env:POKEDEX_DEV_API_BACKEND = 'http://127.0.0.1:8001'
Push-Location (Join-Path $pokedexRoot 'apps\web')
try {
    pnpm dev
    if ($LASTEXITCODE -ne 0) { throw 'Web preview failed.' }
} finally {
    Pop-Location
    $env:POKEDEX_DEV_API_BACKEND = $pokedexPreviousBackend
}
