import { register, rng } from '../../kit/kit.js';
import { proof } from './material/proof.js';

const { job, bounds } = proof, shot = job.shots, copy=job.copy;
document.title = job.title + ' · 倒场';
const W=1536, H=864, cssFont='"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",Arial,sans-serif';
const mono='Consolas,"Courier New",monospace', cream='#f6ecd6', dark='#201926', red='#ff5c41', muted='#c2b1a7';
const ctx=document.getElementById('screen').getContext('2d');
const frames=Object.fromEntries(await Promise.all(['before','edited','after'].map(async name=>{
  const img=new Image(); img.src='./material/'+name+'.png'; await img.decode(); return [name,img];
})));
const rand=rng(330), dust=Array.from({length:95},()=>[rand(),rand(),rand()]);
const smooth=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x)};
function rect(x,y,w,h,color){ctx.fillStyle=color;ctx.fillRect(x,y,w,h);}
function line(x,y,u,v,color,width=1){ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(u,v);ctx.stroke();}
function circle(x,y,r,color){ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();}
function polygon(points,color){ctx.fillStyle=color;ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fill();}
function label(s,x,y,size,color=cream,weight=600,font=cssFont,maxWidth) {
  ctx.fillStyle=color;ctx.font=weight+' '+size+'px '+font;ctx.textBaseline='alphabetic';
  if (maxWidth === undefined) ctx.fillText(s,x,y);
  else ctx.fillText(s,x,y,maxWidth);
}
function rail(x,y,w,color){line(x,y,x+w,y,color,1);line(x,y-5,x,y+5,color,1);line(x+w,y-5,x+w,y+5,color,1);}
function mark(x,y,k,color){polygon([[x,y+33*k],[x+55*k,y],[x+55*k,y+17*k],[x,y+50*k]],color);}
function stage(t, live=false) {
  rect(0,0,W,H,dark);
  const glow=ctx.createRadialGradient(1090,384,40,1090,384,730);
  glow.addColorStop(0,'#61424f');glow.addColorStop(.54,'#332a3c');glow.addColorStop(1,dark);
  rect(0,0,W,H,glow);
  // A clipped stage opening keeps the theatrical beams off the headline.
  ctx.save();ctx.beginPath();ctx.rect(631,0,905,864);ctx.clip();
  const horizon=593;
  polygon([[639,horizon],[W,horizon],[W,H],[555,H]],'#2b2331');
  for(let i=-5;i<14;i++){line(1075+(i-4)*30,horizon,1075+(i-4)*212,H,'#56404c',1.2);}
  for(const yy of [610,635,671,725,811])line(595,yy,W,yy,'#5b424c',1);
  // Truss and real-world cues (lamp housings, curtain legs, floor tape).
  line(633,95,W,95,'#96818b',3);line(633,125,W,125,'#766770',3);
  for(let x=649;x<1560;x+=56){line(x,125,x+28,95,'#81727a',2);line(x+28,95,x+56,125,'#81727a',2);}
  for(let i=0;i<4;i++){
    const x=715+i*230, aim=870+i*160+35*Math.sin(t*.36+i);
    const gradient=ctx.createLinearGradient(x,128,aim,690);
    gradient.addColorStop(0,live?(i%2?'#ffdfa8ed':'#ff7752cc'):(i%2?'#ffd2a48a':'#ff775256'));gradient.addColorStop(.7,i%2?'#ffd2a42c':'#f7765324');gradient.addColorStop(1,'#ffd2a400');
    polygon([[x-5,151],[x+6,151],[aim+130,678],[aim-115,678]],gradient);
    ctx.save();ctx.translate(x,144);ctx.rotate(-.28+i*.12);rect(-14,-14,28,25,'#1c1921');rect(-14,11,28,5,'#ffd4a1');ctx.restore();
  }
  for (const [a,b,c] of dust) circle(645+((a*910+t*(3+c*6))%910),165+b*425,0.6+c,'rgba(249,215,183,'+(.15+c*.24)+')');
  // Downstage monitor wedges, curtain edges, and a floor mark establish scale.
  for(const [x,y,s] of [[864,603,1],[1342,603,.88]]) {
    polygon([[x,y],[x+19*s,y-27*s],[x+85*s,y-21*s],[x+99*s,y],[x+87*s,y+8*s],[x+8*s,y+7*s]],'#221d26');
    line(x+22*s,y-21*s,x+83*s,y-15*s,'#967667',2);
  }
  line(1080,672,1114,685,'#ecb69b',4);line(1109,668,1083,686,'#ecb69b',4);
  if(live){
    // A singer walks from the wing to the microphone; downstage heads turn on the first chord.
    const walk=smooth((t-shot.brand)/1.35), fx=1260-145*walk, fy=585;
    const movement=Math.sin(walk*Math.PI*4)*(1-walk);
    ctx.save();ctx.translate(fx,fy);
    circle(-1,-105,12,'#241c28');polygon([[-11,-92],[9,-93],[18,-54],[7,-43],[-12,-44],[-16,-65]],'#2a202d');
    line(-6,-45,-16-13*movement,0,'#28202a',10);line(5,-46,14+16*movement,0,'#28202a',10);
    line(7,-86,23,-73,'#302331',7);line(23,-73,37,-83-7*walk,'#302331',6);
    ctx.restore();
    line(1153,fy,1153,fy-86,'#433442',3);line(1141,fy+1,1164,fy+1,'#443341',4);line(1148,fy-86,1158,fy-92,'#302532',5);
    for(let row=0;row<2;row++)for(let i=0;i<10;i++){
      const xx=654+i*108+(row?0:36), yy=817+51*row+Math.sin(i*2.4+row)*10, r=14+row*6;
      circle(xx,yy,r,'#201924');ctx.beginPath();ctx.ellipse(xx,yy+r*2.5,r*2.4,r*1.9,0,0,Math.PI*2);ctx.fill();
    }
  }
  polygon([[1495,0],[1536,0],[1536,602],[1480,580]],'#251c2b');
  ctx.restore();
}
function opening(t) {
  stage(t);
  label(copy.venue,76,100,27,cream);
  rail(78,133,480,'#95868b');
  const changed=t>=shot.switch;
  label(copy.opening,69,344,103,cream,800);
  label(changed?copy.after:copy.before,69,480,95,changed?red:cream,800,cssFont,665);
  label('演出统筹的改场时刻',79,756,25,muted,400);
  // Time board belongs in the stage geography. The radio-tick interrupts its old digits.
  rect(784,281,607,220,'#221d28');rect(793,291,589,200,'#2b2531');
  label('开场时间    ／    SHOWTIME',812,340,23,muted,600,cssFont);
  const blink=changed&&t<shot.switch+.11;
  label(blink?'--:--':changed?job.late:job.early,803,457,135,changed?red:cream,700,mono);
  rail(814,478,548,'#635264');
}
function paper(x,y,w,h,color,angle=0) {
  ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.shadowColor='#27182565';ctx.shadowBlur=25;ctx.shadowOffsetY=10;rect(0,0,w,h,color);ctx.restore();
}
function question(t) {
  rect(0,0,W,H,'#e4d6b9');
  for(let i=0;i<9;i++)line(0,55+i*101,W,55+i*101,'#c9bb9f',1);
  label('后台  ／  执行组',78,103,26,'#584b43');
  label(copy.problem[0],66,367,102,dark,800);label(copy.problem[1],68,495,106,dark,800);
  line(79,538,550,538,'#a94432',5);
  label(copy.oldSheet,79,722,30,'#4c423d',500);
  const pull=smooth((t-shot.question)/.45);
  const x=794+55*(1-pull), y=107;
  paper(x+24,y+16,564,660,'#d0c0a0',.025);
  ctx.save();ctx.translate(x,y);ctx.rotate(-.042);
  rect(0,0,564,660,cream);rect(0,0,564,17,red);
  label('执行台本',42,94,53,dark,800);label('变更前',405,89,27,'#ad422e');
  for(let i=0;i<proof.before.length;i++){
    const row=proof.before[i], data=row.match(/^(\d\d:\d\d)(.*?)(?:\d+ 分|—)$/);
    const yy=207+i*106;
    line(45,yy-65,520,yy-65,'#b9ad95');
    label(data?data[1]:row.slice(0,5),43,yy,52,dark,600,mono);
    label(data?data[2]:row.slice(5),275,yy-4,33,dark,600);
    const p=smooth((t-shot.question-.72-i*.19)/.26);
    if(p)line(40,yy-12,40+164*p,yy-28,'#d04430',5);
  }
  ctx.restore();
}
function cursor(x,y,press) {
  ctx.save();ctx.translate(x,y);ctx.scale(1-.12*press,1-.12*press);
  if(press>.04){ctx.strokeStyle='#ff6849';ctx.lineWidth=4;ctx.beginPath();ctx.arc(0,0,10+24*press,0,2*Math.PI);ctx.stroke();}
  const p=[[0,0],[3,35],[12,26],[21,43],[29,38],[21,22],[35,21]];
  polygon(p,'#fffdf6');ctx.strokeStyle='#302333';ctx.lineWidth=3;ctx.stroke();ctx.restore();
}
function position(sel) { const r=bounds[sel];return [r.x+r.width*.59,r.y+r.height*.58]; }
function point(a,b,p){return a.map((v,i)=>v+(b[i]-v)*smooth(p));}
function screenCrop(img,source,dest) {
  const [x,y,w,h]=source,[u,v,dw,dh]=dest;
  ctx.drawImage(img,x*img.width/1180,y*img.height/555,w*img.width/1180,h*img.height/555,u,v,dw,dh);
}
function ui(t) {
  rect(0,0,W,H,dark);
  label(t<shot.rebuild?copy.edit:copy.applied,73,89,52,cream,750);label('倒场    /    工作界面',1200,83,24,muted);
  const source=t<shot.edit?frames.before:t<shot.rebuild?frames.edited:frames.after;
  const start=[1030,470], edit=position('#show'), build=position('#rebuild');
  let pos=point(start,edit,(t-shot.interface)/1.25);
  if(t>shot.edit+.45)pos=point(edit,build,(t-shot.edit-.45)/1.05);
  if(t>shot.rebuild+.35)pos=point(build,[542,488],(t-shot.rebuild-.35)/.48);
  const x=72,y=134,s=1392/1180;
  screenCrop(source,[0,0,1180,555],[x,y,1392,555*s]);
  cursor(x+pos[0]*s,y+pos[1]*s,Math.max(0,1-Math.abs(t-(t<shot.edit+.42?shot.edit:shot.rebuild))/.18));
}
function closeup(t) {
  rect(0,0,W,H,cream);
  label('倒排结果',77,102,28,'#744e43');rail(79,136,440,'#aa9b87');
  const row=copy.featureTask;
  label(job.tasks[row][0],71,317,96,dark,800);
  label(proof.before[row].slice(0,5),81,404,56,'#78665c',600,mono);
  line(78,385,245,377,'#a54736',4);
  label(proof.after[row].slice(0,5),68,544,128,'#ad3c29',700,mono);
  label('把这一版交给执行组。',80,725,30,'#51433d');
  const r=bounds['.sheet'], s=1.43, x=602,y=162;
  const sw=r.width+20,sh=r.height+20;
  ctx.shadowColor='#3a203a30';ctx.shadowBlur=32;ctx.shadowOffsetY=12;
  rect(x,y,sw*s,sh*s,'#d0bd9d');ctx.shadowBlur=0;ctx.shadowOffsetY=0;
  screenCrop(frames.after,[r.x-10,r.y-10,sw,sh],[x,y,sw*s,sh*s]);
  const pt=position('#download');
  const a=point([r.x+r.width*.48,r.y+r.height*.65],pt,(t-shot.closeup-1.25)/1.9);
  cursor(x+(a[0]-r.x+10)*s,y+(a[1]-r.y+10)*s,Math.max(0,1-Math.abs(t-shot.download)/.2));
}
function receipt(t) {
  rect(0,0,W,H,'#ff6751');
  const slide=1-smooth((t-shot.send)/.43), x=806,y=95+slide*85;
  label('导出的执行文件',77,108,30,'#541f23');rail(79,144,520,'#8e3b33');
  label(copy.payoff[0],62,365,122,dark,800);label(copy.payoff[1],62,520,122,dark,800);
  label(proof.filename,78,730,40,dark,600);line(78,751,339,751,dark,3);
  paper(x+16,y+18,618,658,'#c64737',.01);
  rect(x,y,617,658,cream);rect(x,y,617,14,dark);
  for(let i=0;i<25;i++)polygon([[x+i*25,y+657],[x+12.5+i*25,y+666],[x+25+i*25,y+657]],cream);
  const lines=proof.exported.trim().split(/\r?\n/);
  label(lines[0],x+48,y+97,43,dark,800);
  for(let i=1;i<lines.length;i++){
    const parts=lines[i].split(/ {2,}/), yy=y+148+i*82;
    line(x+44,yy-51,x+572,yy-51,'#c4b8a0');
    label(parts[0],x+46,yy,42,dark,600,mono);label(parts[1],x+253,yy-3,33,dark,600);if(parts[2])label(parts[2],x+484,yy-3,25,'#5b5048',500);
  }
  rail(x+47,y+552,521,'#a89a83');label('文本台本   /   UTF-8',x+47,y+598,23,'#69584d',500);
}
function brand(t) {
  stage(t,true);
  mark(77,101,1.1,red);label('倒场',162,153,65,cream,800);
  label(copy.signature[0],65,378,123,cream,800);label(copy.signature[1],67,527,125,red,800);
  label('打开附带的 product.html',79,695,33,cream,600);
  label('填上下一场演出的开场时间。',80,752,29,muted,500);
}
function seek(t) {
  ctx.setTransform(1,0,0,1,0,0);ctx.globalAlpha=1;
  if(t<shot.question)opening(t);else if(t<shot.interface)question(t);else if(t<shot.closeup)ui(t);
  else if(t<shot.send)closeup(t);else if(t<shot.brand)receipt(t);else brand(t);
}
const events=Object.entries(shot).filter(([key])=>key!=='end').map(([type,t])=>({type,t}));
register({duration:shot.end,fps:24,width:W,height:H,seek,meta:{events}});
seek(0);
