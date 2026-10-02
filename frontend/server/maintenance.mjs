import { createHash,timingSafeEqual } from 'node:crypto';
import { configuration,rpc } from './supabase.mjs';
export function createMaintenance({env=process.env,fetcher=fetch}={}) {
 return async(req,res)=>{
  res.setHeader('Cache-Control','no-store');res.setHeader('Content-Type','application/json');
  const send=(status,value)=>{res.statusCode=status;res.end(JSON.stringify(value));};
  if(req.method!=='GET'){send(405,{error:'METHOD_NOT_ALLOWED'});return;}
  const configured=env.CRON_SECRET||'';const supplied=String(req.headers.authorization||'').replace(/^Bearer /,'');
  if(configured.length<32||!timingSafeEqual(createHash('sha256').update(configured).digest(),createHash('sha256').update(supplied).digest())){send(401,{error:'UNAUTHORIZED'});return;}
  try {
   const config=configuration(env,true);const expired=await rpc(env,'sonar_expired_records',{},undefined,fetcher,true);
   if(!Array.isArray(expired)||expired.length>8)throw Error();
   let removed=0;
   for(const record of expired){
    if(!/^[a-f0-9-]{36}$/.test(record.id)||!/^([a-f0-9-]{36})\/([a-f0-9-]{36})\/image\.(jpg|png)$/.test(record.image_path))throw Error();
    const headers={apikey:config.key,'Content-Type':'application/json'};if(config.key.split('.').length===3)headers.Authorization=`Bearer ${config.key}`;
    const response=await fetcher(`${config.url}/storage/v1/object/sonar-records`,{method:'DELETE',headers,body:JSON.stringify({prefixes:[record.image_path]}),signal:AbortSignal.timeout(5000),redirect:'error'});
    if(!response.ok)throw Error();await rpc(env,'sonar_prune_record',{p_id:record.id},undefined,fetcher,true);removed++;
   }
   send(200,{removed});
  }catch{send(503,{error:'RETENTION_UNAVAILABLE'});}
 };
}
