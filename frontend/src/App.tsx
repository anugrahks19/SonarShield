import CloudRecords from './records/CloudRecords';
import SharedRecords from './records/SharedRecords';
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, BarChart3, CircleHelp, FileText, LayoutDashboard, Menu, Radio, X } from 'lucide-react';
import { analyzeImage, AnalysisError, getHealth } from './api';
import { demoEnabled } from './config/env';
import { analyzeSchema } from './api/schema';
import type { AnalyzeResponse, HealthResponse } from './types';
import type { HumanReview } from './review/reviewStore';
import { deleteReview, getReviews, saveReview } from './review/reviewStore';
import SonarViewer from './components/sonar/SonarViewer';
import CandidateList from './components/candidates/CandidateList';
import AnalysisPanel from './components/analysis/AnalysisPanel';
import ReviewSummary from './components/review/ReviewSummary';
import { mapPoints } from './components/map/mapData';
import { OverviewPage, SystemPage } from './components/navigation/Pages';
import { ToastRegion } from './components/ui/Feedback';
import VerifiedExamples, { type VerifiedExampleId } from './components/ui/VerifiedExamples';
import QuotaReset from './components/ui/QuotaReset';
import { clearSession, exportRecord, importRecord, restoreSession, saveSession } from './records/sessionStore';
import { downloadText, safeAnalysisName } from './reports/export';
import type { Toast } from './components/ui/Feedback';
import './App.css';
import './Phase2.css';
import './Phase3.css';
import './Phase4.css';
import './Phase5.css';
import './Phase6.css';
import './Phase7.css';
import './JudgeFallback.css';
import './Records.css';

type Phase = 'empty' | 'selected' | 'running' | 'success' | 'error' | 'invalid';
const navigation = [{ name: 'Overview', icon: LayoutDashboard }, { name: 'Analysis', icon: Activity }, { name: 'Candidates', icon: BarChart3 }, { name: 'Reports', icon: FileText }, { name: 'System', icon: Radio }];
const pathPage = (path: string) => path === '/overview' ? 'Overview' : path.startsWith('/reports') ? 'Reports' : path === '/candidates' ? 'Candidates' : path === '/system' ? 'System' : 'Analysis';
const pagePath = (name: string, id?: string) => name === 'Reports' && id ? `/reports/${encodeURIComponent(id)}` : `/${name.toLowerCase()}`;
const SonarMap = lazy(() => import('./components/map/SonarMap'));
const RecordsPanel = window.location.search.includes('legacy-records=1') && import.meta.env.DEV ? SharedRecords : CloudRecords;
const ReportPage = lazy(() => import('./components/reports/ReportPage'));

