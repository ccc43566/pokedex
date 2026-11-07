$ErrorActionPreference = 'Stop'
$pokedexRoot = Split-Path -Parent $PSScriptRoot
$pokedexSource = (Join-Path $pokedexRoot 'apps\api\src').Replace('\', '/')
Push-Location $pokedexRoot
try {
    $pokedexRunning = docker inspect --format '{{.State.Running}}' pokedex-api-preview 2>$null
    if ($LASTEXITCODE -eq 0) {
        if ($pokedexRunning -ne 'true') { docker start pokedex-api-preview }
    } else {
        $pokedexApi = @(docker inspect pokedex-api-1 | ConvertFrom-Json)[0]
        if ($LASTEXITCODE -ne 0) { throw 'Existing API container was not found.' }
        $pokedexNetwork = @($pokedexApi.NetworkSettings.Networks.PSObject.Properties.Name)[0]
        $pokedexDatabase = @($pokedexApi.Config.Env | Where-Object { $_.StartsWith('DATABASE_URL=') })[0]
        if (-not $pokedexDatabase) { throw 'Existing API database configuration was not found.' }
        $pokedexPreviousDatabase = $env:DATABASE_URL
        try {
            $env:DATABASE_URL = $pokedexDatabase.Substring('DATABASE_URL='.Length)
            docker run -d --pull never --name pokedex-api-preview `
                --network $pokedexNetwork --volumes-from 'pokedex-api-1:ro' `
                -p '127.0.0.1:8001:8000' -v "${pokedexSource}:/app/src:ro" `
                -e DATABASE_URL -e MEDIA_ROOT=/app/media -e MEDIA_PUBLIC_PATH=/media `
                --entrypoint /app/.venv/bin/python $pokedexApi.Image `
                -m uvicorn pokedex_api.main:app --host 0.0.0.0 --port 8000 `
                --reload --reload-dir /app/src
        } finally { $env:DATABASE_URL = $pokedexPreviousDatabase }
    }
    if ($LASTEXITCODE -ne 0) { throw 'API preview failed to start.' }
} finally { Pop-Location }
Write-Host 'API preview: http://127.0.0.1:8001 (shared database, read-only source/media mounts).'
Write-Host 'Before pnpm dev: $env:POKEDEX_DEV_API_BACKEND = "http://127.0.0.1:8001"'
