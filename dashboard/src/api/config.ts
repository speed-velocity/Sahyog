const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';
const DEFAULT_POLL_INTERVAL_MS = 10_000;
export const REQUEST_TIMEOUT_MS = 8_000;

function readPositiveInteger(raw: string | undefined, fallback: number): number {
  if (!raw) {
    return fallback;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function normalizeBaseUrl(raw: string | undefined): string {
  if (!raw || raw.trim().length === 0) {
    return DEFAULT_API_BASE_URL;
  }

  try {
    const parsed = new URL(raw.trim());
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return DEFAULT_API_BASE_URL;
    }
    return parsed.toString().replace(/\/+$/, '');
  } catch {
    return DEFAULT_API_BASE_URL;
  }
}

export const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL);

export const POLL_INTERVAL_MS = readPositiveInteger(
  import.meta.env.VITE_DASHBOARD_POLL_INTERVAL_MS,
  DEFAULT_POLL_INTERVAL_MS,
);

export const INCIDENT_PAGE_LIMIT = 25;
export const READING_HISTORY_LIMIT = 30;
export const HOSPITAL_RESULT_LIMIT = 5;
