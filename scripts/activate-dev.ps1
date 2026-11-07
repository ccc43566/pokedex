# Dot-source this file: . .\scripts\activate-dev.ps1
$pokedexRoot = Split-Path -Parent $PSScriptRoot
$pokedexTools = Join-Path $pokedexRoot '.tools'
$env:COREPACK_HOME = Join-Path $pokedexTools 'corepack-cache'
$env:PNPM_HOME = Join-Path $pokedexTools 'pnpm-home'
$env:pnpm_config_store_dir = Join-Path $pokedexTools 'pnpm-store'
$env:npm_config_cache = Join-Path $pokedexTools 'npm-cache'
$env:UV_CACHE_DIR = Join-Path $pokedexTools 'uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $pokedexTools 'python'
$env:PATH = (Join-Path $pokedexTools 'node') + ';' + (Join-Path $pokedexTools 'bin') + ';' + $env:PATH
$pokedexVenv = Join-Path $pokedexRoot 'apps\api\.venv\Scripts\Activate.ps1'
if (Test-Path -LiteralPath $pokedexVenv) {
    . $pokedexVenv
}
