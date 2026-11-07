$ErrorActionPreference = 'Stop'
$pokedexRoot = Split-Path -Parent $PSScriptRoot
$pokedexTools = Join-Path $pokedexRoot '.tools'

function Assert-LastCommand([string]$operation) {
    if ($LASTEXITCODE -ne 0) { throw "$operation failed with exit code $LASTEXITCODE" }
}

# Reuse the installed Node 24 binary in a private project tool directory.
# Corepack's bundled CLI then installs packageManager's exact pnpm into a private cache.
if (-not (Test-Path -LiteralPath (Join-Path $pokedexTools 'node\node.exe'))) {
    $installedNode = (Get-Command node.exe -ErrorAction Stop).Source
    $installedVersion = & $installedNode --version
    if ($installedVersion -notmatch '^v24\.') { throw 'Node.js 24 is required to bootstrap this project.' }
    $installedCorepack = Join-Path (Split-Path $installedNode) 'node_modules\corepack'
    if (-not (Test-Path -LiteralPath $installedCorepack)) { throw 'Corepack must be available next to Node.js.' }
    New-Item -ItemType Directory -Force -Path (Join-Path $pokedexTools 'node') | Out-Null
    Copy-Item -LiteralPath $installedNode -Destination (Join-Path $pokedexTools 'node\node.exe')
    Copy-Item -LiteralPath $installedCorepack -Destination (Join-Path $pokedexTools 'corepack') -Recurse
}
New-Item -ItemType Directory -Force -Path (Join-Path $pokedexTools 'bin') | Out-Null
$pokedexPackageManager = (Get-Content -Raw (Join-Path $pokedexRoot 'apps\web\package.json') | ConvertFrom-Json).packageManager
if ($pokedexPackageManager -notmatch '^pnpm@\d+\.\d+\.\d+$') { throw 'Expected an exact pnpm version in packageManager.' }
foreach ($pokedexTool in @('pnpm', 'corepack')) {
    $pokedexEntry = '"%~dp0..\node\node.exe" "%~dp0..\corepack\dist\corepack.js"'
    if ($pokedexTool -eq 'pnpm') { $pokedexEntry += ' ' + $pokedexPackageManager }
    $shim = '@echo off' + "`r`n" + 'setlocal' + "`r`n" +
        'set "COREPACK_HOME=%~dp0..\corepack-cache"' + "`r`n" +
        'set "PNPM_HOME=%~dp0..\pnpm-home"' + "`r`n" +
        'set "pnpm_config_store_dir=%~dp0..\pnpm-store"' + "`r`n" +
        'set "npm_config_cache=%~dp0..\npm-cache"' + "`r`n" +
        $pokedexEntry + ' %*' + "`r`n" +
        'exit /b %errorlevel%' + "`r`n"
    Set-Content -LiteralPath (Join-Path $pokedexTools "bin\$pokedexTool.cmd") -Value $shim -Encoding ascii
}
. (Join-Path $PSScriptRoot 'activate-dev.ps1')

Push-Location $pokedexRoot
try {
    uv python install 3.13 --no-bin --no-registry
    Assert-LastCommand 'Python installation'
    Push-Location apps\api
    try {
        uv sync --frozen --python 3.13
        Assert-LastCommand 'API dependency installation'
    } finally { Pop-Location }
    Push-Location apps\web
    try {
        pnpm --version
        Assert-LastCommand 'Pinned pnpm setup'
        pnpm install --frozen-lockfile
        Assert-LastCommand 'Web dependency installation'
    } finally { Pop-Location }
} finally { Pop-Location }
Write-Host 'Ready. Dot-source scripts\activate-dev.ps1 in each new terminal.'
