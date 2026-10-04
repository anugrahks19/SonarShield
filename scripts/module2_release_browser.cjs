const {chromium}=require(process.env.MODULE2_PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'.temp/module2-m211-browser-20261004');
const label='PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE';
(async()=>{
 fs.mkdirSync(out,{recursive:false});
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const results=[];
 try{
  for(const [name,base] of [['local','http://127.0.0.1:8782'],['public','https://sonarshield26.vercel.app']]){
   const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
   const page=await context.newPage();const errors=[];let inferenceCalls=0,spaceRequestsBlocked=0;
   page.on('pageerror',e=>errors.push(e.message));
   await context.route('**/*',async route=>{
    const url=route.request().url();
    if(/\/api\/analyze(?:\?|$)|\/queue\/join|\/gradio_api\/call/.test(url)){inferenceCalls++;return route.abort();}
    if(/huggingface\.co|\.hf\.space/.test(url)){spaceRequestsBlocked++;return route.abort();}
    return route.continue();
   });
   const response=await page.goto(base+'/analysis');assert.equal(response.status(),200);
   await page.getByRole('button',{name:'Explore verified examples',exact:true}).waitFor();
   await page.locator('input[type=file]').first().setInputFiles(path.join(root,'frontend/public/contact-105.jpg'));
   await page.getByRole('button',{name:'Run analysis',exact:true}).click();
   await page.getByRole('button',{name:'View verified example',exact:true}).waitFor();
   assert.match(await page.locator('.upload-bar').count()?await page.locator('body').innerText():await page.locator('body').innerText(),/contact-105/);
   assert.equal(await page.locator('.judge-source-banner').count(),0,'No automatic example substitution');
   await page.getByRole('button',{name:'View verified example',exact:true}).click();
   await page.getByRole('heading',{name:'Explore a previously completed sonar analysis'}).waitFor();
   await page.getByRole('button',{name:'Load precomputed example',exact:true}).click();
   await page.getByRole('button',{name:'View report',exact:true}).waitFor();
   assert.equal(await page.locator('.judge-source-banner').first().innerText().then(x=>x.includes(label)),true);
   await page.getByRole('row',{name:/Candidate 1,/}).click();
   await page.getByRole('button',{name:'Needs investigation',exact:true}).click();
   const note='M2.11 isolated browser QA; precomputed sample review only.';
   await page.getByRole('textbox',{name:'REVIEWER NOTES'}).fill(note);
   await page.getByRole('button',{name:'Save review',exact:true}).click();
   await page.getByRole('dialog').getByRole('button',{name:'Confirm review',exact:true}).click();
   await page.reload();await page.getByRole('button',{name:'View report',exact:true}).waitFor();
   await page.getByRole('row',{name:/Candidate 1,/}).click();
   assert.equal(await page.getByRole('textbox',{name:'REVIEWER NOTES'}).inputValue(),note);
   const completePromise=page.waitForEvent('download');await page.getByRole('button',{name:'Export complete record',exact:true}).click();
   const complete=await completePromise;const recordPath=path.join(out,name+'-complete.sonar.json');await complete.saveAs(recordPath);
   const record=JSON.parse(fs.readFileSync(recordPath,'utf8'));assert.equal(record.source,'PRECOMPUTED_EXAMPLE');assert.ok(record.reviews.some(r=>r.note===note));
   const chooserPromise=page.waitForEvent('filechooser');await page.getByRole('button',{name:'Import complete record',exact:true}).click();await (await chooserPromise).setFiles(recordPath);
   await page.getByRole('button',{name:'View report',exact:true}).click();
   await page.getByRole('heading',{name:'MARINE ANOMALY ANALYSIS REPORT',exact:true}).waitFor();
   assert.ok((await page.locator('.report-source-banner').innerText()).includes(label));
   for(const format of ['JSON','CSV']){
    const promise=page.waitForEvent('download');await page.getByRole('button',{name:'Export '+format,exact:true}).click();
    const download=await promise;const destination=path.join(out,name+'-report.'+format.toLowerCase());await download.saveAs(destination);
    assert.ok(fs.readFileSync(destination,'utf8').includes(label));
   }
   await page.screenshot({path:path.join(out,name+'-report.png'),fullPage:true});
   await page.emulateMedia({media:'print'});assert.equal(await page.locator('.report-source-banner').isVisible(),true);
   await page.screenshot({path:path.join(out,name+'-print.png'),fullPage:true});await page.emulateMedia({media:'screen'});
   await page.getByRole('button',{name:'← Analysis',exact:true}).click();
   await page.setViewportSize({width:390,height:844});
   await page.getByRole('button',{name:'View report',exact:true}).waitFor();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+2),'Mobile page must not overflow horizontally');
   await page.screenshot({path:path.join(out,name+'-mobile.png'),fullPage:true});
   assert.equal(inferenceCalls,0,'Fallback must make zero Space inference calls');assert.deepEqual(errors,[]);
   results.push({target:name,url:base,http_status:200,mode:'SIMULATED_SPACE_OFFLINE_REAL_BROWSER_NO_HF_CALLS',
    explicit_fallback:true,viewer_review_refresh_restore:true,complete_record_export_import:true,
    json_csv_print_labels:true,mobile_no_page_overflow:true,page_errors:errors,inference_calls:inferenceCalls,
    blocked_space_reachability_requests:spaceRequestsBlocked,cloud_signed_in_check:'NOT_REPEATED_NO_REVIEWER_CREDENTIAL_IN_ISOLATED_CONTEXT'});
   await context.close();console.log(name+' browser walkthrough passed');
  }
  fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({browser:'Microsoft Edge headless',results},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exit(1);});