export default function App() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [metadataJson, setMetadataJson] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [src, setSrc] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);
  const [phase, setPhase] = useState<Phase>('empty');
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [reviews, setReviews] = useState<Record<string, HumanReview>>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<AnalysisError | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthBusy, setHealthBusy] = useState(false);
  const [healthError, setHealthError] = useState<AnalysisError | null>(null);
  const healthAbort = useRef<AbortController | null>(null);
  const analysisAbort = useRef<AbortController | null>(null);
  const requestVersion = useRef(0);
  const [demo, setDemo] = useState(false);
  const [showExamples, setShowExamples] = useState(false);
  const [exampleBusy, setExampleBusy] = useState(false);
  const [quotaLimited, setQuotaLimited] = useState(false);
  const [drag, setDrag] = useState(false);
  const [page, setPage] = useState(() => pathPage(window.location.pathname));
  const [routePath, setRoutePath] = useState(() => window.location.pathname);
  const [menuOpen, setMenuOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const toastId = useRef(0);
  const notify = useCallback((kind: Toast['kind'], message: string) => {
    const id = ++toastId.current;
    setToasts(current => [...current.filter(toast => toast.kind !== kind).slice(-1), { id, kind, message }]);
    window.setTimeout(() => setToasts(current => current.filter(toast => toast.id !== id)), 4500);
  }, []);
  useEffect(() => {
    const sync = () => { setRoutePath(window.location.pathname); setPage(pathPage(window.location.pathname)); };
    window.addEventListener('popstate', sync);
    return () => window.removeEventListener('popstate', sync);
  }, []);
  const navigate = useCallback((name: string, id?: string) => {
    const path = pagePath(name, id);
    if (window.location.pathname !== path) window.history.pushState(null, '', path);
    setRoutePath(path); setPage(name); setMenuOpen(false);
  }, []);

  const checkHealth = useCallback(async () => {
    healthAbort.current?.abort();
    const controller = new AbortController();
    healthAbort.current = controller;
    setHealthBusy(true); setHealthError(null);
    try { const value = await getHealth(controller.signal); if (healthAbort.current === controller) setHealth(value); }
    catch (issue) {
      if (healthAbort.current === controller) {
        setHealth(null);
        setHealthError(issue instanceof AnalysisError ? issue : new AnalysisError('API_OFFLINE', 'The analysis service could not be reached.'));
      }
    } finally { if (healthAbort.current === controller) { healthAbort.current = null; setHealthBusy(false); } }
  }, []);
  useEffect(() => {
    // Defer the first request until after the effect has settled; StrictMode's
    // setup/cleanup replay then cannot dispatch a duplicate health request.
    const frame = window.requestAnimationFrame(() => void checkHealth());
    return () => {
      window.cancelAnimationFrame(frame);
      healthAbort.current?.abort(); analysisAbort.current?.abort();
      // The latest request version must be invalidated on unmount, not a captured snapshot.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      requestVersion.current++;
    };
  }, [checkHealth]);
  useEffect(() => () => { if (src?.startsWith('blob:')) URL.revokeObjectURL(src); }, [src]);

  useEffect(() => {
    let cancelled = false;
    const version = requestVersion.current;
    void restoreSession().then(saved => {
      if (!saved || cancelled || version !== requestVersion.current) return;
      const value = saved.result;
      setMetadataJson(saved.metadataJson ?? ''); setResult(value); setSrc(URL.createObjectURL(saved.image)); setDemo(saved.source === 'PRECOMPUTED_EXAMPLE');
      if (saved.source === 'LIVE_ANALYSIS') setFile(new File([saved.image], value.input.filename, { type: saved.image.type }));
      setDimensions(value.input.width && value.input.height ? { width: value.input.width, height: value.input.height } : null);
      setSelectedId(value.candidates[0]?.candidate_id ?? null);
      setReviews(getReviews(value.analysis_id, value.candidates.map(c => c.candidate_id))); setPhase('success');
      notify('info', 'Previous analysis restored from this browser.');
    }).catch(() => { if (!cancelled) notify('error', 'Saved analysis could not be restored. You can clear the saved record.'); });
    return () => { cancelled = true; };
  }, [notify]);
  const selectFile = (next: File | undefined) => {
    if (!next) return;
    analysisAbort.current?.abort(); analysisAbort.current = null; requestVersion.current++;
    setResult(null); setReviews({}); setSelectedId(null); setError(null); setDemo(false); setMetadataJson(''); setDimensions(null); setShowExamples(false); setExampleBusy(false);
    if (next.size > 32 * 1024 * 1024) { setPhase('invalid'); setFile(null); setSrc(null); setError(new AnalysisError('INVALID_FILE', 'Image exceeds 32 MiB.')); return; }
    if (next.size === 0 || !(['image/jpeg', 'image/png'].includes(next.type) || (!next.type && /\.(jpe?g|png)$/i.test(next.name)))) {
      setPhase('invalid'); setFile(null); setSrc(null);
      setError(new AnalysisError('INVALID_FILE', next.size === 0 ? 'The selected file is empty.' : 'Use a JPG or PNG sonar image.'));
      return;
    }
    const objectUrl = URL.createObjectURL(next);
    const image = new Image();
    const imageVersion = requestVersion.current;
    image.onload = () => {
      if (imageVersion !== requestVersion.current) return;
      if (image.naturalWidth * image.naturalHeight > 16_000_000) { setPhase('invalid'); setFile(null); setSrc(null); setError(new AnalysisError('INVALID_IMAGE', 'Image exceeds 16 million pixels.')); return; }
      setDimensions({ width: image.naturalWidth, height: image.naturalHeight });
    };
    image.onerror = () => { if (imageVersion !== requestVersion.current) return; setPhase('invalid'); setError(new AnalysisError('INVALID_IMAGE', 'The selected file could not be read as an image.')); setSrc(null); setFile(null); };
    image.src = objectUrl;
    setFile(next); setSrc(objectUrl); setPhase('selected');
  };
  const run = async () => {
    if (!file || analysisAbort.current) return;
    const controller = new AbortController();
    analysisAbort.current = controller;
    const version = ++requestVersion.current;
    setPhase('running'); setError(null); setResult(null); setReviews({}); setSelectedId(null); setShowExamples(false); setExampleBusy(false);
    try {
      const value = await analyzeImage(file, controller.signal, metadataJson || undefined);
      if (version !== requestVersion.current) return;
      if (value.status !== 'COMPLETED' || value.processing.status === 'FAILED') throw new AnalysisError('ANALYSIS_FAILED', `The backend returned ${value.status} (${value.processing.status}).`);
      void saveSession(value, file, 'LIVE_ANALYSIS', metadataJson).catch(() => notify('error', 'Analysis completed, but browser storage failed. Export your report to keep it.'));
      setResult(value); setDemo(false); setQuotaLimited(false); setReviews(getReviews(value.analysis_id, value.candidates.map(candidate => candidate.candidate_id))); setSelectedId(value.candidates[0]?.candidate_id ?? null); setPhase('success'); notify('success', `Live analysis complete · ${value.candidates.length} candidate${value.candidates.length === 1 ? '' : 's'}`);
    } catch (issue) {
      if (version !== requestVersion.current) return;
      const failure = issue instanceof AnalysisError ? issue : new AnalysisError('ANALYSIS_FAILED', 'Analysis failed. Please retry.');
      setError(failure);
      if (failure.code === 'GPU_QUOTA_EXCEEDED') setQuotaLimited(true);
      setPhase('error'); notify('error', 'Analysis failed. Check the service response and retry.');
    } finally { if (analysisAbort.current === controller) analysisAbort.current = null; }
  };
  const loadDemo = async (sampleId: VerifiedExampleId) => {
    const version = ++requestVersion.current;
    analysisAbort.current?.abort(); analysisAbort.current = null;
    setExampleBusy(true);
    try {
      const [response, imageResponse] = await Promise.all([fetch(`/${sampleId}.json`), fetch(`/${sampleId}.jpg`)]);
      if (!response.ok || !imageResponse.ok) throw Error();
      const parsed = analyzeSchema.safeParse(await response.json());
      if (!parsed.success) throw new AnalysisError('INVALID_API_RESPONSE', 'The validation fixture does not match the F8 contract.');
      const value = parsed.data as AnalyzeResponse;
      const imageBlob = await imageResponse.blob();
      const imageHash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', await imageBlob.arrayBuffer())), byte => byte.toString(16).padStart(2, '0')).join('');
      if (imageHash !== value.input.sha256.toLowerCase()) throw new Error('Image and saved response do not match.');
      if (version !== requestVersion.current) return;
      const imageUrl = URL.createObjectURL(imageBlob);
      setFile(null); setDemo(true); setResult(null); setReviews({}); setSelectedId(null); setError(null); setShowExamples(false);
      setDimensions(value.input.width && value.input.height ? { width: value.input.width, height: value.input.height } : null);
      void saveSession(value, imageBlob, 'PRECOMPUTED_EXAMPLE').catch(() => notify('error', 'Example loaded, but browser storage failed.'));
      setSrc(imageUrl); setResult(value); setReviews(getReviews(value.analysis_id, value.candidates.map(candidate => candidate.candidate_id))); setSelectedId(value.candidates[0]?.candidate_id ?? null); setPhase('success'); notify('info', `Precomputed example loaded · ${value.candidates.length} candidate${value.candidates.length === 1 ? '' : 's'}`);
    } catch {
      if (version === requestVersion.current) {
        if (!result) { setError(new AnalysisError('EXAMPLE_UNAVAILABLE', 'The verified example could not be loaded. Your uploaded image remains available.')); setPhase('error'); }
        notify('error', 'The verified example could not be loaded. Your current image remains available.');
      }
    } finally { if (version === requestVersion.current) setExampleBusy(false); }
  };
  const openExamples = () => setShowExamples(true);
  const closeExamples = useCallback(() => setShowExamples(false), []);
  const candidate = useMemo(() => result?.candidates.find(item => item.candidate_id === selectedId) ?? null, [result, selectedId]);
  const saveHumanReview = (review: HumanReview) => {
    if (!result || review.analysisId !== result.analysis_id || !result.candidates.some(item => item.candidate_id === review.candidateId)) return false;
    if (!saveReview(review)) return false;
    setReviews(current => ({ ...current, [review.candidateId]: review })); notify('success', 'Review saved locally.');
    return true;
  };
  const deleteHumanReview = () => {
    if (!result || !selectedId || !deleteReview(result.analysis_id, selectedId)) return false;
    setReviews(current => { const next = { ...current }; delete next[selectedId]; return next; }); notify('info', 'Local review reset.');
    return true;
  };
  const selectedIndex = result?.candidates.findIndex(item => item.candidate_id === selectedId) ?? -1;
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (target.closest('input,textarea,select,[contenteditable="true"],button,[role="dialog"]')) return;
      if (event.key === 'Escape') { setShortcutsOpen(false); setMenuOpen(false); return; }
      if (event.key === '?' && (page === 'Analysis' || page === 'Candidates')) { setShortcutsOpen(open => !open); return; }
      if ((page !== 'Analysis' && page !== 'Candidates') || !result || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      const index = result.candidates.findIndex(item => item.candidate_id === selectedId);
      const next = index + (event.key === 'ArrowRight' ? 1 : -1);
      if (next >= 0 && next < result.candidates.length) { event.preventDefault(); setSelectedId(result.candidates[next].candidate_id); }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [page, result, selectedId]);
  const total = result?.summary.candidate_count ?? result?.candidates.length ?? 0;
  const geographicCount = result ? mapPoints(result.candidates).length : 0;
  const status = phase === 'running' ? 'ANALYZING' : phase === 'success' ? result?.processing.status ?? 'COMPLETED' : phase === 'error' || phase === 'invalid' ? 'FAILED' : 'READY';
  const ready = !quotaLimited && (health?.status === 'OK' || health?.status === 'REACHABLE');
  const spaceStatus = quotaLimited ? 'GPU LIMIT' : health?.status === 'REACHABLE' ? 'REACHABLE · GPU UNVERIFIED' : health?.status ?? (healthBusy ? 'CHECKING' : 'OFFLINE');
  const showWorkspace = page === 'Analysis' || page === 'Candidates';
  const leavePage = (name: string) => {
    if (name !== 'Analysis' && name !== 'Candidates' && analysisAbort.current) {
      analysisAbort.current.abort(); analysisAbort.current = null; requestVersion.current++;
      setPhase(file ? 'selected' : 'empty');
    }
    navigate(name, name === 'Reports' ? result?.analysis_id : undefined);
    if (name === 'Candidates') requestAnimationFrame(() => document.getElementById('candidates')?.scrollIntoView({ behavior: 'smooth' }));
  };

  return <div className="app-shell">
    <header className="topbar"><div className="brand"><button type="button" className="mobile-menu-trigger" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} onClick={() => setMenuOpen(open => !open)}>{menuOpen ? <X size={19} /> : <Menu size={19} />}</button><div className="brand-icon">S<span>•</span></div><div><strong>SONAR-SHIELD</strong><small>MARINE ANOMALY INTELLIGENCE</small></div></div><div className="topbar-meta">{result ? <span className={demo ? 'top-example-badge' : 'top-live-badge'}>{demo ? 'PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE' : 'LIVE ANALYSIS'}</span> : demoEnabled && <span className="top-demo-badge">DEMO MODE</span>}<span className="top-analysis"><span>ANALYSIS</span><strong>{result?.analysis_id ?? 'NO ACTIVE ANALYSIS'}</strong></span><span className="top-status"><span>SPACE API</span><strong><i className={`status-dot ${ready ? 'ready' : ''}`} />{spaceStatus}</strong></span></div></header>
    {menuOpen && <button type="button" className="mobile-nav-scrim" aria-label="Dismiss navigation overlay" onClick={() => setMenuOpen(false)} />}
    <div className="body-layout"><nav className={`sidebar ${menuOpen ? 'is-open' : ''}`} aria-label="Main navigation"><div className="nav-caption">WORKSPACE</div>{navigation.map(({ name, icon: Icon }) => <button type="button" key={name} className={page === name ? 'active' : ''} aria-current={page === name ? 'page' : undefined} onClick={() => leavePage(name)}><Icon className="nav-symbol" size={17} strokeWidth={1.8} />{name}</button>)}<div className="sidebar-system"><span className="nav-caption">SYSTEM · SPACE</span><div><span>API</span><strong className={ready ? 'good' : 'offline'}>{spaceStatus}</strong></div>{!health && <button type="button" className="health-retry" onClick={() => void checkHealth()} disabled={healthBusy} title={healthError?.message}>{healthBusy ? 'Checking…' : 'Retry connection'}</button>}</div></nav>
    <main className="main-content">{showWorkspace ? <>
      <div className="page-intro"><div><span className="eyebrow">SONAR WORKSPACE · F8 ANALYSIS</span><h1>Sonar analysis</h1><p>Inspect candidates, evidence, localization, and human review.</p></div><div className="workspace-state"><div><span>SELECTED / TOTAL</span><strong>{selectedIndex >= 0 ? selectedIndex + 1 : 0} / {total}</strong></div><div><span>GEOGRAPHIC</span><strong>{geographicCount} / {result?.candidates.length ?? 0}</strong></div><div><span>ANALYSIS STATUS</span><strong className={`workspace-status status-${status.toLowerCase()}`}>{status}</strong></div>{demo && <span className="demo-tag">PRECOMPUTED EXAMPLE</span>}</div></div>
      <RecordsPanel analysis={result} imageSrc={src} source={demo ? 'PRECOMPUTED_EXAMPLE' : 'LIVE_ANALYSIS'} reviews={reviews} onOpen={(value, image, source, savedReviews) => {
        analysisAbort.current?.abort(); analysisAbort.current = null;
        const version = ++requestVersion.current;
        setPhase(result ? 'success' : file ? 'selected' : 'empty'); setError(null);
        void exportRecord(value, image, source, savedReviews).then(text => importRecord(new File([text], 'shared.sonar.json', { type: 'application/json' }))).then(async record => {
          if (version !== requestVersion.current) return;
          await saveSession(record.result, record.image, record.source);
          if (version !== requestVersion.current) return;
          for (const review of record.reviews) if (!saveReview(review)) notify('error', 'A shared review could not be stored locally.');
          setResult(record.result); setSrc(URL.createObjectURL(record.image)); setDemo(record.source === 'PRECOMPUTED_EXAMPLE');
          setFile(record.source === 'LIVE_ANALYSIS' ? new File([record.image], record.result.input.filename, { type: record.image.type }) : null);
          setDimensions(record.result.input.width && record.result.input.height ? { width: record.result.input.width, height: record.result.input.height } : null);
          setSelectedId(record.result.candidates[0]?.candidate_id ?? null); setMetadataJson(''); setError(null); setPhase('success');
          setReviews(getReviews(record.result.analysis_id, record.result.candidates.map(c => c.candidate_id))); notify('info', 'Shared record opened; no inference ran.');
        }).catch(() => { if (version === requestVersion.current) notify('error', 'Shared record validation or storage failed. Current image remains available.'); });
      }} />
      <section className="judge-paths" aria-label="Judging paths"><p><strong>Live</strong> processes your uploaded image now. <strong>Verified example</strong> replays a previously completed analysis of the displayed sample image.</p><button type="button" className="secondary" onClick={openExamples}>Explore verified examples</button></section>
      <section className="record-tools panel" aria-label="Saved analysis record controls"><div className="record-tools-heading"><span className="eyebrow">ANALYSIS RECORD</span><p>Transfer your image, results and reviews, or attach navigation metadata before a live run.</p></div><div className="record-tool-actions">
      <button className="secondary" type="button" disabled={!result || !src} onClick={() => {
        if (!result || !src) return;
        void fetch(src).then(r => r.blob()).then(image => exportRecord(result, image, demo ? 'PRECOMPUTED_EXAMPLE' : 'LIVE_ANALYSIS', Object.values(reviews))).then(text => downloadText(`${safeAnalysisName(result.analysis_id)}.sonar.json`, text, 'application/json')).catch(() => notify('error', 'Could not export the complete analysis record.'));
      }}>Export complete record</button>
      <button className="secondary" type="button" disabled={phase === 'running'} onClick={() => {
        const chooser = document.createElement('input'); chooser.type = 'file'; chooser.accept = '.json';
        const version = requestVersion.current;
        chooser.onchange = () => { const recordFile = chooser.files?.[0]; if (!recordFile) return;
          void importRecord(recordFile).then(async record => {
            if (version !== requestVersion.current) return;
            const value = record.result;
            await saveSession(value, record.image, record.source);
            if (version !== requestVersion.current) return;
            requestVersion.current++;
            for (const review of record.reviews) if (!saveReview(review)) notify('error', 'A review could not be stored.');
            setResult(value); setSrc(URL.createObjectURL(record.image)); setDemo(record.source === 'PRECOMPUTED_EXAMPLE');
            setFile(record.source === 'LIVE_ANALYSIS' ? new File([record.image], value.input.filename, { type: record.image.type }) : null);
            setDimensions(value.input.width && value.input.height ? { width: value.input.width, height: value.input.height } : null);
            setSelectedId(value.candidates[0]?.candidate_id ?? null); setMetadataJson(''); setError(null); setPhase('success');
            setReviews(getReviews(value.analysis_id, value.candidates.map(c => c.candidate_id))); notify('info', 'Saved record opened; no inference ran.');
          }).catch(() => notify('error', 'Record is invalid or could not be saved. Current analysis remains available.'));
        }; chooser.click();
      }}>Import complete record</button>
      <button className="secondary" type="button" disabled={!file || phase === 'running'} onClick={() => {
        const chooser = document.createElement('input'); chooser.type = 'file'; chooser.accept = '.json,application/json';
        const version = requestVersion.current;
        chooser.onchange = () => { const sidecar = chooser.files?.[0]; if (!sidecar) return;
          if (sidecar.size > 256 * 1024) { notify('error', 'Metadata exceeds 256 KiB.'); return; }
          void sidecar.text().then(text => { if (version !== requestVersion.current) return;
            const data: unknown = JSON.parse(text);
            if (!data || typeof data !== 'object' || Array.isArray(data)) throw Error();
            setMetadataJson(text); notify('info', 'Metadata attached. Requires the corrected backend; invalid geometry will be rejected.');
          }).catch(() => notify('error', 'Metadata must be a valid JSON object.'));
        }; chooser.click();
      }}>Attach navigation metadata</button>
      {metadataJson && <button className="secondary" type="button" disabled={phase === 'running'} onClick={() => setMetadataJson('')}>Remove metadata</button>}
      <button className="secondary record-danger" type="button" onClick={() => void clearSession().then(() => notify('info', 'Saved session deleted. Current view and local reviews remain available.')).catch(() => notify('error', 'Could not delete saved session.'))}>Delete saved session</button>
      </div></section>
      <section className={`upload-bar ${drag ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={event => { event.preventDefault(); setDrag(false); selectFile(event.dataTransfer.files[0]); }}><input ref={inputRef} type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" hidden onChange={event => { selectFile(event.target.files?.[0]); event.currentTarget.value = ''; }} /><div className="upload-icon">↑</div><div className="upload-copy"><strong>{file ? file.name : result?.input.filename ?? 'DROP SONAR IMAGE'}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · ${dimensions ? `${dimensions.width} × ${dimensions.height} px · ` : ''}JPG / PNG` : 'Drag a file here or browse · JPG / PNG'}</span></div><div className="upload-actions"><button className="secondary" type="button" onClick={() => inputRef.current?.click()}>Browse image</button><button className="primary" type="button" onClick={run} disabled={!file || phase === 'running'}>{phase === 'running' && !demo ? 'Analyzing…' : 'Run analysis'}</button>{phase === 'running' && file && <button className="secondary" type="button" onClick={() => { analysisAbort.current?.abort(); analysisAbort.current = null; requestVersion.current++; setPhase('selected'); }}>Cancel</button>}</div></section>
      {showExamples && <VerifiedExamples busy={exampleBusy} onConfirm={id => void loadDemo(id)} onClose={closeExamples} />}
      {phase === 'running' && <div className="notice progress" role="status"><span className="spinner" /><div><strong>LIVE ANALYSIS IN PROGRESS</strong><span>Processing your uploaded sonar image. Candidate and evidence results are pending.</span></div></div>}
      {(phase === 'error' || phase === 'invalid') && <div className="notice error" role="alert"><strong>{phase === 'invalid' ? 'INVALID FILE' : error?.code === 'INVALID_API_RESPONSE' ? 'INVALID API RESPONSE' : error?.code === 'GPU_QUOTA_EXCEEDED' ? 'LIVE GPU LIMIT REACHED' : 'ANALYSIS FAILED'}</strong><span>{error?.message}</span><code>{error?.code}</code>{phase === 'error' && <div className="judge-error-actions"><button type="button" onClick={openExamples}>View verified example</button>{file && <button type="button" onClick={run}>Try live again later</button>}</div>}{error?.code === 'GPU_QUOTA_EXCEEDED' && <QuotaReset details={error.details} />}{error?.details && Object.keys(error.details).length > 0 && <details><summary>Technical details</summary><pre>{JSON.stringify(error.details, null, 2)}</pre></details>}</div>}
      {phase === 'success' && result && <div className="notice complete" role="status"><strong>{demo ? 'PRECOMPUTED EXAMPLE LOADED' : 'LIVE ANALYSIS COMPLETE'}</strong><span>{result.analysis_id} · {total} {total === 1 ? 'CANDIDATE' : 'CANDIDATES'}</span><button type="button" className="report-view-button" onClick={() => navigate('Reports', result.analysis_id)}>View report</button></div>}
      {result && <div className={`judge-source-banner ${demo ? '' : 'live'}`} role="note"><strong>{demo ? 'PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE' : 'LIVE ANALYSIS'}</strong><span>{demo ? 'This response was computed earlier for the displayed sample image. It is not an analysis of any image you uploaded.' : 'Live inference result for the displayed uploaded image. Opening a saved record runs no new inference.'}</span></div>}
      {result && !demo && result.schema_version !== 'F8.1' && <div className="notice neutral" role="note"><strong>LEGACY BACKEND OUTPUT</strong><span>This backend predates verified class mapping and provenance. Reliability and uncertainty fields may be placeholders. Review results cautiously.</span></div>}
      {phase === 'success' && total === 0 && <div className="notice neutral"><strong>NO CANDIDATES DETECTED</strong><span>The analysis pipeline returned no candidates for this image.</span></div>}
      <div className="workspace"><div className="workspace-left"><SonarViewer key={src ?? 'none'} src={src} filename={file?.name ?? null} dimensions={dimensions} result={result} selectedId={selectedId} onSelect={setSelectedId} onUpload={() => inputRef.current?.click()} /><CandidateList candidates={result?.candidates ?? []} selectedId={selectedId} onSelect={setSelectedId} hasAnalysis={result !== null} reviews={reviews} /></div><AnalysisPanel candidate={candidate} index={selectedIndex} result={result} review={selectedId ? reviews[selectedId] : undefined} onSaveReview={saveHumanReview} onDeleteReview={deleteHumanReview} onNavigate={offset => { const next = result?.candidates[selectedIndex + offset]; if (next) setSelectedId(next.candidate_id); }} /></div>
      {result && <><div className={`judge-source-banner ${demo ? '' : 'live'}`} role="note"><strong>{demo ? 'PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE' : 'LIVE ANALYSIS'}</strong><span>Human review below applies to the {demo ? 'displayed verified sample' : 'uploaded image'}.</span></div><ReviewSummary candidates={result.candidates} reviews={reviews} selectedId={selectedId} onSelect={setSelectedId} /></>}
      <Suspense fallback={<section className="sonar-map-section panel"><div className="sonar-map-empty">Loading geospatial workspace…</div></section>}><SonarMap result={result} selectedId={selectedId} reviews={reviews} onSelect={setSelectedId} /></Suspense>
      <button type="button" className="shortcut-help" onClick={() => setShortcutsOpen(open => !open)} aria-expanded={shortcutsOpen}><CircleHelp size={15} /> Keyboard shortcuts</button>{shortcutsOpen && <div className="shortcut-panel" role="note"><span><kbd>←</kbd> Previous candidate</span><span><kbd>→</kbd> Next candidate</span><span><kbd>?</kbd> Show shortcuts</span><span><kbd>Esc</kbd> Close</span></div>}
    </> : page === 'Reports' ? <Suspense fallback={<div className="report-empty panel">Loading report preview…</div>}><ReportPage key={`${result?.analysis_id ?? 'none'}-${demo}`} analysis={routePath.startsWith('/reports/') && result && routePath !== pagePath('Reports', result.analysis_id) ? null : result} source={demo ? 'PRECOMPUTED_EXAMPLE' : 'LIVE_ANALYSIS'} reviews={reviews} imageSrc={src} fileSize={file?.size ?? null} onBack={() => navigate('Analysis')} onToast={notify} /></Suspense> : page === 'Overview' ? <OverviewPage result={result} reviews={reviews} health={health} onAnalysis={() => navigate('Analysis')} onReports={() => navigate('Reports', result?.analysis_id)} /> : <SystemPage health={health} busy={healthBusy} onRetry={() => void checkHealth()} />}</main></div><ToastRegion toasts={toasts} dismiss={id => setToasts(current => current.filter(toast => toast.id !== id))} />
  </div>;
}
