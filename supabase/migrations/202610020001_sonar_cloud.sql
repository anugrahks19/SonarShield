-- SONAR-SHIELD: invite-only records, private images and server-only admission.
-- Apply once in the selected Supabase project's SQL editor. No model changes.
begin;
create table public.sonar_members(user_id uuid primary key references auth.users(id) on delete cascade);
create table public.sonar_team_members(team_id uuid not null,user_id uuid not null references auth.users(id) on delete cascade,primary key(team_id,user_id));
create table public.sonar_settings(id boolean primary key default true check(id),daily_limit integer not null default 20 check(daily_limit between 1 and 10000),concurrent_limit integer not null default 1 check(concurrent_limit between 1 and 16),lease_seconds integer not null default 600 check(lease_seconds between 360 and 3600),max_records integer not null default 8 check(max_records between 1 and 8));
insert into public.sonar_settings(id) values(true);
create table public.sonar_records(id uuid primary key default gen_random_uuid(),owner uuid not null references auth.users(id),team_id uuid,analysis_id text not null check(length(analysis_id) between 1 and 200),analysis jsonb not null check(octet_length(analysis::text)<=2097152),source text not null check(source in ('LIVE_ANALYSIS','PRECOMPUTED_EXAMPLE')),image_sha256 text not null check(image_sha256~'^[a-f0-9]{64}$'),image_bytes integer not null check(image_bytes between 1 and 33554432),image_mime text not null check(image_mime in ('image/jpeg','image/png')),created_at timestamptz not null default now(),expires_at timestamptz not null default now()+interval '30 days',deleting boolean not null default false,unique(owner,analysis_id));
create table public.sonar_reviews(record_id uuid not null references public.sonar_records(id) on delete cascade,candidate_id text not null check(length(candidate_id) between 1 and 200),revision integer not null check(revision between 1 and 200),reviewer uuid not null references auth.users(id),status text not null check(status in ('CONFIRMED','FALSE_POSITIVE','NEEDS_INVESTIGATION')),note text not null check(length(note)<=20000),created_at timestamptz not null default now(),primary key(record_id,candidate_id,revision));
create table public.sonar_usage(day date primary key,runs integer not null check(runs>=0));
create table public.sonar_leases(id uuid primary key default gen_random_uuid(),expires_at timestamptz not null);
alter table public.sonar_members enable row level security;
alter table public.sonar_team_members enable row level security;
alter table public.sonar_records enable row level security;
alter table public.sonar_reviews enable row level security;
alter table public.sonar_settings enable row level security;
alter table public.sonar_usage enable row level security;
alter table public.sonar_leases enable row level security;
-- All application access goes through narrowly granted RPCs. No direct table writes.
revoke all on public.sonar_members,public.sonar_team_members,public.sonar_records,public.sonar_reviews,public.sonar_settings,public.sonar_usage,public.sonar_leases from anon,authenticated;

create function public.sonar_member() returns uuid language plpgsql security definer set search_path='' as $$
declare actor uuid:=auth.uid();
begin
 if actor is null or not exists(select 1 from public.sonar_members where user_id=actor) then raise exception 'Reviewer access has not been provisioned.' using errcode='42501';end if;
 return actor;
end $$;
create function public.sonar_access(p_id uuid) returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.sonar_records r where r.id=p_id and exists(select 1 from public.sonar_members m where m.user_id=auth.uid()) and (r.owner=auth.uid() or exists(select 1 from public.sonar_team_members t where t.team_id=r.team_id and t.user_id=auth.uid())));
$$;
create function public.sonar_image_path(p_id uuid) returns text language sql stable security definer set search_path='' as $$
 select owner::text||'/'||id::text||'/image.'||case when image_mime='image/png' then 'png' else 'jpg' end from public.sonar_records where id=p_id and public.sonar_access(p_id);
$$;
create function public.sonar_record_list() returns jsonb language plpgsql security definer set search_path='' as $$
begin
 perform public.sonar_member();
 return jsonb_build_object('records',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'analysis_id',r.analysis_id,'source',r.source,'created_at',r.created_at,'expires_at',r.expires_at,'deleting',r.deleting,'has_image',exists(select 1 from storage.objects o where o.bucket_id='sonar-records' and o.name=public.sonar_image_path(r.id))) order by r.created_at desc) from public.sonar_records r where public.sonar_access(r.id)),'[]'::jsonb));
