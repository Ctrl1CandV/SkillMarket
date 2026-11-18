param([Parameter(Mandatory=$true)][string]$Scratch, [string]$Voice='Microsoft Huihui Desktop', [string]$CasePath)
# Optional Windows recording route. The six supplied MP3 clips can be rendered on any supported host.
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
if (-not $CasePath) { $CasePath = Join-Path $PSScriptRoot 'spot.json' }
$job=Get-Content -LiteralPath $CasePath -Encoding UTF8 -Raw | ConvertFrom-Json
$speaker=New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.SelectVoice($Voice)
$speaker.Rate=1
$voiceDir=Join-Path $PSScriptRoot 'voice'
New-Item -ItemType Directory -Force -Path $voiceDir,$Scratch | Out-Null
try {
  foreach ($line in $job.voice) {
    $wav=Join-Path $Scratch ($line.id+'.wav')
    $mp3=Join-Path $voiceDir ($line.id+'.mp3')
    $speaker.SetOutputToWaveFile($wav)
    $speaker.Speak($line.words)
    $speaker.SetOutputToNull()
    ffmpeg -v error -y -i $wav -af 'silenceremove=start_periods=1:start_duration=0.015:start_threshold=-48dB,areverse,silenceremove=start_periods=1:start_duration=0.025:start_threshold=-48dB,areverse,highpass=f=70' -c:a libmp3lame -b:a 80k $mp3
    if ($LASTEXITCODE -ne 0) { throw "Could not encode $mp3" }
  }
} finally { $speaker.Dispose() }
