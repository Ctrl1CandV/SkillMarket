param([Parameter(Mandatory=$true)][string]$Scratch, [string]$Voice='promo', [string]$CasePath)
# Render the spoken lines with kit/narrate.py (local VoxCPM voice card; Edge when VoxCPM is missing).
# Existing WAVs can instead be passed to audio.mjs --vo.
$ErrorActionPreference = 'Stop'
if (-not $CasePath) { $CasePath = Join-Path $PSScriptRoot 'spot.json' }
$job = Get-Content -LiteralPath $CasePath -Encoding UTF8 -Raw | ConvertFrom-Json
$generator = Join-Path $PSScriptRoot '../../kit/narrate.py'
python $generator $CasePath $Scratch --voice $Voice --takes 3
if ($LASTEXITCODE) { throw 'Could not render the spoken takes.' }
$encoder = if ($env:VC_FFMPEG) { $env:VC_FFMPEG } else { 'ffmpeg' }
$voiceDir = Join-Path $PSScriptRoot 'voice'
New-Item -ItemType Directory -Force -Path $voiceDir | Out-Null
foreach ($line in $job.voice) {
    $wav = Join-Path $Scratch ($line.id + '.wav')
    $mp3 = Join-Path $voiceDir ($line.id + '.mp3')
    & $encoder -nostdin -v error -y -i $wav -c:a libmp3lame -b:a 160k $mp3
    if ($LASTEXITCODE) { throw "Could not encode $mp3" }
}
