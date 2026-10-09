const pptxgen = require('pptxgenjs');
const path = require('path');
const fs = require('fs');
const os = require('os');
const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'Presentation craft';
pptx.subject = '版式与导出验证示例；所有数据均为演示数据';
pptx.title = '把科研汇报讲成一条清晰的论证';
pptx.company = 'Presentation craft';
pptx.lang = 'zh-CN';
pptx.theme = {headFontFace:'Microsoft YaHei', bodyFontFace:'Microsoft YaHei', lang:'zh-CN'};
const C = {ink:'142F3B', teal:'147D78', muted:'64727A', paper:'F4F5F1', white:'FFFFFF', line:'D9E1DE', orange:'C77532'};
const W = 13.333333, H = 7.5;
const shape = pptx.ShapeType;
function text(s, content, x, y, w, h, size=22, color=C.ink, bold=false, extra={}) {
  s.addText(content, {x,y,w,h,fontFace:'Microsoft YaHei',fontSize:size,color,bold,margin:0,breakLine:false,valign:'mid',...extra});
}
function rect(s,x,y,w,h,fill,line=fill) {
  s.addShape(shape.rect,{x,y,w,h,fill:{color:fill},line:{color:line,width:0.6}});
}
function rule(s,x,y,w,color=C.line) {
  s.addShape(shape.line,{x,y,w,h:0,line:{color,width:1}});
}
function page(n, title, section) {
  const s=pptx.addSlide(); s.background={color:C.paper};
  text(s,section.toUpperCase(),0.65,0.36,11,0.25,11,C.teal,true,{charSpacing:1.2});
  text(s,title,0.65,0.88,12.0,0.75,30,C.ink,true);
  rule(s,0.65,6.83,12.02);
  text(s,'PRESENTATION CRAFT  /  中文汇报与导出示例',0.65,6.98,9,0.22,10,C.muted);
  text(s,String(n).padStart(2,'0'),11.9,6.94,0.76,0.32,12,C.muted,false,{align:'right'});
  return s;
}
async function main() {
  const outDir = path.resolve(process.argv[2] || fs.mkdtempSync(path.join(os.tmpdir(), 'presentation-craft-demo-')));
  fs.mkdirSync(outDir, {recursive:true});
  const output = path.join(outDir, 'demo.pptx');
  if (fs.existsSync(output)) throw new Error('demo.pptx already exists; choose a new output directory');
  let s=pptx.addSlide(); s.background={color:C.ink};
  rect(s,0.66,0.72,0.5,0.06,C.orange);
  text(s,'RESEARCH PRESENTATION',0.66,1.03,10,0.35,13,'90BCB6',true,{charSpacing:1.5});
  text(s,'把科研汇报\n讲成一条清晰的论证',0.65,1.88,8.05,1.93,38,C.white,true,{lineSpacingMultiple:1.1});
  text(s,'问题 → 方法 → 证据 → 边界',0.69,4.34,8,0.5,22,'B9CFCB');
  text(s,'每页回答一个问题\n每个结论保留证据',9.35,2.25,3.2,1.35,22,C.white,true,{lineSpacingMultiple:1.18});
  rule(s,9.35,4.03,2.96,'42616A');
  text(s,'01  组织内容\n02  设计版式\n03  审查实际导出',9.35,4.42,3.1,1.26,16,'B9CFCB',false,{lineSpacingMultiple:1.35});
  text(s,'六页能力验证示例 · 演示数据不对应真实实验',0.69,6.71,11.8,0.3,12,'9CB8B6');
  s.addNotes('本稿用于检验中文混排、原生图表、图片、表格、备注以及实际 PPTX 渲染，不作为科研结果。开场先说听众将获得什么，再介绍结构。');

  s=page(2,'先讲清楚问题，再给听众一条理解证据的路径','01 / Story');
  text(s,'听众需要带走的主旨',0.65,2.04,4.05,0.42,16,C.teal,true);
  text(s,'方法为什么有效，\n证据支持到哪里？',0.65,2.78,4.45,1.18,29,C.ink,true);
  text(s,'先写一句回答，再安排支撑这句话的图表。\n细节放在讲稿备注和附录。',0.65,4.6,4.5,1.25,18,C.muted,false,{lineSpacingMultiple:1.3});
  const story=[['问题','现有方法有什么具体不足'],['方法','哪个机制有望解决不足'],['证据','主比较、消融与失败样例'],['边界','适用条件及尚未解决的部分']];
  story.forEach((p,i)=>{let y=2.0+i*1.08; text(s,String(i+1).padStart(2,'0'),5.52,y,0.5,0.43,17,C.teal,true); text(s,p[0],6.22,y,1.0,0.43,22,C.ink,true); text(s,p[1],7.68,y,4.95,0.5,20,C.muted); if(i<3)rule(s,6.22,y+0.78,6.4);});
  s.addNotes('长标题用于检验中文标题排版。汇报结构是可调整的建议，不机械规定页数。课程报告可以将主线替换为概念、例子、应用和局限。先确认听众背景与时间，再决定哪些细节进入正文。');

  s=page(3,'让主比较成为页面焦点，同时交代数字的边界','02 / Evidence');
  text(s,'指标得分（%） · 示意数据',0.74,1.96,7.2,0.35,14,C.muted);
  s.addChart(pptx.ChartType.bar,[{name:'得分',labels:['Baseline','Method A','Method B'],values:[71,79,84]}],{
    x:0.7,y:2.42,w:7.3,h:3.84,barDir:'col',catAxisLabelFontFace:'Microsoft YaHei',catAxisLabelFontSize:16,
    valAxisLabelFontFace:'Microsoft YaHei',valAxisLabelFontSize:12,valAxisMinVal:0,valAxisMaxVal:100,valAxisMajorUnit:20,
    showLegend:false,showTitle:false,showValue:true,dataLabelPosition:'outEnd',dataLabelFormatCode:'0',dataLabelColor:C.ink,
    dataLabelBkgrdColor:C.paper,dataLabelFormatCodeSourceLinked:false,dataLabelFontSize:18,
    chartColors:['ABC4BF','73A7A1',C.teal],showBorder:false,
    catAxisLineShow:false,valAxisLineShow:false,valGridLine:{color:C.line,width:0.6},
    showMarker:false,showShadow:false,showSerName:false,gapSizePct:90,
    showPercent:false,showLabel:false,
    showChartBorder:false,showPlotArea:false,
    chartArea:{fill:{color:C.paper},line:{color:C.paper}},plotArea:{fill:{color:C.paper},line:{color:C.paper}}
  });
  text(s,'突出一项主比较',8.67,2.22,3.9,0.52,24,C.ink,true);
  rect(s,8.68,3.09,0.08,2.55,C.teal);
  text(s,'13',9.08,3.02,2.7,0.88,48,C.teal,true);
  text(s,'百分点的示例差异',9.1,3.98,3.25,0.44,17,C.ink,true);
  text(s,'实际汇报还应交代样本量、\n数据集、重复次数和误差。',9.1,4.82,3.2,1.0,17,C.muted,false,{lineSpacingMultiple:1.3});
  text(s,'数据来源：人工构造的 71 / 79 / 84，仅用于版式验证，不代表实测性能。',0.76,6.43,11.8,0.23,11,C.muted);
  s.addNotes('三个数值均为人工演示数据。84 减 71 等于 13 个百分点；不称为提高 13%。图表是原生 PowerPoint 图表，保留分类和数据；纵轴从零起。真实任务必须保留统计误差和数据来源。');

  s=page(4,'原始图、过程图与数据图，承担不同的表达职责','03 / Figures');
  s.addImage({path:path.join(__dirname,'assets','illustration.png'),x:0.66,y:2.17,w:6.24,h:4.16});
  text(s,'图 A · 人工示意热图，用于测试图片与图注',0.72,6.44,6.5,0.24,11,C.muted);
  text(s,'原始科研图',7.55,2.22,4.9,0.4,22,C.ink,true);
  text(s,'保留轴、图例与重要标注；裁切不能改变\n结论，也不能凭生成式重画替换原数据。',7.55,2.83,4.92,0.87,18,C.muted,false,{lineSpacingMultiple:1.25});
  rule(s,7.55,4.0,4.95);
  text(s,'方法流程',7.55,4.35,4.8,0.42,22,C.ink,true);
  ['输入','处理','结果'].forEach((item,i)=>{const x=7.55+i*1.74;rect(s,x,5.1,1.45,0.64,i===1?C.teal:'E3EAE5');text(s,item,x,5.2,1.45,0.38,17,i===1?C.white:C.ink,true,{align:'center'}); if(i<2)text(s,'→',x+1.48,5.24,0.23,0.3,16,C.muted);});
  text(s,'用原生形状说明因果关系，便于后续修改。',7.55,6.02,4.95,0.46,15,C.muted);
  s.addNotes('左侧热图由固定规则绘制，是清晰标注的示意资产，不是论文原图。本页检验位图可读性与图注关联。真实科研任务保留原图与原文出处，流程可以独立重绘但不能改变科研数据。');

  s=page(5,'按交付用途选择输出，明确什么可以继续编辑','04 / Delivery');
  s.addTable([
    [{text:'输出',options:{bold:true}},{text:'可编辑内容',options:{bold:true}},{text:'适合的需求',options:{bold:true}}],
    ['原生 PPTX','文本、表格、形状与原生图表','需要老师或同学继续修改'],
    ['网页演示','源稿、样式与支持的组件','公式、代码和交互展示'],
    ['图片式 PPTX','整页图像及部分备注','固定展示，且接受编辑限制'],
    ['PDF','固定页面；保留可重建源稿','分发阅读与版面确认']
  ],{x:0.65,y:2.16,w:12.03,h:3.74,colW:[2.75,4.65,4.63],rowH:[0.68,0.8,0.8,0.8,0.8],fontFace:'Microsoft YaHei',fontSize:18,
    color:C.ink,border:{type:'solid',color:C.line,pt:0.7},fill:C.white,margin:0.16,
    autoPage:false,verbose:false,
    bold:false,align:'left',valign:'mid'});
  rect(s,0.65,6.17,0.08,0.39,C.orange);
  text(s,'扩展名为 .pptx，并不等于整稿都能编辑；应查看实际对象与最终导出。',0.91,6.11,11.75,0.54,17,C.muted);
  s.addNotes('这是交付能力分类，不承诺任何工具完整支持所有 PowerPoint 功能。网页转原生 PPTX 的支持范围依实现和版本而定。要交付源稿及实际使用的本地素材。实际 Office 与 LibreOffice 的渲染可能不同，应有余量。');

  s=page(6,'把完成标准放在实际成品上，而不是生成成功上','05 / Review');
  text(s,'内容可信\n画面可读\n交付可用',0.65,2.31,4.2,2.2,32,C.ink,true,{lineSpacingMultiple:1.2});
  const checks=[['内容','来源、单位、数字和局限都能追溯'],['视觉','逐页检查标题、图表、图注及留白'],['版本','修改后重查导出，预览对应最终文件']];
  checks.forEach((p,i)=>{let y=2.08+i*1.36;text(s,p[0],5.68,y,1.4,0.45,22,C.teal,true);text(s,p[1],7.33,y,5.29,0.6,20,C.ink);rule(s,5.68,y+0.92,6.99);});
  text(s,'工具负责生成；好的内容与设计，需要持续判断和修订。',0.67,6.2,11.95,0.39,19,C.muted);
  s.addNotes('最后解释验证范围：结构检查不判断审美；实际看图不替代事实核对；记录通过也不是独立人工验收。若材料不足，说明缺口，不虚构数据和来源。免费路线不需要额外付费模型 API，但宿主 AI 仍使用用户已有额度。');
  await pptx.writeFile({fileName:output});
  console.log(output);
}
main().catch(error=>{console.error(error);process.exitCode=1;});
