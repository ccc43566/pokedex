param([string]$BaseUrl = 'http://localhost:8080')

$ErrorActionPreference = 'Stop'
$pokedexJobUrl = $BaseUrl.TrimEnd('/') + '/media/.collection/2026-10-26'
$pokedexState = Invoke-RestMethod ($pokedexJobUrl + '/state.json')
$pokedexProgress = Invoke-RestMethod ($pokedexJobUrl + '/progress.json')
[pscustomobject]@{
    Status = $pokedexState.status
    StartedAt = $pokedexState.startedAt
    Round = $pokedexState.round
    ProcessedUrlsThisRound = $pokedexProgress.processedUrls
    TotalUrlsThisRound = $pokedexProgress.totalUrls
    DownloadedUrlsThisRound = $pokedexProgress.downloadedUrls
    ReusedHashesThisRound = $pokedexProgress.reusedHashes
    FailedUrlsThisRound = $pokedexProgress.failedUrls
    CorruptUrlsThisRound = $pokedexProgress.corruptUrls
    NewMiBThisRound = [math]::Round($pokedexProgress.newBytes / 1MB, 1)
    UpdatedAt = $pokedexProgress.updatedAt
    FinishedAt = $pokedexState.finishedAt
}
