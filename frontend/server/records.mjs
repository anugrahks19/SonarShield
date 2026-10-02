import { configuration,rpc } from './supabase.mjs';
import { analyzeSchema } from '../src/api/schema.ts';
const uuid=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
export function createRecordsHandler({env=process.env,fetcher=fetch}={}) {
 return async(req,res)=>{
  res.setHeader('Cache-Control','no-store');res.setHeader('Content-Type','application/json');
  const send=(status,value)=>{res.statusCode=status;res.end(JSON.stringify(value));};
  try {
   const config=configuration(env);
   if(req.method==='GET'){send(200,{url:config.url,publishableKey:config.key,bucket:'sonar-records'});return;}
   if(req.method!=='POST'){send(405,{detail:'Use POST for records.'});return;}
   const expected=env.APP_ORIGIN||(env.VERCEL_URL?`https://${env.VERCEL_URL}`:env.NODE_ENV!=='production'?`http://${req.headers.host}`:null);
   if(req.headers.origin!==expected||!expected||(req.headers['sec-fetch-site']&&req.headers['sec-fetch-site']!=='same-origin')){send(403,{detail:'Record requests must come from this site.'});return;}
   const auth=req.headers.authorization;
   if(typeof auth!=='string'||!/^Bearer [A-Za-z0-9._-]{20,8192}$/.test(auth)){send(401,{detail:'Sign in to save or open shared records.'});return;}
   const token=auth.slice(7);
   const verified=await fetcher(`${config.url}/auth/v1/user`,{headers:{apikey:config.key,Authorization:auth},signal:AbortSignal.timeout(5000),redirect:'error'});
   const user=await verified.json().catch(()=>null);
   if(!verified.ok||!uuid.test(user?.id)){send(401,{detail:'Session expired or revoked. Sign in again.'});return;}
   if(!/^application\/json(?:\s*;|$)/i.test(req.headers['content-type']||'')){send(415,{detail:'Use a JSON record request.'});return;}
   let body=req.body;
   if(body===undefined){const chunks=[];let size=0;for await(const chunk of req){size+=chunk.length;if(size>2200*1024){send(413,{detail:'Record request is too large.'});return;}chunks.push(chunk);}body=Buffer.concat(chunks).toString('utf8');}
   if(Buffer.byteLength(typeof body==='string'?body:JSON.stringify(body))>2200*1024){send(413,{detail:'Record request is too large.'});return;}
   if(typeof body==='string')body=JSON.parse(body);
   if(!body||typeof body!=='object'||Array.isArray(body))throw Error('INVALID_RECORD');
   let name,args={};
   switch(body.action){
    case 'list':name='sonar_record_list';break;
    case 'create':{
     const result=analyzeSchema.safeParse(body.analysis);
     if(!result.success||!['LIVE_ANALYSIS','PRECOMPUTED_EXAMPLE'].includes(body.source)||!/^[a-f0-9]{64}$/.test(body.image_sha256)||!Number.isInteger(body.image_bytes)||body.image_bytes<1||body.image_bytes>32*1024*1024||!['image/jpeg','image/png'].includes(body.image_mime)||(body.team_id&&!uuid.test(body.team_id)))throw Error('INVALID_RECORD');
     name='sonar_record_create';args={p_analysis:body.analysis,p_source:body.source,p_image_sha256:body.image_sha256,p_image_bytes:body.image_bytes,p_image_mime:body.image_mime,p_team_id:body.team_id||null};break;
    }
    case 'get':case 'delete_begin':case 'delete_finish':if(!uuid.test(body.id))throw Error('INVALID_RECORD');name=`sonar_record_${body.action}`;if(body.action.startsWith('delete'))name=`sonar_${body.action}`;args={p_id:body.id};break;
    case 'review':if(!uuid.test(body.id)||typeof body.candidate_id!=='string'||body.candidate_id.length>200||!Number.isInteger(body.previous_revision)||body.previous_revision<0||!['CONFIRMED','FALSE_POSITIVE','NEEDS_INVESTIGATION'].includes(body.status)||typeof body.note!=='string'||body.note.length>20000)throw Error('INVALID_RECORD');name='sonar_review_save';args={p_id:body.id,p_candidate_id:body.candidate_id,p_previous_revision:body.previous_revision,p_status:body.status,p_note:body.note};break;
    default:throw Error('INVALID_RECORD');
   }
   const value=await rpc(env,name,args,token,fetcher);
   const serialized=JSON.stringify(value);
   if([env.SUPABASE_SECRET_KEY,env.SUPABASE_SERVICE_ROLE_KEY,env.HF_TOKEN,token].filter(Boolean).some(secret=>serialized.includes(secret)))throw Error('UNSAFE_RESPONSE');
   send(200,value);
  } catch(error){
   const code=error.dbCode;const status=code==='42501'?403:code==='23505'?409:code==='P0002'?404:code==='P0001'?429:code==='22023'?422:error.message==='INVALID_RECORD'||error instanceof SyntaxError?422:503;
   const message=code==='42501'?'Reviewer/team access denied. Ask the owner to provision your account.':code==='23505'?'Record or review conflict. Reload before saving; AI records and images are immutable.':code==='P0002'?'Record unavailable.':code==='P0001'?'Shared storage or review capacity reached. Delete older records.':status===422?'Invalid analysis, image metadata or review request.':'Shared records are unavailable or not configured. Browser records remain available.';
   send(status,{detail:message});
  }
 };
}
