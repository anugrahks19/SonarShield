-- Run AFTER creating the email-confirmed demo Auth user and applying the judge migration.
-- This finds only the new public demo email; it never reads/changes private passwords.
do $$
declare actor uuid;
begin
 select id into actor from auth.users where lower(email)='judge.demo@sonarshield.example' and email_confirmed_at is not null;
 if actor is null then raise exception 'Create the email-confirmed judge.demo@sonarshield.example Auth user first.';end if;
 if exists(select 1 from public.sonar_records where owner=actor)
    or exists(select 1 from public.sonar_team_members where user_id=actor) then
  raise exception 'Use a fresh demo account with no existing records or private teams.';
 end if;
 insert into public.sonar_members(user_id) values(actor) on conflict do nothing;
 update public.sonar_judge_demo set user_id=actor,enabled=true where id=true;
 if not found then raise exception 'Run the judge demo migration first.';end if;
end $$;
select public.sonar_judge_demo_ready() as judge_demo_enabled;