end $$;
create function public.sonar_record_get(p_id uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.sonar_records;
begin
 perform public.sonar_member();select * into r from public.sonar_records where id=p_id and public.sonar_access(id);
 if not found then raise exception 'Record not found.' using errcode='P0002';end if;
 return jsonb_build_object('id',r.id,'analysis',r.analysis,'source',r.source,'image_path',public.sonar_image_path(r.id),'image_sha256',r.image_sha256,'image_bytes',r.image_bytes,'image_mime',r.image_mime,'expires_at',r.expires_at,'deleting',r.deleting,'origin','CLIENT_IMPORTED_UNATTESTED','review_history',coalesce((select jsonb_agg(to_jsonb(v) order by v.revision) from public.sonar_reviews v where record_id=r.id),'[]'::jsonb));
end $$;
create function public.sonar_record_create(p_analysis jsonb,p_source text,p_image_sha256 text,p_image_bytes integer,p_image_mime text,p_team_id uuid default null) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=public.sonar_member();r public.sonar_records;settings public.sonar_settings;
begin
 select * into settings from public.sonar_settings where id=true for update;
 if p_team_id is not null and not exists(select 1 from public.sonar_team_members where team_id=p_team_id and user_id=actor) then raise exception 'Team access denied.' using errcode='42501';end if;
 select * into r from public.sonar_records where owner=actor and analysis_id=p_analysis->>'analysis_id';
 if found then
  if r.analysis<>p_analysis or r.source<>p_source or r.image_sha256<>p_image_sha256 or r.image_bytes<>p_image_bytes or r.image_mime<>p_image_mime or r.team_id is distinct from p_team_id or r.deleting or r.expires_at<=now() then raise exception 'Record identity is immutable or expired.' using errcode='23505';end if;
  return public.sonar_record_get(r.id);
 end if;
 if (select count(*) from public.sonar_records)>=settings.max_records then raise exception 'Shared record capacity reached; delete older records.' using errcode='P0001';end if;
 if (p_source='PRECOMPUTED_EXAMPLE' or p_analysis->>'schema_version'='F8.1') and p_analysis->'input'->>'sha256' is distinct from p_image_sha256 then raise exception 'Image pairing disagrees.' using errcode='22023';end if;
 insert into public.sonar_records(owner,team_id,analysis_id,analysis,source,image_sha256,image_bytes,image_mime) values(actor,p_team_id,p_analysis->>'analysis_id',p_analysis,p_source,p_image_sha256,p_image_bytes,p_image_mime) returning * into r;
 return public.sonar_record_get(r.id);
end $$;
create function public.sonar_review_save(p_id uuid,p_candidate_id text,p_previous_revision integer,p_status text,p_note text) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=public.sonar_member();r public.sonar_records;current_revision integer;
begin
 select * into r from public.sonar_records where id=p_id and public.sonar_access(id) for update;
 if not found or r.deleting or r.expires_at<=now() then raise exception 'Record unavailable.' using errcode='P0002';end if;
 if not exists(select 1 from jsonb_array_elements(r.analysis->'candidates') c where c->>'candidate_id'=p_candidate_id) then raise exception 'Candidate does not belong to record.' using errcode='22023';end if;
 select coalesce(max(revision),0) into current_revision from public.sonar_reviews where record_id=p_id and candidate_id=p_candidate_id;
 if current_revision<>p_previous_revision then raise exception 'Review changed; reload before saving.' using errcode='23505';end if;
 if (select count(*) from public.sonar_reviews where record_id=p_id)>=200 then raise exception 'Review history capacity reached.' using errcode='P0001';end if;
 insert into public.sonar_reviews values(p_id,p_candidate_id,current_revision+1,actor,p_status,p_note,now());
 return jsonb_build_object('revision',current_revision+1,'reviewer',actor);
end $$;
create function public.sonar_delete_begin(p_id uuid) returns jsonb language plpgsql security definer set search_path='' as $$
begin
 perform public.sonar_member();update public.sonar_records set deleting=true where id=p_id and owner=auth.uid();
 if not found then raise exception 'Only the record owner can delete it.' using errcode='42501';end if;
 return jsonb_build_object('id',p_id,'image_path',public.sonar_image_path(p_id));
end $$;
create function public.sonar_delete_finish(p_id uuid) returns jsonb language plpgsql security definer set search_path='' as $$
begin
 perform public.sonar_member();
 if exists(select 1 from storage.objects where bucket_id='sonar-records' and name=public.sonar_image_path(p_id)) then raise exception 'Delete the paired storage object first.' using errcode='23505';end if;
 delete from public.sonar_records where id=p_id and owner=auth.uid() and deleting;
 if not found then raise exception 'Deletion was not prepared.' using errcode='42501';end if;
 return jsonb_build_object('deleted',true);
end $$;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types) values('sonar-records','sonar-records',false,33554432,array['image/jpeg','image/png']);
create function public.sonar_storage_allowed(p_name text,p_operation text) returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.sonar_records r where p_name=public.sonar_image_path(r.id) and public.sonar_access(r.id) and case p_operation when 'read' then r.expires_at>now() or (r.owner=auth.uid() and r.deleting) when 'insert' then r.owner=auth.uid() and not r.deleting and r.expires_at>now() when 'delete' then r.owner=auth.uid() and r.deleting else false end);
$$;
revoke all on function public.sonar_storage_allowed(text,text) from public,anon,authenticated;
grant execute on function public.sonar_storage_allowed(text,text) to authenticated;
create policy sonar_image_select on storage.objects for select to authenticated using(bucket_id='sonar-records' and public.sonar_storage_allowed(name,'read'));
create policy sonar_image_insert on storage.objects for insert to authenticated with check(bucket_id='sonar-records' and public.sonar_storage_allowed(name,'insert'));
create policy sonar_image_delete on storage.objects for delete to authenticated using(bucket_id='sonar-records' and public.sonar_storage_allowed(name,'delete'));
-- No UPDATE policy: images cannot be overwritten/upserted.
create function public.sonar_admission_acquire() returns jsonb language plpgsql security definer set search_path='' as $$
declare settings public.sonar_settings;used integer;lease uuid;today date:=(now() at time zone 'UTC')::date;
begin
 select * into settings from public.sonar_settings where id=true for update;
 delete from public.sonar_leases where expires_at<=now();delete from public.sonar_usage where day<today-7;
 select runs into used from public.sonar_usage where day=today;used:=coalesce(used,0);
 if used>=settings.daily_limit or (select count(*) from public.sonar_leases)>=settings.concurrent_limit then raise exception 'Live admission limit reached.' using errcode='P0001';end if;
 insert into public.sonar_usage values(today,1) on conflict(day) do update set runs=public.sonar_usage.runs+1;
 insert into public.sonar_leases(expires_at) values(now()+make_interval(secs=>settings.lease_seconds)) returning id into lease;
 return jsonb_build_object('lease_id',replace(lease::text,'-',''),'budget_remaining',settings.daily_limit-used-1);
