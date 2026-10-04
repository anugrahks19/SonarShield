// Intentionally public credentials for a dedicated sample-only reviewer.
// Never substitute a private account, HF token or Supabase service key here.
export const judgeDemo={email:'judge.demo@sonarshield.example',password:'SonarShield-Demo-2026!',imageHash:'6407b4344f90aa1ade206d83c2e9072e6a007c200f3a721212258908225e29e3'};
export async function seedJudgeDemo({api,upload,fetcher=fetch}) {
 const response=await fetcher('/contact-105.json');if(!response.ok)throw Error('Demo response unavailable.');
 const analysis=await response.json();const picture=await fetcher('/contact-105.jpg');if(!picture.ok)throw Error('Demo image unavailable.');
 const image=await picture.blob();const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await image.arrayBuffer())),v=>v.toString(16).padStart(2,'0')).join('');
 if(digest!==judgeDemo.imageHash||analysis.input.sha256!==digest||image.size!==66818)throw Error('Demo sample pairing failed.');
 const record=await api({action:'create',analysis,source:'PRECOMPUTED_EXAMPLE',image_sha256:digest,image_bytes:image.size,image_mime:'image/jpeg',team_id:null});
 await upload(record.image_path,image,digest);
 let current=await api({action:'get',id:record.id});
 // Idempotent: do not overwrite a judge's existing revisions.
 if(current.review_history.length===0){
  const candidate=analysis.candidates[0].candidate_id;
  await api({action:'review',id:record.id,candidate_id:candidate,previous_revision:0,status:'NEEDS_INVESTIGATION',note:'DEMO SEED: Example review for judging. This is a precomputed Contact 105 result, not new inference or a confirmed field target.'});
  await api({action:'review',id:record.id,candidate_id:candidate,previous_revision:1,status:'NEEDS_INVESTIGATION',note:'DEMO SEED: Second revision demonstrates preserved review history. Add your own demo note and sync it to test restoration. Do not enter private information.'});
  current=await api({action:'get',id:record.id});
 }
 return current;
}
