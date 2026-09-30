export const REVIEW_STORAGE_KEY = 'sonarShield.review.v1';

export type HumanReviewStatus = 'NOT_REVIEWED' | 'CONFIRMED' | 'FALSE_POSITIVE' | 'NEEDS_INVESTIGATION';
export type HumanReview = {
  analysisId: string;
  candidateId: string;
  status: Exclude<HumanReviewStatus, 'NOT_REVIEWED'>;
  note: string;
  reviewedAt: string;
};

type StoredReviews = { version: 1; reviews: Record<string, HumanReview> };
const statuses = new Set<HumanReviewStatus>(['CONFIRMED', 'FALSE_POSITIVE', 'NEEDS_INVESTIGATION']);
const keyFor = (analysisId: string, candidateId: string) => JSON.stringify([analysisId, candidateId]);
const empty = (): StoredReviews => ({ version: 1, reviews: {} });

export function isReview(value: unknown): value is HumanReview {
  if (!value || typeof value !== 'object') return false;
  const review = value as Partial<HumanReview>;
  return typeof review.analysisId === 'string' && review.analysisId.length > 0
    && typeof review.candidateId === 'string' && review.candidateId.length > 0
    && statuses.has(review.status as HumanReviewStatus)
    && typeof review.note === 'string'
    && typeof review.reviewedAt === 'string' && !Number.isNaN(Date.parse(review.reviewedAt));
}

function readStore(): StoredReviews {
  try {
    const raw = localStorage.getItem(REVIEW_STORAGE_KEY);
    if (!raw) return empty();
    const data: unknown = JSON.parse(raw);
    if (!data || typeof data !== 'object' || (data as StoredReviews).version !== 1) return empty();
    const values = (data as StoredReviews).reviews;
    if (!values || typeof values !== 'object' || Array.isArray(values)) return empty();
    const reviews: Record<string, HumanReview> = {};
    for (const [key, value] of Object.entries(values)) {
      if (isReview(value) && key === keyFor(value.analysisId, value.candidateId)) reviews[key] = value;
    }
    return { version: 1, reviews };
  } catch { return empty(); }
}

export function getReviews(analysisId: string, candidateIds: string[]): Record<string, HumanReview> {
  const stored = readStore().reviews;
  const reviews: Record<string, HumanReview> = {};
  for (const candidateId of candidateIds) {
    const value = stored[keyFor(analysisId, candidateId)];
    if (value) reviews[candidateId] = value;
  }
  return reviews;
}

export function saveReview(review: HumanReview): boolean {
  if (!isReview(review)) return false;
  try {
    const store = readStore();
    store.reviews[keyFor(review.analysisId, review.candidateId)] = review;
    localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(store));
    return true;
  } catch { return false; }
}

export function deleteReview(analysisId: string, candidateId: string): boolean {
  try {
    const store = readStore();
    delete store.reviews[keyFor(analysisId, candidateId)];
    localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(store));
    return true;
  } catch { return false; }
}
