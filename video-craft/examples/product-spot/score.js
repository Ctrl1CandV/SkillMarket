import { install, voice, duck, pluck, NOTE, bass, hat, kick, chime, tick, pop, warmPad } from '../../kit/sound.js';
import { proof } from './material/proof.js';

function score(m, events, duration) {
  const { job }=proof, S=job.shots;
  const chords=[['D2','A3','D4','F4'],['Bb1','F3','A3','D4'],['G1','D3','F3','A3'],['A1','E3','G3','C4']];
  const beat=.46, bar=beat*4;
  for(let i=0;i*bar<duration-1.7;i++){
    const start=i*bar, notes=chords[i%4];
    warmPad(m,m.music,start,start+bar,notes.slice(1).map(NOTE),{gain:.025,cutoff:1150,attack:.17,release:.42});
    for(let j=0;j<4;j++){
      const t=start+j*beat;
      if(j%2===0){kick(m,m.music,t,{gain:.15});bass(m,m.music,t,NOTE(notes[0]),{dur:.26,gain:.105});}
      if(t>S.question&&t<S.send)hat(m,m.music,t+beat/2,{gain:.034,dur:.05});
      if(t>S.interface&&j%2)pluck(m,m.music,t,NOTE(notes[1+(i+j)%3])*2,{gain:.055,dur:.31,bright:1800,pan:j===1?-.22:.24});
    }
  }
  const regions=job.voice.map(({at,id})=>{
    if(!m.vo[id])throw new Error('Missing voice '+id+'; supply --vo examples/product-spot/voice');
    const end=voice(m,at,id,{gain:1});
    return [at,end];
  });
  duck(m.music,regions,{base:.58,depth:-8,attack:.10,release:.27});
  for(const {t,type} of events) {
    if(type==='switch'){for(const delta of [0,.065,.15])tick(m,m.sfx,t+delta,{freq:1700-delta*4000,gain:.14,dur:.045});}
    if(type==='edit'||type==='rebuild'||type==='download'){
      tick(m,m.sfx,t,{freq:type==='edit'?1200:2300,gain:.12,dur:.035});
      pop(m,m.sfx,t+.025,{f0:360,f1:type==='rebuild'?820:480,gain:.09,dur:.08});
    }
    if(type==='send'||type==='brand'){
      ['D4','A4','D5'].forEach((note,i)=>chime(m,m.sfx,t+i*.105,NOTE(note),{gain:.045,dur:1.2}));
    }
  }
  m.master.gain.setValueAtTime(1,duration-1.1);m.master.gain.linearRampToValueAtTime(0,duration);
}
install(score,{reverb:.11,irSec:1.15,irPow:3});
