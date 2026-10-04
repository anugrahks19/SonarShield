# Judge walkthrough and recovery

Prepared 4 October 2026 for PS 26057. Public entry point: https://sonarshield26.vercel.app/analysis.

## Before presenting

- Open the public site and confirm verified examples load. Retain the local submission ZIP and deck on this computer.
- If using live inference, make one deliberate representative run when quota permits. M2.11 did not consume quota or establish fresh authenticated live success. Check the original error details rather than claiming GPU availability from reachability.
- Confirm the provisioned reviewer can sign in if demonstrating cloud history. Keep credentials out of projected screens. Cloud login is optional for live/examples.
- Export important complete records. Do not rely on retention, a free service or this browser as your only backup.

## Five-minute demonstration

| Time | Action | Explanation |
|---|---|---|
| 0:00 | Show Analysis | This is a sonar candidate-review prototype for PS26057. |
| 0:30 | Upload representative JPG/PNG and select Run analysis | Live processes this image now, subject to the shared account quota. |
| If live fails | Read failure, choose View verified example, confirm Contact105 | The sample was analyzed earlier. No new inference runs and it is not the uploaded image. |
| 1:30 | Select candidate and inspect evidence | Scores are model/evidence scores. Unsupported calibrated correctness stays unavailable. |
| 2:30 | Save a human review note | The reviewer assessment remains separate from AI decisions. |
| 3:00 | Open Reports, download JSON/CSV and show source label | Geographic fields appear only with supported metadata. Pixel-only examples have no invented location. |
| 4:00 | Export complete record, refresh and restore | The paired image, response and review are portable. |
| Optional | Sign in, save/sync, refresh, sign in and reopen cloud record | Private images and review revisions are persistent but client imported. |

The precomputed flow uses Contact103/104/105 and a background example. Keep **PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE** visible. A historical sample can contain older machine decisions and must not be presented as the new experimental detector output.

## If everything is offline

The ZIP includes a static built frontend. Serve the `frontend-static` directory over HTTP using `python -m http.server 8783 --bind 127.0.0.1`; open `http://127.0.0.1:8783/` and use verified examples. Avoid direct `file://` opening. Static hosting has no gateway/cloud APIs, so live and cloud controls are unavailable. The interactive example, local review and report are the backup. An external basemap may be unavailable offline; pixel evidence remains usable. Private/incognito or disabled IndexedDB can prevent local persistence.

## Results to say aloud

The experimental M2.08 detector achieved 80.10% precision and 41.43% recall at one selected DEV threshold, with 236 false positives. Its mAP50 was 69.90%, mAP50-95 49.73%, warm GPU forward 7.53ms. DEV was reused for selection; this is not independent field accuracy. The weights are frozen locally and not deployed. Our 80/80 and 90/90 goals are not achieved.

## Raw XTF and edge scope

Show the local raw dashboard only as a supported bounded prototype. Navigation/dimensions are estimates only with reviewed source geometry. Confirmed target annotation and external evaluation are missing, so public XTF remains disabled. The future edge endpoint accepts authenticated images; no actual AUV hardware test is claimed. Do not start training during the judging session.

## Rollback

1. Redeploy the last verified Vercel deployment from its deployment history. Preserve Supabase data/schema and server secrets. Do not remove shared admission controls to bypass a failed check.
2. For an HF runtime rollback, use a previously verified full source-and-artifact revision. Do not substitute new weights under old fusion/policy/calibration. The local `rollback-d1.pt` is an experimental baseline, not a deployed-runtime backup.
3. Restore paired browser records through Import complete record, or reopen an authorized cloud record. Review histories stay separate from original analysis.
4. Verify the fallback/viewer/review/report labels after recovery. Real live inference remains a deliberate separate check.

## Public demo reviewer

[Activate the dedicated judge sandbox](JUDGE_CLOUD_DEMO.md) to test a precomputed cloud record and public review history without your private login. Supabase activation is required; the UI checks readiness before enabling the button.
