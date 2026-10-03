-- Run as the project administrator in Supabase SQL Editor.
-- All test writes roll back. This makes zero HF inference calls.
-- Run when no judge is using live inference; refuse an active lease.
do $$
declare a jsonb; b jsonb; lease uuid; rejected boolean:=false; checks jsonb:='[]'::jsonb; today date:=(now() at time zone 'UTC')::date;
begin
 perform set_config('lock_timeout','2s',true);
 begin -- Exception-safe subtransaction: every test write is rolled back.
 perform 1 from public.sonar_settings where id=true for update;
 if exists(select 1 from public.sonar_leases where expires_at>now()) then
   raise exception 'A live safety lease is active. Wait for it to finish/expire; do not bypass it.';
 end if;
 if not has_function_privilege('service_role','public.sonar_admission_acquire()','EXECUTE')
   or has_function_privilege('anon','public.sonar_admission_acquire()','EXECUTE')
   or has_function_privilege('authenticated','public.sonar_admission_acquire()','EXECUTE') then
   raise exception 'Admission privilege boundary is incorrect.';
 end if;
 checks:=checks||jsonb_build_array(jsonb_build_object('check_name','service_only_admission','passed',true,'details','anon/authenticated cannot reserve account quota'));
 update public.sonar_settings set daily_limit=2,concurrent_limit=1 where id=true;
 delete from public.sonar_usage where day=today;
 a:=public.sonar_admission_acquire();
 lease:=(a->>'lease_id')::uuid;
 begin perform public.sonar_admission_acquire(); exception when sqlstate 'P0001' then rejected:=true;end;
 if not rejected then raise exception 'Concurrent admission was not rejected.';end if;
 checks:=checks||jsonb_build_array(jsonb_build_object('check_name','concurrent_limit','passed',true,'details','second simultaneous admission rejected'));
 update public.sonar_leases set expires_at=now()-interval '1 second' where id=lease;
 b:=public.sonar_admission_acquire();
 if b->>'lease_id'=a->>'lease_id' then raise exception 'Expired lease was reused.';end if;
 checks:=checks||jsonb_build_array(jsonb_build_object('check_name','lease_expiry','passed',true,'details','expired lease cleared; new admission accepted'));
 perform public.sonar_admission_release((b->>'lease_id')::uuid);
 rejected:=false;
 begin perform public.sonar_admission_acquire(); exception when sqlstate 'P0001' then rejected:=true;end;
 if not rejected then raise exception 'Daily budget was not enforced.';end if;
 checks:=checks||jsonb_build_array(jsonb_build_object('check_name','daily_budget','passed',true,'details','budget remains consumed after lease release'));
 if not has_function_privilege('service_role','public.sonar_expired_records()','EXECUTE')
   or has_function_privilege('authenticated','public.sonar_expired_records()','EXECUTE')
   or has_function_privilege('anon','public.sonar_expired_records()','EXECUTE') then
   raise exception 'Retention privilege boundary is incorrect.';
 end if;
 perform public.sonar_expired_records();
 checks:=checks||jsonb_build_array(jsonb_build_object('check_name','retention_rpc_permissions','passed',true,'details','expiry listing callable only by service/admin'));
 raise exception using errcode='ZX001',message='ROLLBACK_QA_WRITES';
 exception when sqlstate 'ZX001' then null;
 end;
 perform set_config('sonar.module1_probe_result',checks::text,false);
end $$;
select * from jsonb_to_recordset(current_setting('sonar.module1_probe_result')::jsonb)
 as checks(check_name text,passed boolean,details text) order by check_name;

-- This verifies hosted database behavior when YOU run it there. It does not
-- certify Vercel secret values, cron delivery, Storage deletion or signed-in UI.