end $$;
create function public.sonar_admission_release(p_lease_id uuid) returns void language sql security definer set search_path='' as $$ delete from public.sonar_leases where id=p_lease_id; $$;
create function public.sonar_expired_records() returns jsonb language sql security definer set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'image_path',owner::text||'/'||id::text||'/image.'||case when image_mime='image/png' then 'png' else 'jpg' end)),'[]'::jsonb) from public.sonar_records where expires_at<=now();
$$;
create function public.sonar_prune_record(p_id uuid) returns void language plpgsql security definer set search_path='' as $$
begin
 if exists(select 1 from storage.objects o join public.sonar_records r on r.id=p_id where o.bucket_id='sonar-records' and o.name=r.owner::text||'/'||r.id::text||'/image.'||case when r.image_mime='image/png' then 'png' else 'jpg' end) then raise exception 'Storage object still exists.';end if;
 delete from public.sonar_records where id=p_id and expires_at<=now();
end $$;
-- PostgreSQL grants PUBLIC execute on new functions by default; explicitly revoke it.
revoke all on function public.sonar_member(),public.sonar_access(uuid),public.sonar_image_path(uuid),public.sonar_record_list(),public.sonar_record_get(uuid),public.sonar_record_create(jsonb,text,text,integer,text,uuid),public.sonar_review_save(uuid,text,integer,text,text),public.sonar_delete_begin(uuid),public.sonar_delete_finish(uuid),public.sonar_admission_acquire(),public.sonar_admission_release(uuid),public.sonar_expired_records(),public.sonar_prune_record(uuid) from public,anon,authenticated;
grant execute on function public.sonar_member(),public.sonar_access(uuid),public.sonar_image_path(uuid),public.sonar_record_list(),public.sonar_record_get(uuid),public.sonar_record_create(jsonb,text,text,integer,text,uuid),public.sonar_review_save(uuid,text,integer,text,text),public.sonar_delete_begin(uuid),public.sonar_delete_finish(uuid) to authenticated;
grant execute on function public.sonar_admission_acquire(),public.sonar_admission_release(uuid),public.sonar_expired_records(),public.sonar_prune_record(uuid) to service_role;
commit;
