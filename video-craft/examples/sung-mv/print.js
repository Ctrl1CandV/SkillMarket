// Shared motifs for the four pieces of cut-paper scenery. All coordinates are in artboard units.
import { clamp, rng } from '../../kit/kit.js';

export const P = {
  ink:'#143d3e', pine:'#225553', sea:'#43817b', jade:'#76aaa0', mist:'#adcbad',
  paper:'#f3dfad', white:'#fff0c6', straw:'#e7bd70', red:'#ee5c40', scarlet:'#c93e32',
  rust:'#a3312c', pink:'#f6966e', earth:'#936a47', skin:'#edac72', skinDeep:'#c67753',
};
export const C = document.getElementById('film').getContext('2d',{alpha:false});
export const smooth = x => { x=clamp(x); return x*x*(3-2*x); };
export function path(shape, color, stroke, width=1) {
  const p=new Path2D(shape);
  if(color){C.fillStyle=color; C.fill(p);}
  if(stroke){C.strokeStyle=stroke; C.lineWidth=width; C.stroke(p);}
}
export function line(points,color,width=1) {
  C.beginPath(); points.forEach(([x,y],i)=>i ? C.lineTo(x,y) : C.moveTo(x,y));
  C.strokeStyle=color; C.lineWidth=width; C.stroke();
}
export function poly(points,color) {
  C.beginPath(); points.forEach(([x,y],i)=>i ? C.lineTo(x,y) : C.moveTo(x,y));
  C.closePath(); C.fillStyle=color; C.fill();
}
export function rect(x,y,w,h,color){C.fillStyle=color;C.fillRect(x,y,w,h);}
export function ellipse(x,y,a,b,color) {
  C.beginPath(); C.ellipse(x,y,a,b,0,0,Math.PI*2); C.fillStyle=color; C.fill();
}
export function cloud(x,y,k,color) {
  C.save(); C.translate(x,y); C.scale(k,k);
  path('M-161 23 Q-127 18 -100 10 Q-84 -13 -60 -9 Q-44 -30 -21 -18 Q2 -54 33 -42 Q61 -43 78 -16 Q109 -20 122 -2 Q153 0 171 12 L231 19 L139 22 L91 28 L-37 31 Z',color);
  C.restore();
}
export function postmark(x,y,r,col) {
  C.save(); C.translate(x,y); C.rotate(-.18);
  C.strokeStyle=col; C.lineWidth=r*.063;
  for(const f of [1,.82]){C.beginPath(); C.arc(0,0,r*f,-.9,4.98); C.stroke();}
  const unit=r/40; C.scale(unit,unit);
  line([[-22,8],[-3,-12],[16,8]],col,2.1);
  line([[-5,5],[3,-2],[15,9]],col,1.3);
  line([[-20,13],[21,13]],col,1.7);
  for(let i=0;i<3;i++)path('M26 '+(-9+i*9)+' q12 -5 24 -1 t24 -1',null,col,1.4);
  C.restore();
}

// Shared triangle fan. The tail, high wing, notch, neck and bent beak read separately in silhouette.
const sheet=[[-167,-92],[-95,-94],[-14,-97],[70,-95],[165,-91],[167,-41],
             [166,22],[163,91],[55,96],[-34,96],[-165,89]];
function rim(flap){
  return [[-148,-24],[-43,-3],[-88,-105-flap*25],[14,-23],[82,-74],[111,-51],
          [84,-57],[39,14],[-7,34],[-92,72+flap*19],[-57,17]];
}
export function bird(x,y,k,angle,fold,flap=0){
  C.save(); C.translate(x,y); C.rotate(angle); C.scale(k,k);
  const dest=rim(flap);
  const colors=[P.pink,P.scarlet,P.red,P.rust,P.scarlet,P.rust,P.pink,P.scarlet,P.rust,P.scarlet,P.red];
  const colorsFlat=['#ef674a','#ed6547','#f06a49','#f36d4e','#f37050','#eb6748',
                    '#ed694a','#ef6848','#eb6043','#e95e40','#ef6948'];
  function blend(a,b){return a.map((v,i)=>v+(b[i]-v)*fold);}
  sheet.forEach((vertex,i)=>{
    const next=(i+1)%sheet.length;
    const points=[blend(vertex,dest[i]),blend(sheet[next],dest[next]),blend([-22,12],[6,6])];
    poly(points,colorsFlat[i]);
    C.save(); C.globalAlpha=fold; poly(points,colors[i]); C.restore();
    if(fold>.18){C.save();C.globalAlpha=.28*fold;line([points[0],points[1]],P.white,1.15);C.restore();}
  });
  // Model the ink as a stamp on a rigid patch of the wing. An affine warp of the whole
  // fan triangle crushes the circles into lines when the wing is nearly edge-on.
  const stamp=blend([-57,-39],[-23,-37-flap*7]);
  C.save();C.translate(...stamp);C.rotate(-.16+1.03*fold);
  C.scale(1,.95-.28*fold);
  const radius=19-6*fold;
  ellipse(0,0,radius*1.04,radius*1.04,P.pink);
  postmark(0,0,radius,P.rust);C.restore();
  if(fold>.54){
    C.save(); C.globalAlpha=smooth((fold-.54)/.46);
    ellipse(82,-64,2,2,P.ink);
    const tip=rim(flap)[2];
    for(let j=0;j<3;j++)line([[tip[0]+23+j*5,tip[1]+27+j*5],[tip[0]+38+j*7,tip[1]+49+j*7]],P.pink,.8);
    C.restore();
  }
  C.restore();
}

const random=rng(20);
const texture=document.createElement('canvas'); texture.width=texture.height=384;
const tc=texture.getContext('2d'), data=tc.createImageData(384,384);
for(let i=0;i<data.data.length;i+=4){
  const r=random(); const shade=r<.5?15:250;
  data.data[i]=data.data[i+1]=data.data[i+2]=shade;
  data.data[i+3]=Math.floor(8+29*random());
}
tc.putImageData(data,0,0);
for(let i=0;i<400;i++){
  const x=random()*384,y=random()*384;
  tc.strokeStyle=i%2?'#f1e3b841':'#203c352a';tc.lineWidth=.55+random()*.5;
  tc.beginPath();tc.moveTo(x,y);tc.lineTo(x+1+random()*4,y-2+random()*3);tc.stroke();
}
const grain=C.createPattern(texture,'repeat');
export function paperGrain(){
  C.save(); C.globalCompositeOperation='soft-light'; C.fillStyle=grain; C.fillRect(0,0,1200,750); C.restore();
}
