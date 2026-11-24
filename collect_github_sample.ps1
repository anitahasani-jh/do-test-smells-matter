[CmdletBinding()]
param(
    [ValidateSet(20, 100, 200, 300)]
    [int]$Count = 20,
    [string]$Query = 'topic:testing',
    [string]$BaselineDate = '2025-01-01',
    [string]$FollowupDate = '2025-07-01',
    [int]$Seed = 7,
    [int]$MinStars = 20,
    [int]$MaxCandidates = 300,
    [int]$MaxPages = 3
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host '=== Team 7 GitHub collection ===' -ForegroundColor Cyan
Write-Host "Requested repositories: $Count"
Write-Host "Baseline: $BaselineDate | Follow-up: $FollowupDate"
Write-Host "Query: $Query"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is not installed or not on PATH.' }
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Python launcher (py) is not installed.' }

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host '[1/4] Creating Python environment...'
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv. Install Python 3.12 first.' }
}
$Python = (Resolve-Path '.venv\Scripts\python.exe').Path

Write-Host '[2/4] Installing project and dependencies...'
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
& $Python -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Project/dependency installation failed.' }

Write-Host '[3/4] Checking runtime...'
& $Python -m team7_pipeline doctor
if ($LASTEXITCODE -ne 0) { throw 'Runtime doctor failed.' }
$Jar = Join-Path $Root 'tools\TestSmellDetector.jar'
if (-not (Test-Path $Jar)) {
    throw 'Missing tools\TestSmellDetector.jar. Download the official tsDetect v2.2 standalone JAR, place it there, then rerun this script.'
}

$Sample = "configs\github-sample-$Count.json"
$Audit = "configs\github-sample-$Count.sampling-audit.json"
if ((Test-Path $Sample) -or (Test-Path $Audit)) {
    throw "Sample files already exist ($Sample or $Audit). Do not overwrite an existing sample. Review/archive them and choose a fresh filename/run ID before retrying."
}
if ($MaxCandidates -lt $Count) { throw 'MaxCandidates must be >= Count.' }

Write-Host '[4/4] Selecting repositories from GitHub...'
& $Python -m team7_pipeline sample `
    --query $Query `
    --count $Count `
    --baseline-date $BaselineDate `
    --followup-date $FollowupDate `
    --seed $Seed `
    --min-stars $MinStars `
    --max-candidates $MaxCandidates `
    --max-pages $MaxPages `
    --output $Sample
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Sample selection did not reach $Count repositories. Inspect $Audit. No collection run was started."
    exit $LASTEXITCODE
}

$AuditData = Get-Content $Audit -Raw | ConvertFrom-Json
if ([int]$AuditData.selected -ne $Count) {
    throw "Audit selected $($AuditData.selected) of $Count. Refusing to start collection."
}

Write-Host 'Starting real repository collection. This can take a long time and use substantial disk/network.' -ForegroundColor Yellow
& $Python -m team7_pipeline run --config $Sample
if ($LASTEXITCODE -ne 0) {
    Write-Warning 'Collection ended with failed/partial repositories. Keep all outputs; inspect repository_status.csv and manifest.json. Resume with the documented --resume command.'
    exit $LASTEXITCODE
}

Write-Host "Collection command finished. Review results\github-sample-$Count\manifest.json and repository_status.csv." -ForegroundColor Green
