# Public judge cloud sandbox

## Public demo login

- Email: `judge.demo@sonarshield.example`
- Password: `SonarShield-Demo-2026!`

These are intentionally public credentials for a dedicated sample-only user. They must never be used for private records or reused as another account password. Judges share the same identity and public notes, so individual attribution is unavailable.

## Administrator activation: two steps

1. Supabase → Authentication → Users → Add user / Create user. Enter the email and password above and enable **Auto Confirm User**. Keep email sign-in enabled and public sign-ups disabled. Use a fresh user with no existing records or team memberships.
2. SQL Editor → New query. Copy the entire [setup SQL](../supabase/verification/setup_judge_demo.sql), then Run. It finds the email automatically, installs database guards, provisions membership and enables the demo. The final row must show `judge_demo_enabled = true`. No private key or UID is needed in source or chat.

After Vercel deploys the GitHub change, reload the site and expand Cloud records and review history. Click **Sign in as demo judge**. It saves the paired Contact105 sample and two clearly labeled demo review revisions, without inference. The button stays disabled until database readiness is confirmed. No extra Vercel variables are required. If the eight-record global capacity is full, remove an unused record through your private owner account to leave one slot.

## Judge test

Click **Open cloud record**. Select a candidate, edit a review note, save it locally and **Sync reviews to cloud**, confirming the new revision. Refresh, sign in as demo and reopen. The note and earlier revisions should return. Reports are on the site's Reports page. This uses real Supabase Auth/Storage/Postgres when activated; local browser tests used mocked Supabase and do not prove hosted activation.

## Isolation and limits

Database rules allow only the exact bundled Contact105 response/hash/byte count, JPEG, no team and one record. Arbitrary/live records and private-team membership are rejected even through direct RPC. The demo cannot delete its sample or paired image. Existing RLS prevents access to other owners' records; private reviewers retain their normal controls.

All demo notes are public. Do not enter private information. They are reviews of a precomputed example, not new inference or confirmed field evidence. Demo notes are capped at 2,000 characters and the existing 200-revision cap applies. Ordinary 30-day expiry applies. An administrator must reset a full or expired demo using the normal Storage-before-record deletion flow. A service account can perform retention; the public user cannot.

After judging, revoke sessions and disable/ban or delete the Auth demo user through Supabase administration. To disable the button run `update public.sonar_judge_demo set enabled=false where id=true;`. To revoke existing read access too, remove its `sonar_members` row and revoke Auth sessions. The readiness flag alone does not revoke existing sessions. Preserve private records, RLS and shared inference admission.

## Verification

Local SQL tests cover readiness, private isolation, altered/live response rejection, idempotent creation, review length/history, deletion/team restrictions, ordinary reviewer behavior and administrator retention. Browser checks cover login/sample/history, review sync, refresh/reopen, source labels and mobile layout with zero inference calls. [Evidence](metrics/judge-cloud-demo-20261004.json).
