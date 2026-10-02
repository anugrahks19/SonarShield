import { isReview } from '../review/reviewStore';
import { analyzeSchema } from '../api/schema';
import type { AnalyzeResponse } from '../types';
import type { ResultSource } from '../reports/export';
type Session = { version: 1; result: AnalyzeResponse; image: Blob; source: ResultSource; savedAt: string; metadataJson?: string };
const MAX_BYTES = 32 * 1024 * 1024;
async function database(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('sonar-shield-records', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('sessions');
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function operation<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest): Promise<T> {
  const db = await database();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction('sessions', mode);
    const request = action(transaction.objectStore('sessions'));
    transaction.oncomplete = () => { db.close(); resolve(request.result as T); };
    transaction.onerror = () => { db.close(); reject(transaction.error); };
    transaction.onabort = () => { db.close(); reject(transaction.error ?? new Error('Storage aborted.')); };
  });
}
// Calls serialize so old writes cannot complete after a clear/newer session.
let pending: Promise<unknown> = Promise.resolve();
export function saveSession(result: AnalyzeResponse, image: Blob, source: ResultSource, metadataJson = ''): Promise<void> {
  if (image.size > MAX_BYTES) return Promise.reject(new Error('Image exceeds local storage limit.'));
  const value: Session = { version: 1, result: analyzeSchema.parse(result), image, source, metadataJson, savedAt: new Date().toISOString() };
  const task = pending.catch(() => {}).then(() => operation<void>('readwrite', store => store.put(value, 'active')));
  pending = task; return task;
}
export async function restoreSession(): Promise<Session | null> {
  const value = await operation<Session | undefined>('readonly', store => store.get('active'));
  if (!value) return null;
  if (value.version !== 1 || !(value.image instanceof Blob) || value.image.size > MAX_BYTES || !['LIVE_ANALYSIS','PRECOMPUTED_EXAMPLE'].includes(value.source)) throw new Error('Stored record is invalid.');
  if (value.metadataJson !== undefined && (typeof value.metadataJson !== 'string' || new TextEncoder().encode(value.metadataJson).length > 256 * 1024)) throw new Error('Stored metadata is invalid.');
  const result = analyzeSchema.parse(value.result);
  if (value.source === 'PRECOMPUTED_EXAMPLE' || result.schema_version === 'F8.1') {
    const bytes = new Uint8Array(await crypto.subtle.digest('SHA-256', await value.image.arrayBuffer()));
    const hash = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
    if (hash !== result.input.sha256) throw new Error('Stored image does not match analysis.');
  }
  return { ...value, result };
}
export function clearSession(): Promise<void> {
  const task = pending.catch(() => {}).then(() => operation<void>('readwrite', store => store.delete('active')));
  pending = task; return task;
}


// Portable records retain result source and pair identity independently of legacy provenance.
export async function exportRecord(result: AnalyzeResponse, image: Blob, source: ResultSource, reviews: unknown): Promise<string> {
  if (!image.size || image.size > MAX_BYTES) throw new Error('Record image size is invalid.');
  const imageHash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', await image.arrayBuffer())), b => b.toString(16).padStart(2,'0')).join('');
  const imageData = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(reader.error); reader.readAsDataURL(image);
  });
  return JSON.stringify({ format: 'SONAR_SHIELD_RECORD', version: 1, source, result: analyzeSchema.parse(result), image_sha256: imageHash, image_data: imageData, reviews });
}
export async function importRecord(file: File): Promise<{ result: AnalyzeResponse; image: Blob; source: ResultSource; reviews: import('../review/reviewStore').HumanReview[] }> {
  if (file.size > 48 * 1024 * 1024) throw new Error('Record exceeds 48 MiB.');
  const record = JSON.parse(await file.text());
  if (record.format !== 'SONAR_SHIELD_RECORD' || record.version !== 1 || !['LIVE_ANALYSIS','PRECOMPUTED_EXAMPLE'].includes(record.source)) throw new Error('Unsupported record.');
  const result = analyzeSchema.parse(record.result);
  if (typeof record.image_data !== 'string' || !/^data:image\/(jpeg|png);base64,[A-Za-z0-9+/=]+$/.test(record.image_data)) throw new Error('Invalid record image.');
  const [header, encoded] = record.image_data.split(',');
  const binary = atob(encoded);
  if (!binary.length || binary.length > MAX_BYTES) throw new Error('Record image size is invalid.');
  const image = new Blob([Uint8Array.from(binary, c => c.charCodeAt(0))], { type: header.includes('png') ? 'image/png' : 'image/jpeg' });
  const actual = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', await image.arrayBuffer())), b => b.toString(16).padStart(2,'0')).join('');
  if (actual !== record.image_sha256 || ((result.schema_version === 'F8.1' || record.source === 'PRECOMPUTED_EXAMPLE') && actual !== result.input.sha256)) throw new Error('Record image hash mismatch.');
  if (!Array.isArray(record.reviews) || record.reviews.length > result.candidates.length) throw new Error('Invalid record reviews.');
  for (const review of record.reviews) if (!isReview(review) || review.analysisId !== result.analysis_id || !result.candidates.some(c => c.candidate_id === review.candidateId) || review.note.length > 20000) throw new Error('Review identity does not match record.');
  return { result, image, source: record.source, reviews: record.reviews };
}
