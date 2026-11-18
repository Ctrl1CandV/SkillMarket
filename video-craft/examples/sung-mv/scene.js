import { clamp, register, rng } from '../../kit/kit.js';
import { beat, cues, duration, lines, title } from './song.mjs';
import { C, P, bird, cloud, ellipse, line, paperGrain, path, poly, postmark, rect, smooth } from './print.js';

const W=1200, H=750;
const serif='"KaiTi","STKaiti","Kaiti SC","Noto Serif CJK SC","SimSun",serif';
const rand=rng(46);
const wood=Array.from({length:94},()=>[rand()*1900-200,rand()*1000-100,25+rand()*225,rand()*20-10]);
const roofs=Array.from({length:36},(_,i)=>({
  x:i*99-480, y:289+rand()*130, w:71+rand()*69, h:26+rand()*46, steep:rand(),
}));

function text(str,x,y,size,color,opts={}){
  C.font=(opts.weight||'normal')+' '+size+'px '+(opts.family||serif);
  C.textAlign=opts.align||'left'; C.fillStyle=color; C.fillText(str,x,y);
}
function wall(x,y,w,h,side,front,shade,roof){
  poly([[x,y],[x+w,y+6],[x+w,y+h+8],[x,y+h]],front);
  poly([[x+w,y+6],[x+w+side,y-20],[x+w+side,y+h-17],[x+w,y+h+8]],shade);
  poly([[x-9,y],[x+21,y-33],[x+w+side-8,y-40],[x+w+8,y+8]],roof);
  line([[x-9,y+2],[x+w+8,y+9],[x+w+side,y-19]],P.ink,2);
  poly([[x+w*.28,y-18],[x+w*.28,y-50],[x+w*.28+11,y-51],[x+w*.28+11,y-18]],shade);
  rect(x+w*.28-2,y-54,16,4,roof);
  for(let r=0;r<4;r++)line([[x+19-r*5,y-26+r*6],[x+w+side-23-r*6,y-32+r*7]],shade,1);
  for(let j=0;j<5;j++){
    const dx=(j+1)*side/6;
    line([[x+w+dx,y+15-dx*.36],[x+w+dx,y+h-7-dx*.36]],front,1);
  }
  for(let wy=21;wy<h-13;wy+=40){
    for(let wx=14;wx<w-7;wx+=27){
      const xx=x+wx, yy=y+wy+wx*.035;
      rect(xx,yy,10,18,shade); rect(xx+1,yy+8,9,2,front);
      rect(xx-1,yy+18,13,2,roof);
    }
  }
}
function skyline(offset,base,scale,dark=false){
  C.save(); C.translate(offset,base); C.scale(scale,scale);
  for(const [i,a] of roofs.entries()){
    const y=a.y;
    poly([[a.x,y+10],[a.x+a.w*.43,y-a.h],[a.x+a.w,y+8],[a.x+a.w,670],[a.x,670]],dark?P.pine:P.jade);
    if(i%3===0)rect(a.x+a.w*.65,y-a.h*.8,9,24,dark?P.pine:P.jade);
    if(dark){
      for(let j=0;j<3;j++)rect(a.x+15+j*18,y+24,5,9,P.sea);
    }
  }
  C.restore();
}
function desk(t){
  rect(0,0,W,H,P.pine);
  C.save(); C.rotate(-.19); C.globalAlpha=.42;
  for(const [x,y,len,dy] of wood)path('M'+x+' '+y+' q'+len*.4+' '+dy+' '+len+' 1',null,P.sea,1.2);
  C.restore();
  // Clipped corners of the blotter, envelope and fountain pen establish this as a real workspace.
  poly([[-56,195],[819,-194],[1385,580],[304,943]],'#123f3d');
  poly([[-53,170],[820,-212],[1372,555],[292,925]],P.jade);
  poly([[-14,177],[811,-185],[1337,554],[295,894]],'#80aa98');
  C.save(); C.translate(152,155); C.rotate(-.26);
  rect(-260,-175,406,271,'#538078'); rect(-268,-185,406,272,P.paper);
  line([[-268,-155],[-70,9],[137,-175]],P.earth,1.5);
  line([[-269,76],[-119,-41]],P.earth,1.2);
  C.restore();
  C.save(); C.translate(1064,207); C.rotate(-1.04);
  rect(-169,-7.5,228,17,'#517575');rect(-167,-12,224,14,P.scarlet);
  rect(-165,-12,220,3,P.pink);poly([[57,-12],[89,-6],[57,2]],P.paper);
  poly([[77,-8],[91,-6],[78,-3.5]],P.ink);rect(-181,-12,15,14,P.straw);
  C.restore();
  // The sheet takes the full measure to crease. The following held note lets the viewer read its new silhouette.
  const amount=smooth((t-cues.fold)/1.18);
  const lift=smooth((t-5.38)/1.83);
  const px=566+82*lift,py=344-86*lift;
  C.save(); C.translate(586,386);C.rotate(-.13);C.globalAlpha=.19;
  ellipse(0,0,207-82*amount,86-54*amount,P.ink);C.restore();
  bird(px,py,1.70-.24*amount,-.17+.09*amount-.12*lift,amount,Math.sin(lift*8)*lift);
  if(amount<.72){
    C.save();C.translate(px,py);C.rotate(-.17);C.scale(1.7,1.7);C.globalAlpha=1-smooth(amount/.72);
    path('M11 -27 C-3 -41 -17 -18 12 0 C41 -20 25 -43 11 -27 Z',null,'#8c302a',2.3);
    C.restore();
  }
  if(t<2.34){
    C.save();C.globalAlpha=1-smooth((t-1.86)/.45);
    text(title,82,618,98,P.white,{weight:'bold'});text('P A P E R   P O S T',88,656,17,P.white,{family:'Georgia,serif'});
    C.restore();
  }
}
function street(t){
  const p=clamp((t-cues.launch)/(cues.hook-cues.launch));
  rect(0,0,W,H,P.mist);
  cloud(932-p*82,94,1.05,P.paper);cloud(245-p*82,219,.64,'#cbd6af');
  skyline(20-p*65,8,.83); skyline(-100-p*145,46,1.03,true);
  C.save(); C.translate(-p*400,-p*26);
  wall(-102,430,242,330,75,P.straw,P.earth,P.rust);
  wall(75,516,160,283,60,'#c69e68','#866952',P.ink);
  wall(301,368,232,410,69,P.paper,'#a78359',P.scarlet);
  wall(532,479,145,331,59,'#c5a975','#866f54',P.ink);
  wall(727,319,225,490,83,'#edcf91','#ae8a5f','#b9563b');
  wall(977,406,174,450,67,'#91aa8d','#628a7e',P.ink);
  wall(1195,485,204,320,40,'#e2b97d','#aa8057',P.rust);
  wall(1412,367,188,420,70,P.paper,'#a78359',P.scarlet);
  poly([[313,521],[520,526],[536,554],[304,548]],P.red);
  for(let i=0;i<7;i++){
    poly([[316+29*i,521],[326+29*i,521],[336+29*i,549],[322+29*i,548]],P.paper);
  }
  rect(328,551,48,72,P.pine);rect(389,553,105,44,P.sea);
  rect(739,399,133,21,P.pine);
  text('邮 政',805,415,15,P.paper,{align:'center',weight:'bold'});
  // Clothes and street wires cross the flightpath at different depths.
  path('M-40 370 Q330 552 675 431 T1390 316',null,P.ink,2);
  for(const [x,y,col] of [[84,422,P.paper],[125,434,P.jade],[169,446,P.pink],[1019,422,P.straw]]){
    poly([[x,y],[x+22,y+5],[x+20,y+41],[x-5,y+32]],col);
    line([[x+5,y-2],[x+5,y+5]],P.ink,2);
  }
  C.restore();
  const x=317+462*p, y=270-51*Math.sin(p*Math.PI*1.2)+18*p;
  bird(x,y,.92+.12*p,-.11+.15*Math.cos(p*Math.PI),1,.68*Math.sin(8*p+.7));
  // A near sill slips through the lower edge while the distant roofs barely move.
  poly([[-560-p*530,588],[-58-p*530,452],[168-p*530,522],[-348-p*530,713]],P.pine);
  poly([[-390-p*530,713],[168-p*530,522],[168-p*530,750],[-390-p*530,750]],P.ink);
}
function meadow(t){
  const p=clamp((t-cues.hook)/(cues.land-cues.hook));
  rect(0,0,W,H,P.paper);
  ellipse(279+p*24,221,111,111,'#edac68');
  for(let i=0;i<8;i++)rect(166,209+i*13,246,1.8,'#f2c98a');
  cloud(1007-85*p,128,.91,'#f9e8bf');cloud(89-27*p,337,.57,'#f9e9c1');
  path('M0 494 Q178 411 331 467 T670 456 Q830 405 1028 448 T1250 409 V760 H0Z',P.mist);
  path('M0 555 Q162 489 297 537 Q432 590 587 518 T921 521 Q1115 546 1240 501 V760 H0Z',P.jade);
  path('M-25 677 Q170 557 325 633 Q448 666 599 595 Q760 524 920 601 Q1060 653 1230 560 V760 H-25Z',P.sea);
  for(let i=0;i<9;i++){
    path('M'+(-54+i*16)+' 760 Q198 '+(584+i*10)+' 326 '+(647+i*7)+' T669 '+(609+i*10),null,'#74a597',1.5);
  }
  const q=clamp(p*2);
  // The large second call is a reverse angle on the ink mark seen on the table; it is earned by the approach.
  if(t<cues.secondCall){
    const x=142+728*q, y=381-160*Math.sin(q*Math.PI*.84);
    path('M15 510 C160 536 228 477 280 433',null,'#c9b27e',1.5);
    bird(x,y,.67+.54*q,-.37+.23*q,1,.72*Math.sin(q*6));
  }else{
    const r=clamp((t-cues.secondCall)/(cues.land-cues.secondCall));
    C.save(); C.translate(60+42*r,-55*r);
    bird(668+53*r,306+48*r,2.68-.27*r,-.15+.24*r,1,.84*Math.sin(r*5.5+.6));
    C.restore();
    cloud(1238-128*r,476,1.20,'#f5e5b6');
  }
}
function hand(x,y,k){
  C.save();C.translate(x,y);C.scale(k,k);
  // Index, middle and ring fingers lie at unequal heights along the far edge of an open palm.
  path('M414 100 C330 103 273 64 219 44 C190 32 151 19 137 9 C129 0 139 -10 154 -9 L244 13 L134 -21 C117 -28 118 -41 132 -45 C143 -49 180 -37 209 -32 L261 -22 L166 -62 C151 -68 149 -77 160 -82 C169 -87 180 -85 194 -79 L310 -39 Q350 -29 371 -9 L421 10 Z',P.skinDeep);
  path('M401 100 C350 106 305 88 266 73 C217 55 148 46 99 20 C85 13 78 7 82 -1 C86 -11 101 -10 121 -5 L212 17 C222 19 228 12 215 7 L99 -33 C85 -37 78 -44 83 -53 C88 -63 104 -63 121 -57 L240 -25 C260 -23 281 -22 308 -13 C286 -37 280 -70 272 -86 C265 -103 270 -113 282 -111 C298 -110 306 -91 316 -77 C339 -47 368 -40 392 -13 L444 15 Z',P.skin);
  path('M107 -51 Q148 -42 187 -31 M93 -2 Q118 2 145 10 M232 27 Q288 20 308 0 M195 37 Q228 48 255 51 M288 -83 Q292 -89 299 -85',null,'#ae6e4c',1.7);
  for(let j=0;j<7;j++)path('M'+(308+j*6)+' '+(72+j*.5)+' q7 -2 14 -7',null,'#ce8860',1);
  path('M396 -10 L519 11 L527 148 L357 116 Z',P.paper);
  path('M424 -8 L596 -28 L599 166 L390 123 Z',P.pine);
  for(let j=0;j<9;j++)line([[436+j*15,-7],[405+j*16,126]],j%3?P.sea:P.mist,j%3?1.4:3);
  C.restore();
}
function landing(t){
  const p=clamp((t-cues.land)/(cues.palm-cues.land));
  const settle=smooth((t-cues.palm)/1.04);
  rect(0,0,W,H,P.jade);
  ellipse(264,190,108,108,P.straw);
  cloud(885,144,.98,P.mist);cloud(358,254,.45,'#c4cca5');
  skyline(-24,46,.87);skyline(-127,122,1.06,true);
  poly([[0,523],[1200,604],[1200,750],[0,750]],P.ink);
  poly([[0,520],[1200,598],[1200,620],[0,543]],P.paper);
  const rise=smooth((t-cues.land+.05)/1.4);
  C.save(); C.translate(64*(1-rise),42*(1-rise));
  hand(440,421,1.49);
  C.restore();
  const x=289+423*smooth(p), y=181+174*smooth(p);
  // Finish with the red wing resting in the fold of the palm; settle on the sustained '心'.
  C.save(); C.globalAlpha=.20*settle;ellipse(712,411,81,10,P.rust);C.restore();
  const rest=Math.max(0,t-cues.palm);
  bird(x,y,.73+.22*p,.24*Math.sin(p*Math.PI)-.08*(1-settle)+.027*settle*Math.sin(rest*1.8),1,
       (1-settle)*.65*Math.sin((t-cues.land)*4.4)+settle*(.17+.16*Math.exp(-rest*.45)*Math.sin(rest*3)));
}
function caption(t) {
  const b=t/beat, active=lines.find(l=>b>=l.start-.08 && b<l.end);
  if(!active) return;
  const dark=t>=cues.hook && t<cues.land;
  // Each line is readable at once. A thin underline belongs to the print, not to a karaoke cursor.
  C.save();
  C.globalAlpha=smooth((b-active.start+.08)/.22)*smooth((active.end-b)/.25);
  C.font='bold 42px '+serif;
  const width=C.measureText(active.text).width;
  rect(50,639,width+52,72,dark?P.paper:P.ink);
  rect(50,709,width+52,2.6,dark?P.scarlet:P.pink);
  text(active.text,76,690,42,dark?P.ink:P.white,{weight:'bold'});
  C.restore();
}
function seek(t) {
  C.setTransform(1.2,0,0,1.2,0,0);C.lineJoin='round';C.lineCap='round';
  if(t<cues.launch)desk(t);
  else if(t<cues.hook)street(t);
  else if(t<cues.land)meadow(t);
  else landing(t);
  caption(t);paperGrain();
}
register({width:1440,height:900,fps:24,duration,seek,meta:{events:Object.entries(cues).map(([kind,t])=>({kind,t}))}});
seek(0);
