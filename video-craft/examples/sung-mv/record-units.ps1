param([Parameter(Mandatory = $true)][string]$Out, [string]$Voice = 'Microsoft Huihui Desktop')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$directory = [IO.Directory]::CreateDirectory($Out).FullName
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice($Voice)
$synth.Rate = -2
try {
    $characters = node --input-type=module -e "import {lines} from './song.mjs'; console.log([...new Set(lines.flatMap(l=>l.notes.map(n=>n[0].codePointAt(0))))].join(' '))"
    if ($LASTEXITCODE -ne 0) { throw 'Run from the sung-mv folder with Node on PATH.' }
    foreach ($code in $characters.Trim().Split(' ')) {
        $synth.SetOutputToWaveFile((Join-Path $directory "$code.wav"))
        $synth.Speak([string][char][int]$code)
        $synth.SetOutputToNull()
    }
} finally { $synth.Dispose() }
