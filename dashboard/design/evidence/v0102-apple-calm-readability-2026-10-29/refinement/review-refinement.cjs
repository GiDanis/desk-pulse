const {chromium}=require('/home/giuseppe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:992,height:1200},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file://'+path.join(__dirname,'preview.html'));
 const fr=page.frameLocator('iframe');await fr.locator('.rf-app').first().waitFor();
 const f=page.frames().find(x=>x.parentFrame());await f.evaluate(()=>document.fonts.ready);
 const out=path.join(__dirname,'screens');fs.mkdirSync(out,{recursive:true});
 const views=['network','weather','racing','casa','account','menu','icons'];
 async function show(layout,state){await f.evaluate(({layout,state})=>{document.querySelectorAll('[data-variant]').forEach(s=>s.hidden=s.querySelector('.rf-app')?.dataset.layout!==layout);refinementMock.set(state);},{layout,state});}
 const captures=[];
 async function capture(layout,view,palette='day',scale=1,data='complete'){
  await show(layout,{view,palette,scale,data,period:'1h',selected:0});
  const app=fr.locator('[data-layout="'+layout+'"]');
  const box=await app.boundingBox();const name=[view,layout,palette,scale===1.1?'110':'100',data].join('-')+'.png';
  await app.screenshot({path:path.join(out,name)});captures.push({name,width:box.width,height:box.height});
 }
 for(const layout of ['grouped','open'])for(const view of views)await capture(layout,view);
 for(const layout of ['grouped','open'])for(const view of ['network','casa'])await capture(layout,view,'night');
 for(const view of ['racing','account'])await capture('open',view,'day',1.1);
 for(const view of ['network','account'])await capture('open',view,'day',1,'partial');
 const geometry=[];
 for(const viewport of [992,768,392,352]){
  await page.setViewportSize({width:viewport,height:1800});
  for(const layout of ['grouped','open'])for(const view of views)for(const data of ['complete','partial']){
   await show(layout,{view,data,scale:1.1,palette:'day'});
   const result=await f.evaluate(layout=>{
    const app=document.querySelector('[data-layout="'+layout+'"]'),box=app.getBoundingClientRect();
    const leaves=[...app.querySelectorAll('span,strong,p,h2,h3,small,text')].filter(n=>!n.children.length&&n.textContent.trim());
    const outside=leaves.filter(n=>{const b=n.getBoundingClientRect();return b.width&&b.height&&(b.left<box.left-1||b.right>box.right+1||b.bottom>box.bottom+1);}).map(n=>n.textContent.trim()).slice(0,8);
    const footer=app.querySelector('.rf-footer'),rows=[...app.querySelectorAll('.rf-row')];
    const footerOverlap=!!(footer&&rows.length&&rows.at(-1).getBoundingClientRect().bottom>footer.getBoundingClientRect().top-6);
    const svg=app.querySelector('.rf-chart');const chartOverlaps=[];
    if(svg){const labels=[...svg.querySelectorAll('text')];for(let i=0;i<labels.length;i++)for(let j=i+1;j<labels.length;j++){const a=labels[i].getBoundingClientRect(),b=labels[j].getBoundingClientRect();if(a.left<b.right-2&&a.right>b.left+2&&a.top<b.bottom-2&&a.bottom>b.top+2)chartOverlaps.push([labels[i].textContent,labels[j].textContent]);}}
    return{width:box.width,height:box.height,outside,footerOverlap,chartOverlaps};
   },layout);
   geometry.push({viewport,layout,view,data,...result});
  }
 }
 await page.setViewportSize({width:992,height:1200});
 await show('open',{view:'network',data:'complete',scale:1});
 await fr.locator('[data-layout="open"] [data-period="24h"]').click();
 const period=await f.evaluate(()=>refinementMock.state.period);
 await fr.locator('#rf-view').selectOption('racing');await fr.locator('[data-layout="open"] [data-select="1"]').click();
 const selected=await f.evaluate(()=>refinementMock.state.selected);
 await fr.locator('#rf-view').selectOption('account');await fr.locator('#rf-data').selectOption('partial');
 const missing=await fr.locator('[data-layout="open"] .rf-usage .rf-card').nth(1).textContent();
 await fr.locator('#rf-palette').selectOption('night');
 const palette=await fr.locator('[data-layout="open"]').getAttribute('data-palette');
 await fr.locator('#rf-view').selectOption('menu');await fr.locator('[data-layout="open"] .rf-footer button').click();
 const menuLast=await fr.locator('[data-layout="open"] .rf-rows').textContent();
 await fr.locator('#rf-view').selectOption('network');
 const gapCount=await fr.locator('[data-layout="open"] .rf-data-line').first().getAttribute('d');
 const report={scope:'New browser concept only; no runtime, board, GPU, provider or physical-display qualification',errors,captures,geometry,interactions:{period:period==='24h',selected:selected===1,missing:missing.includes('Dato non disponibile'),palette:palette==='night',menuScroll:menuLast.includes('Diagnostica'),chartGaps:(gapCount.match(/M/g)||[]).length===2}};
 fs.writeFileSync(path.join(__dirname,'review.json'),JSON.stringify(report,null,2)+'\n');
 const problems=geometry.filter(x=>x.outside.length||x.footerOverlap||x.chartOverlaps.length||(x.width===960&&x.height!==640));
 console.log(JSON.stringify({errors,interactions:report.interactions,captures:captures.length,badCaptureSizes:captures.filter(c=>c.width!==960||c.height!==640),geometryCases:geometry.length,problems}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
