const {chromium} = require('/home/giuseppe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const dir = __dirname;
(async () => {
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:992,height:1120},deviceScaleFactor:1});
 const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file://'+path.join(dir,'preview.html'));
 const iframe=page.frameLocator('iframe');
 await iframe.locator('#calm-v0102 .ac-stage').first().waitFor();
 const frame=page.frames().find(f=>f.parentFrame());
 await frame.evaluate(()=>document.fonts.ready);
 const out=path.join(dir,'screens');fs.mkdirSync(out,{recursive:true});
 const captures=[];
 for(const screen of ['home','inbox','detail','weather','network','sport','settings','empty','offline','revoked','urgent']) {
  await frame.evaluate(screen=>acConcept.set({screen,palette:'day',textScale:1}),screen);
  const stage=iframe.locator('[data-layout="essential"]');
  const box=await stage.boundingBox();
  if(Math.abs(box.width-960)>1 || Math.abs(box.height-640)>1) throw Error('Target dimensions: '+screen+' '+JSON.stringify(box));
  await stage.screenshot({path:path.join(out,screen+'-day.png')});
  captures.push({screen,palette:'day',width:960,height:640});
 }
 for(const screen of ['home','inbox']){
  await frame.evaluate(screen=>acConcept.set({screen,palette:'night'}),screen);
  await iframe.locator('[data-layout="essential"]').screenshot({path:path.join(out,screen+'-night.png')});
 }
 await frame.evaluate(()=>{acConcept.set({screen:'home',palette:'day'});document.querySelector('[data-variant="Calm essenziale"]').hidden=true;document.querySelector('[data-variant="Calm laterale"]').hidden=false;});
 await iframe.locator('[data-layout="lateral"]').screenshot({path:path.join(out,'home-lateral-day.png')});
 await frame.evaluate(()=>{document.querySelector('[data-variant="Calm essenziale"]').hidden=false;document.querySelector('[data-variant="Calm laterale"]').hidden=true;acConcept.set({screen:'inbox',textScale:1.1});});
 await iframe.locator('[data-layout="essential"]').screenshot({path:path.join(out,'inbox-scale110.png')});
 const geometry=[];
 for(const width of [992,768,392,352]) {
  await page.setViewportSize({width,height:1600});
  for(const screen of ['home','inbox','detail','weather','network','sport','settings','empty','offline','revoked','urgent']){
   await frame.evaluate(screen=>acConcept.set({screen,palette:'day',textScale:1.1}),screen);
   const status=await frame.evaluate(()=>{
    const root=document.getElementById('calm-v0102');
    const stage=root.querySelector('[data-layout="essential"]');
    const box=stage.getBoundingClientRect();
    const overflow=[...stage.querySelectorAll('*')].filter(e=>{const b=e.getBoundingClientRect();return b.width&&b.height&&getComputedStyle(e).position!=='absolute'&&(b.right>box.right+1||b.left<box.left-1)}).map(e=>e.className?.baseVal??e.className).slice(0,8);
    const leafOverflow=[...stage.querySelectorAll('p,strong,span,h2,h3,time')].filter(e=>{
      if(e.children.length||!e.textContent.trim())return false;
      const b=e.getBoundingClientRect();return b.width&&b.height&&(b.bottom>box.bottom+1||b.right>box.right+1||b.left<box.left-1);
    }).map(e=>e.textContent.trim()).slice(0,8);
    const footer=stage.querySelector('.ac-footer'), rows=[...stage.querySelectorAll('.ac-row')];
    const footerOverlap=!!(footer&&rows.length&&rows.at(-1).getBoundingClientRect().bottom>footer.getBoundingClientRect().top-6);
    const banner=stage.querySelector('.ac-banner'), card=stage.querySelector('.ac-home .ac-card');
    const bannerOverlap=!!(banner&&card&&card.getBoundingClientRect().bottom>banner.getBoundingClientRect().top-8);
    return {width:box.width,height:box.height,overflow,leafOverflow,footerOverlap,bannerOverlap,icons:stage.querySelectorAll('svg.lucide').length};
   });
   geometry.push({viewport:width,screen,...status});
  }
 }
 // Primary interactions are local and produce an observable view change.
 await page.setViewportSize({width:992,height:1120});
 await iframe.locator('#ac-screen').selectOption('home');
 await iframe.locator('[data-layout="essential"] [data-action="inbox"]').click();
 await iframe.locator('[data-layout="essential"] .ac-row').first().click();
 const opened=await frame.evaluate(()=>acConcept.state.screen);
 await iframe.locator('#ac-screen').selectOption('inbox');
 await iframe.locator('[data-layout="essential"] .ac-row').nth(1).click();
 const weatherDetail=await iframe.locator('[data-layout="essential"] .ac-title').textContent();
 await iframe.locator('#ac-screen').selectOption('inbox');
 await iframe.locator('[data-layout="essential"] .ac-row').nth(2).click();
 const networkDetail=await iframe.locator('[data-layout="essential"] .ac-title').textContent();
 await iframe.locator('#ac-palette').selectOption('night');
 const palette=await iframe.locator('[data-layout="essential"]').getAttribute('data-palette');
 await iframe.locator('#ac-replay').click();
 const replay=await frame.evaluate(()=>acConcept.state.screen==='home'&&!!document.querySelector('.ac-banner.ac-animate'));
 await page.screenshot({path:path.join(dir,'preview-review.png'),fullPage:true});
 const report={scope:'Browser concept only; no QML, ARM, GPU or physical qualification',captures:captures.length+4,errors,interactions:{detailOpened:opened==='detail',weatherDetail:weatherDetail.includes('Avviso meteo'),networkDetail:networkDetail.includes('Router'),paletteChanged:palette==='night',bannerReplay:replay},geometry};
 fs.writeFileSync(path.join(dir,'concept-review.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({errors,interactions:report.interactions,geometryProblems:geometry.filter(r=>r.overflow.length||r.leafOverflow.length||r.footerOverlap||r.bannerOverlap),icons:geometry[0].icons,captures:report.captures}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
