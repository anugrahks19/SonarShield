const {chromium}=require(process.env.MODULE2_PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'.temp/module2-m211-gateway-browser-20261004');
(async()=>{
 fs.mkdirSync(out,{recursive:false});const browser=await chromium.launch({channel:'msedge',headless:true});const results=[];
 const host='https://mrintrovert19-sonar-shield-api.hf.space';
 const config={root:host,api_prefix:'/gradio_api',protocol:'sse',enable_queue:false,run_history:false,
  components:[{id:1,type:'file',props:{}},{id:2,type:'checkbox',props:{}},{id:3,type:'json',props:{}}],
  dependencies:[{id:0,api_name:'analyze_image_gradio',inputs:[1,2],outputs:[3],queue:false,api_visibility:'public',types:{generator:false}}]};
 const info={named_endpoints:{'/analyze_image_gradio':{parameters:[{parameter_name:'image_filepath',parameter_has_default:false,component:'File',type:{type:'string'}},{parameter_name:'run_tiled_auxiliary',parameter_has_default:true,parameter_default:true,component:'Checkbox',type:{type:'boolean'}}],returns:[{component:'JSON',type:{type:'object'}}]}},unnamed_endpoints:{}};
 const sample=JSON.parse(fs.readFileSync(path.join(root,'frontend/public/contact-105.json'),'utf8'));
 try{
  for(const mode of ['mock_success','mock_quota_countdown','mock_quota_no_countdown']){
   const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});const page=await context.newPage();
   let gatewayCalls=0,upstreamInferenceCalls=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
   const receivedAt=new Date().toISOString();
   await context.route('**/*',async route=>{
    const url=route.request().url(),u=new URL(url);
    const json=(payload,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(payload)});
    if(u.pathname==='/api/analyze'){
     gatewayCalls++;
     if(mode==='mock_success')return json(sample);
     const details={upstreamMessage:'You have exceeded your ZeroGPU runs limit. '+(mode==='mock_quota_countdown'?'Try again in 0:05:00.':''),receivedAt,
       ...(mode==='mock_quota_countdown'?{resetAt:new Date(Date.now()+300000).toISOString(),resetAfterSeconds:300}:{})};
     return json({error:{code:'GPU_QUOTA_EXCEEDED',message:'Live inference is unavailable because the authenticated service account GPU limit was reached. Your image was not analyzed.',details}},429);
    }
    if(/huggingface\.co|\.hf\.space/.test(u.hostname)){
     if(/\/queue\/join|\/gradio_api\/(call|run)/.test(u.pathname)){upstreamInferenceCalls++;return route.abort();}
     if(u.pathname.endsWith('/host'))return json({host});
     if(u.pathname.endsWith('/config'))return json(config);
     if(u.pathname.endsWith('/info'))return json(info);
     if(u.pathname.endsWith('/upload'))return json(['/tmp/gradio/qa/image.jpg']);
     if(u.pathname.endsWith('/upload_progress'))return route.fulfill({contentType:'text/event-stream',body:'event: complete\ndata: {}\n\n'});
     return json({runtime:{stage:'RUNNING'}});
    }
    return route.continue();
   });
   await page.goto('http://127.0.0.1:8782/analysis');await page.getByRole('button',{name:'Run analysis',exact:true}).waitFor();
   await page.locator('input[type=file]').first().setInputFiles(path.join(root,'frontend/public/contact-105.jpg'));
   await page.getByRole('button',{name:'Run analysis',exact:true}).click();
   if(mode==='mock_success'){
    await page.getByRole('button',{name:'View report',exact:true}).waitFor();
    assert.ok((await page.locator('.judge-source-banner').first().innerText()).includes('LIVE ANALYSIS'));
    await page.getByRole('button',{name:'View report',exact:true}).click();
    await page.getByRole('heading',{name:'MARINE ANOMALY ANALYSIS REPORT',exact:true}).waitFor();
    assert.match(await page.locator('.report-source-banner').innerText(),/LIVE ANALYSIS/);
    const promise=page.waitForEvent('download');await page.getByRole('button',{name:'Export JSON',exact:true}).click();
    const download=await promise;const file=path.join(out,'mock-live-report.json');await download.saveAs(file);
    assert.equal(JSON.parse(fs.readFileSync(file,'utf8')).result_source,'LIVE_ANALYSIS');
   }else{
    await page.getByRole('button',{name:'View verified example',exact:true}).waitFor();
    assert.equal(await page.locator('.judge-source-banner').count(),0);
    await page.getByText('Technical details',{exact:true}).click();assert.match(await page.locator('pre').innerText(),/ZeroGPU runs limit/);
    const text=await page.locator('body').innerText();
    assert.ok(text.includes(mode==='mock_quota_countdown'?'Hugging Face reported reset in':'Reset time was not supplied by Hugging Face.'));
    await page.getByRole('button',{name:'View verified example',exact:true}).click();await page.getByRole('button',{name:'Load precomputed example',exact:true}).click();
    await page.getByRole('button',{name:'View report',exact:true}).waitFor();
    assert.ok((await page.locator('.judge-source-banner').first().innerText()).includes('NOT LIVE INFERENCE'));
   }
   assert.equal(gatewayCalls,1,'No automatic retry or additional inference during fallback');assert.equal(upstreamInferenceCalls,0);assert.deepEqual(errors,[]);
   await page.screenshot({path:path.join(out,mode+'.png'),fullPage:true});
   results.push({mode,passed:true,mocked_gateway_calls:gatewayCalls,real_inference_calls:0,page_errors:errors});
   await context.close();console.log(mode+' browser scenario passed');
  }
  fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({scope:'FULLY_MOCKED_HF_AND_GATEWAY_NOT_REAL_LIVE_VERIFICATION',results},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exit(1);});
