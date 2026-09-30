import type { HumanReviewStatus } from '../../review/reviewStore';

export const reviewLabel = (status: HumanReviewStatus) => status.replaceAll('_', ' ');

export default function ReviewStatusBadge({ status }: { status: HumanReviewStatus }) {
  return <span className={`review-badge review-${status.toLowerCase()}`} aria-label={`Human review state: ${reviewLabel(status)}`}>{reviewLabel(status)}</span>;
}
