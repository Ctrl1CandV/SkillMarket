"""Mix an aligned lead vocal with the paper-bird arrangement.

Usage: python make-song.py path/to/vocal.wav out/audio
Requires NumPy, Node and FFmpeg. The input starts at film time zero.
"""
import json
import math
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np


RATE = 44100
TRANSPOSE = -3


def hz(midi):
    return 440 * 2 ** ((midi+TRANSPOSE-69)/12)


def put(track, at, mono, amp=1., pan=0.):
    index = round(at*RATE)
    n = min(len(mono), len(track)-index)
    if n > 0:
        track[index:index+n] += mono[:n, None]*amp*np.array([math.cos((pan+1)*math.pi/4),
                                                              math.sin((pan+1)*math.pi/4)])


def pluck(midi, length, mellow=False):
    t = np.arange(round(length*RATE))/RATE
    freq = hz(midi)
    sig = np.zeros(len(t))
    for k, amount in enumerate([1., .39, .16, .11, .05, .026], 1):
        sig += amount*np.sin(2*np.pi*freq*k*(1+.000045*k*k)*t) * np.exp(-t*(1.6+.78*k))
    return sig*np.minimum(1,t/(.012 if mellow else .005))*np.minimum(1,t[::-1]/.06)


def write(path, data):
    with wave.open(str(path), 'wb') as output:
        output.setparams((2,2,RATE,0,'NONE','not compressed'))
        output.writeframes((np.clip(data,-.999,.999)*32767).astype('<i2').tobytes())


def build(lead, output):
    show = "import {beat,duration,lines,chords} from './song.mjs';console.log(JSON.stringify({beat,duration,lines,chords}))"
    chart = json.loads(subprocess.check_output(['node','--input-type=module','-e',show], cwd=Path(__file__).parent))
    beat, duration = chart['beat'], chart['duration']
    # Preserve phrasing and relative dynamics across the entire performance.
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-loglevel', 'error', '-i', str(lead),
                                   '-ar', str(RATE), '-ac', '1', '-f', 'f32le', 'pipe:1'])
    track = np.frombuffer(raw, '<f4')
    frames = round(duration * RATE)
    if abs(len(track) - frames) > RATE * .10:
        raise ValueError(f'Expected a lead aligned to {duration:.2f} seconds; got {len(track) / RATE:.2f}.')
    voice = np.zeros((frames, 2))
    music = np.zeros_like(voice)
    count = min(len(track), frames)
    rms = np.sqrt(np.mean(track * track))
    if rms < 1e-5:
        raise ValueError('The supplied vocal is silent.')
    voice[:count] = track[:count, None] * min(.95 / np.max(np.abs(track)), .14 / rms)
    direct = voice.copy()
    for delay, gain, channel in [(.033, .095, 0), (.047, .085, 1), (.079, .045, 0), (.113, .040, 1)]:
        n = round(delay * RATE)
        voice[n:, channel] += direct[:-n, channel] * gain
    rng = np.random.default_rng(707)
    for bar, chord in enumerate(chart['chords']):
        start = bar*4
        for j, step in enumerate([0.,.52,1.52,2.,2.78,3.50]):
            if start+step >= chart['duration']/beat-.7:
                continue
            note = chord[[1,2,3,1,2,3][j]]+12
            put(music,(start+step)*beat,pluck(note,1.5),[.13,.105,.08,.095,.09,.07][j],-.45+.16*(j%3))
        for j in (0,2):
            t = np.arange(round(beat*1.8*RATE))/RATE
            base = hz(chord[0]-(12 if j==0 else 5))
            bass = (np.sin(2*np.pi*base*t)+.27*np.sin(4*np.pi*base*t))
            put(music,(start+j)*beat,bass*(1-np.exp(-t*65))*np.exp(-t*3)*np.minimum(1,t[::-1]/.08),.23)
        if 2 <= bar < 9:
            for pulse in range(8):
                hit = np.arange(round(.14*RATE))/RATE
                noise = rng.normal(0,1,len(hit))
                brush = np.diff(np.r_[0,noise])*np.exp(-hit*(28 if pulse in (2,6) else 75))
                put(music,(start+pulse/2+.022*(pulse%2))*beat,brush,.022 if pulse in (2,6) else .010,.31)
        if bar in (0,5,6,8):
            for j, n in enumerate(chord[1:]):
                put(music,(start+.07*j)*beat,pluck(n+24,1.70,True),.065,.54)
    endfade = np.minimum(1,np.arange(len(music))[::-1]/(.65*RATE))
    music *= endfade[:,None]
    # The pluck and brush start on some of the same beats as fricatives. Make room for their onsets.
    duck = np.ones(len(music))
    for line in chart['lines']:
        for _, start, length, _ in line['notes']:
            start_sample = max(0,round((start*beat-.028)*RATE))
            t = np.arange(round((length*beat+.14)*RATE))/RATE
            depth = (.33+.23*np.exp(-t/.20))*np.minimum(1,t/.026)*np.minimum(1,t[::-1]/.14)
            n = min(len(t),len(duck)-start_sample)
            duck[start_sample:start_sample+n] = np.minimum(duck[start_sample:start_sample+n],1-depth[:n])
    music *= duck[:,None]
    output.mkdir(parents=True,exist_ok=True)
    write(output/'vocal-room.wav',voice)
    write(output/'backing.wav',music)
    write(output/'mix.wav',(voice+music)*.74)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(output/'mix.wav'),
                    '-af','loudnorm=I=-16:TP=-1.6:LRA=11','-ar','48000',
                    '-metadata','artist=绮萱 / DiffSinger AI 合成演唱','-c:a','libopus','-b:a','160k',str(output/'song.ogg')],check=True)


if __name__ == '__main__':
    build(Path(sys.argv[1]),Path(sys.argv[2]))
