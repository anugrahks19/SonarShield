export function configuration(env, secret = false) {
  let url;try { url=new URL(env.SUPABASE_URL); } catch { throw Error('SUPABASE_NOT_CONFIGURED'); }
  if (url.protocol!=='https:'||url.username||url.password||url.pathname!=='/'||url.search||url.hash) throw Error('SUPABASE_NOT_CONFIGURED');
  const key=secret?(env.SUPABASE_SECRET_KEY||env.SUPABASE_SERVICE_ROLE_KEY):env.SUPABASE_PUBLISHABLE_KEY;
  if(typeof key!=='string'||key.length<20)throw Error('SUPABASE_NOT_CONFIGURED');
  let role;try{role=JSON.parse(Buffer.from(key.split('.')[1],'base64url').toString()).role;}catch{ /* Modern API keys are opaque. */ }
  if(secret ? !(key.startsWith('sb_secret_')||role==='service_role') : !(key.startsWith('sb_publishable_')||role==='anon'))throw Error('SUPABASE_NOT_CONFIGURED');
  return {url:url.origin,key};
}
export async function rpc(env,name,args={},bearer,fetcher=fetch,secret=false) {
  const config=configuration(env,secret);const headers={'apikey':config.key,'Content-Type':'application/json'};
  if(bearer)headers.Authorization=`Bearer ${bearer}`;else if(config.key.split('.').length===3)headers.Authorization=`Bearer ${config.key}`;
  const response=await fetcher(`${config.url}/rest/v1/rpc/${name}`,{method:'POST',headers,body:JSON.stringify(args),signal:AbortSignal.timeout(5000),redirect:'error'});
  const value=await response.json().catch(()=>null);
  if(!response.ok)throw Object.assign(Error('SUPABASE_REQUEST_FAILED'),{dbCode:value?.code,status:response.status});
  return value;
}
export async function acquireSupabaseAdmission(env,fetcher=fetch) {
  let value;try { value=await rpc(env,'sonar_admission_acquire',{},undefined,fetcher,true); }
  catch(error){throw Object.assign(Error(error.dbCode==='P0001'?'The site live budget or concurrency limit was reached. No inference started; use a verified example or retry manually later.':'Live usage control is unavailable. No inference started.'),{admissionError:true,code:error.dbCode==='P0001'?'LIVE_USAGE_LIMIT':'LIVE_LIMITER_UNAVAILABLE',status:error.dbCode==='P0001'?429:503});}
  if(!/^[a-f0-9]{32}$/.test(value?.lease_id))throw Object.assign(Error('Live usage control returned invalid data.'),{admissionError:true,code:'LIVE_LIMITER_UNAVAILABLE',status:503});
  const uuid=value.lease_id.replace(/^(.{8})(.{4})(.{4})(.{4})(.{12})$/,'$1-$2-$3-$4-$5');
  return {release:async()=>{try{await rpc(env,'sonar_admission_release',{p_lease_id:uuid},undefined,fetcher,true);}catch{/* Retain until conservative expiry. */}}};
}
