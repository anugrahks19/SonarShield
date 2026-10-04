# SONAR-SHIELD architecture

Updated 4 October 2026. [Overview](../README.md) · [Setup](SUPABASE_VERCEL_SETUP.md) · [Release scope](MODULE2_M211_RELEASE.md)

## Service boundaries

```mermaid
flowchart TB
 subgraph Browser
  UI[React / Vite viewer]
  IDB[(IndexedDB complete local session)]
  REV[Human review separate from AI]
  OUT[JSON / CSV / complete record / print]
  UI --> IDB
  UI --> REV --> OUT
 end
 subgraph Vercel
  GW[api/analyze: reference validation / deadline / errors]
  REC[api/records: authenticated user JWT]
  MA[api/maintenance: cron credential]
  STATIC[Verified image and response pairs]
 end
 subgraph Supabase
  AUTH[Provisioned reviewer Auth]
  DB[(RLS Postgres: records / immutable reviews / leases)]
  ST[(Private image Storage)]
 end
 HF[Gradio upload and analyze_image_gradio / ZeroGPU]
 UI -->|Image bytes| HF
 UI -->|Small file reference| GW
 GW -->|Admission RPC| DB
 GW -->|Server-only HF_TOKEN| HF
 HF -->|F8.1 contract| GW --> UI
 UI -->|Explicit sample confirmation and hash validation| STATIC
 UI --> AUTH
 UI --> REC --> DB
 UI --> ST
 MA -->|Delete expired image first| ST
 MA -->|Then delete record| DB
```

## Live request

```mermaid
sequenceDiagram
 actor Judge
 participant UI as Browser
 participant HF as HF Space
 participant GW as Vercel gateway
 participant DB as Supabase admission
 Judge->>UI: Upload JPG/PNG and run
 UI->>HF: Upload image bytes directly
 HF-->>UI: Space file reference
 UI->>GW: Same-origin small reference request
 GW->>GW: Validate configured Space upload location
 GW->>DB: Reserve shared budget and lease
 DB-->>GW: Admission or explicit rejection
 GW->>HF: Authenticated named analysis endpoint
 HF-->>GW: Result / status / error
 GW-->>UI: Contract or bounded redacted failure
 UI->>UI: Schema validation and stale-result guard
 UI-->>Judge: LIVE result or retained image plus failure
```

The Vercel function limit is 300 seconds with an earlier controlled timeout. No automatic inference retry or anonymous fallback occurs. Cancellation stops browser waiting and attempts upstream cancellation; consumed quota may remain consumed. Reachability and inference availability are separate. Origin checks reduce accidental cross-site use but do not authenticate public visitors. Shared database admission does not make HF quota unlimited.

## Runtime and artifact identity

Production uses the V6-based shared runtime: canonical classes, global plus optional tiled proposals, merging, image evidence, fusion features, REVIEW decisions and an F8.1-shaped response with actual input/artifact identity where available. Unsupported calibrated probabilities remain unavailable. Older policy/fusion identity does not establish compatibility with the M2.08 experimental weights.

The experimental detector bundle pins FP32/640/batch1, NMS0.7, max300, confidence floor0.001 and post-NMS threshold >=0.3653043210506439. It excludes fusion/calibration and is not enabled in production. [Frozen manifest](metrics/module2-m211-frozen-manifest-20261004.json).

## Examples, persistence and exports

```mermaid
flowchart LR
 E[Explicit example choice] --> H[Image SHA-256 equals saved response]
 H --> A[Validated analysis / visible source label]
 A --> V[Viewer and evidence]
 V --> R[Human review]
 A --> I[(IndexedDB session)]
 R --> I
 I --> P[Portable paired complete record]
 R -->|User JWT / optimistic revision| C[Cloud review history]
 C --> O[Cloud reopen / validate paired image]
 O --> V
 R --> REP[Browser report / CSV / JSON / print]
```

Examples make no inference calls and never analyze an earlier uploaded image. Source labels persist in reports and downloads. IndexedDB restores the complete local session; storage permissions/capacity may prevent it, so portable exports remain important. Reviews retain their analysis/candidate identity and do not overwrite machine decisions. Optional cloud records use provisioned Supabase users, RLS, private paired images and immutable review revisions. Cloud content is client imported, not an independent scientific attestation. Reviewer sign-in is needed again after refresh.

## Raw and edge paths

```mermaid
flowchart LR
 X[Local XTF file] --> P[Bounded packet/sample parser]
 P --> W[Deterministic sonar window rendering / quality flags]
 W --> M[Local CPU runtime]
 NAV[Reviewed source-bound navigation profile] --> G[Geometry / pose validation]
 G --> M
 M --> R[Local viewer / separate reviews / reports]
 G -->|Supported valid geometry only| POS[Estimated WGS84 positions and dimensions]
 R --> POS
 D[Future device image] --> API[Authenticated local edge API] --> M
```

Raw processing is local and bounded, not available as public Vercel XTF inference. The low-amplitude UINT16 rendering defect was corrected. Supported flat-bottom slant/pose/lever-arm handling is conditional; full terrain and motion correction and field accuracy remain incomplete. Missing units, datum, pose or geometry stay unavailable. The edge API is a future integration contract, not AUV hardware certification.

## Verification and recovery

M2.11 records actual test/build and browser scope in [release evidence](MODULE2_M211_RELEASE.md). Mock responses prove UI contract behavior, not real model quality. Restore a previous verified Vercel deployment for web rollback while preserving Supabase data. HF rollback needs a verified runtime/weights revision, not the experimental D1 backup. Portable records are analyst backups; retention is not backup. [Judge and rollback instructions](JUDGE_WALKTHROUGH.md).
