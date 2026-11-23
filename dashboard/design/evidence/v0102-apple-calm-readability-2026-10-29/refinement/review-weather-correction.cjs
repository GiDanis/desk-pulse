const {chromium}=require('/home/giuseppe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:992,height:1800},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file://'+path.join(__dirname,'preview.html'));
 const fr=page.frameLocator('iframe');await fr.locator('.rf-app').first().waitFor();
 const f=page.frames().find(x=>x.parentFrame());await f.evaluate(()=>document.fonts.ready);
 async function show(layout,data='complete',palette='day',scale=1.1){
  await f.evaluate(({layout,data,palette,scale})=>{
   document.querySelectorAll('[data-variant]').forEach(s=>s.hidden=s.querySelector('.rf-app')?.dataset.layout!==layout);
   refinementMock.set({view:'weather',data,palette,scale});
  },{layout,data,palette,scale});
 }
 const geometry=[];
 for(const viewport of [992,768,392,352]){
  await page.setViewportSize({width:viewport,height:2200});
  for(const layout of ['grouped','open'])for(const data of ['complete','partial']){
   await show(layout,data);
   const details=await f.evaluate(layout=>{
    const app=document.querySelector('[data-layout="'+layout+'"]'),box=app.getBoundingClientRect();
    const leaves=[...app.querySelectorAll('span,strong,p,h2,h3,small')].filter(n=>!n.children.length&&n.textContent.trim());
    const outside=leaves.filter(n=>{const b=n.getBoundingClientRect();return b.width&&b.height&&(b.left<box.left-1||b.right>box.right+1||b.bottom>box.bottom+1);}).map(n=>n.textContent.trim());
    const cards=[...app.querySelectorAll('.rf-forecast .rf-card')];
    const cardOverflow=cards.flatMap(card=>[...card.querySelectorAll('span,strong')].filter(n=>{const c=card.getBoundingClientRect(),b=n.getBoundingClientRect();return b.left<c.left-1||b.right>c.right+1;}).map(n=>n.textContent));
    const footerOverlap=app.querySelector('.rf-main').getBoundingClientRect().bottom>app.querySelector('.rf-footer').getBoundingClientRect().top;
    return {width:box.width,height:box.height,outside,cardOverflow,footerOverlap,dailyCount:cards.length,body:cards.map(c=>c.textContent)};
   },layout);
   geometry.push({viewport,layout,data,...details});
  }
 }
 await page.setViewportSize({width:992,height:1200});
 const captures=[];
 for(const layout of ['grouped','open'])for(const [palette,scale,data] of [['day',1,'complete'],['night',1,'complete'],['day',1.1,'partial']]){
  await show(layout,data,palette,scale);
  const app=fr.locator('[data-layout="'+layout+'"]'),box=await app.boundingBox();
  const name=['weather',layout,palette,scale===1.1?'110':'100',data].join('-')+'.png';
  await app.screenshot({path:path.join(__dirname,'screens',name)});captures.push({name,width:box.width,height:box.height});
 }
 const fragment=path.resolve(__dirname,'../../../concepts/v0102-apple-calm/apple-calm-refinement.html');
 const report={scope:'Only changed weather concept; three dated daily forecasts, no new runtime/provider fields',fragmentSha256:crypto.createHash('sha256').update(fs.readFileSync(fragment)).digest('hex'),errors,captures,geometry};
 fs.writeFileSync(path.join(__dirname,'review-weather-correction.json'),JSON.stringify(report,null,2)+'\n');
 const problems=geometry.filter(x=>x.outside.length||x.cardOverflow.length||x.footerOverlap||x.dailyCount!==3||(x.width===960&&x.height!==640));
 console.log(JSON.stringify({errors,captures:captures.length,geometryCases:geometry.length,problems}));
 await browser.close();if(problems.length||errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
