import { useEffect, useRef, useState } from 'react';
import { analyzeSchema } from '../api/schema';
import type { AnalyzeResponse } from '../types';
import type { ResultSource } from '../reports/export';
import type { HumanReview } from '../review/reviewStore';

type Entry={analysis_id:string;source:ResultSource;created_at:string;has_image:boolean};
type Revision={candidate_id:string;revision:number;reviewer:string;status:HumanReview['status'];note:string;created_at:string};
export default function SharedRecords({analysis,imageSrc,source,reviews,onOpen}: {analysis:AnalyzeResponse|null;imageSrc:string|null;source:ResultSource;reviews:Record<string,HumanReview>;onOpen:(analysis:AnalyzeResponse,image:Blob,source:ResultSource,reviews:HumanReview[])=>void}) {
  const [base,setBase]=useState(''); const [credential,setCredential]=useState('');
  const [entries,setEntries]=useState<Entry[]>([]); const [message,setMessage]=useState(''); const [busy,setBusy]=useState(false);
  const [history,setHistory]=useState<Revision[]>([]); const generation=useRef(0);
  const controller=useRef<AbortController|null>(null);
  useEffect(() => () => { generation.current++; controller.current?.abort(); }, []);
  const request=async(path:string,options:RequestInit={})=>{
    const url=new URL(base);
    if (url.username||url.password||url.search||url.hash||(url.protocol!=='https:'&&!(url.protocol==='http:'&&['localhost','127.0.0.1'].includes(url.hostname)))) throw Error('Use an HTTPS service URL, or localhost for development.');
    if (credential.length<32) throw Error('Enter your privately issued reviewer credential.');
    const response=await fetch(`${url.href.replace(/\/$/,'')}/records${path}`,{...options,signal:controller.current ? AbortSignal.any([controller.current.signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000),redirect:'error',headers:{...options.headers,Authorization:`Bearer ${credential}`}});
    if(!response.ok) { const value=await response.json().catch(()=>({})); throw Error(typeof value.detail==='string'?value.detail:`Record service returned ${response.status}.`); }
    return response;
  };
  const perform=(action:(version:number)=>Promise<void>)=>{
    const version=++generation.current;controller.current?.abort();controller.current=new AbortController();setBusy(true);setMessage('');
    void action(version).catch(error=>{if(version===generation.current)setMessage(error instanceof Error?error.message:'Shared operation failed.');}).finally(()=>{if(version===generation.current){setBusy(false);controller.current=null;}});
  };
  const listing=async()=>{const response=await request('');const value=await response.json();if(!Array.isArray(value.records))throw Error('Invalid record list.');setEntries(value.records);};
  return <section className="panel shared-records"><details><summary>Shared records and review history</summary>
    <p>Optional persistent service. Your reviewer credential stays in memory and is cleared when you disconnect. Uploaded records are client-imported, not server-certified AI evidence. Live inference still uses Hugging Face.</p>
    <label>Record service URL<input type="url" value={base} onChange={event=>{generation.current++;controller.current?.abort();setBusy(false);setEntries([]);setHistory([]);setBase(event.target.value);}} placeholder="https://records.example.org" /></label>
    <label>Reviewer credential<input type="password" autoComplete="off" value={credential} onChange={event=>{generation.current++;controller.current?.abort();setBusy(false);setEntries([]);setHistory([]);setCredential(event.target.value);}} /></label>
    <button type="button" className="secondary" disabled={busy} onClick={()=>perform(async()=>{await listing();setMessage('Connected. Records are visible only to your account or configured team.');})}>Connect and list records</button>
    <button type="button" className="secondary" onClick={()=>{generation.current++;controller.current?.abort();setCredential('');setEntries([]);setHistory([]);setMessage('Disconnected. Credential cleared.');setBusy(false);}}>Disconnect</button>
    <button type="button" className="secondary" disabled={busy||!analysis||!imageSrc} onClick={()=>perform(async(version)=>{
      if(!analysis||!imageSrc)return; const captured=analysis;
      try {await request('',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({analysis:captured,source})});}
      catch(error){const response=await request(`/${encodeURIComponent(captured.analysis_id)}`);const existing=await response.json();if(JSON.stringify(existing.analysis)!==JSON.stringify(captured)||existing.source!==source)throw error;}
      const image=await fetch(imageSrc).then(response=>response.blob());
      await request(`/${encodeURIComponent(captured.analysis_id)}/image`,{method:'POST',headers:{'Content-Type':image.type},body:image});
      if(version===generation.current){await listing();setMessage('Analysis and paired image saved. Reviews require explicit sync below.');}
    })}>Save current analysis and image</button>
    <button type="button" className="secondary" disabled={busy||!analysis} onClick={()=>perform(async()=>{
      if(!analysis)return;const key=encodeURIComponent(analysis.analysis_id);const data=await request(`/${key}`).then(response=>response.json());
      const revisions:Revision[]=data.review_history;let saved=0;
      for(const review of Object.values(reviews)) {
        if(review.analysisId!==analysis.analysis_id)continue;
        const previous=revisions.filter(entry=>entry.candidate_id===review.candidateId).sort((a,b)=>b.revision-a.revision)[0];
        if(previous&&previous.status===review.status&&previous.note===review.note)continue;
        if(previous && !window.confirm('A different shared review already exists. Save your local assessment as a new revision?')) continue;
        await request(`/${key}/reviews`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({candidate_id:review.candidateId,previous_revision:previous?.revision??0,status:review.status,note:review.note})});saved++;
      }
      const latest=await request(`/${key}`).then(response=>response.json());setHistory(latest.review_history);setMessage(`${saved} review revisions saved. Conflicting edits require reload; AI output is unchanged.`);
    })}>Sync current reviews</button>
    <p role="status">{busy?'Working…':message}</p>
    <ul>{entries.map(entry=><li key={entry.analysis_id}><span>{entry.analysis_id} · {entry.source==='PRECOMPUTED_EXAMPLE'?'PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE':'LIVE ANALYSIS'} · {entry.has_image?'paired image stored':'image missing'}</span>
      <button type="button" disabled={busy||!entry.has_image} onClick={()=>perform(async(version)=>{const key=encodeURIComponent(entry.analysis_id);const data=await request(`/${key}`).then(response=>response.json());const result=analyzeSchema.parse(data.analysis) as AnalyzeResponse;if(!['LIVE_ANALYSIS','PRECOMPUTED_EXAMPLE'].includes(data.source))throw Error('Invalid result source.');const image=await request(`/${key}/image`).then(response=>response.blob());const latest=new Map<string,Revision>();for(const revision of data.review_history as Revision[])if(!latest.has(revision.candidate_id)||(latest.get(revision.candidate_id)?.revision??0)<revision.revision)latest.set(revision.candidate_id,revision);if(version!==generation.current)return;setHistory(data.review_history);onOpen(result,image,data.source,[...latest.values()].map(revision=>({analysisId:result.analysis_id,candidateId:revision.candidate_id,status:revision.status,note:revision.note,reviewedAt:revision.created_at})));setMessage('Stored record opened. No inference ran.');})}>Open stored record</button>
      <button type="button" disabled={busy} onClick={()=>{if(!window.confirm('Delete this shared analysis, image and all review history?'))return;perform(async()=>{await request(`/${encodeURIComponent(entry.analysis_id)}`,{method:'DELETE'});await listing();setMessage('Shared record and history deleted.');});}}>Delete shared record</button></li>)}</ul>
    {history.length>0&&<details><summary>Immutable review revision history</summary><ul>{history.map(revision=><li key={`${revision.candidate_id}-${revision.revision}`}>{revision.candidate_id} · revision {revision.revision} · {revision.reviewer} · {revision.status} · {revision.created_at}<p>{revision.note}</p></li>)}</ul></details>}
  </details></section>;
}
