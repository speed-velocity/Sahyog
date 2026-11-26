import type { HealthReading, LocationSnapshot } from '../api/types';

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

const relativeFormatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
const DEFAULT_STALE_AFTER_SECONDS = 120;

function parseTimestamp(value: string | null | undefined): number | null {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatDateTime(value: string | null | undefined): string {
  const parsed = parseTimestamp(value);
  return parsed === null ? 'Unavailable' : dateTimeFormatter.format(parsed);
}

export function formatClockTime(value: string | null | undefined): string {
  const parsed = parseTimestamp(value);
  return parsed === null ? 'Unavailable' : timeFormatter.format(parsed);
}

export function formatRelativeTime(value: string | null | undefined, now = Date.now()): string {
  const parsed = parseTimestamp(value);
  if (parsed === null) {
    return 'Unknown time';
  }

  const differenceSeconds = Math.round((parsed - now) / 1000);
  if (Math.abs(differenceSeconds) < 45) {
    return 'Just now';
  }

  const divisions: Array<{ amount: number; unit: Intl.RelativeTimeFormatUnit }> = [
    { amount: 60, unit: 'second' },
    { amount: 60, unit: 'minute' },
    { amount: 24, unit: 'hour' },
    { amount: 7, unit: 'day' },
    { amount: 4.34524, unit: 'week' },
    { amount: 12, unit: 'month' },
    { amount: Number.POSITIVE_INFINITY, unit: 'year' },
  ];

  let duration = differenceSeconds;
  for (const division of divisions) {
    if (Math.abs(duration) < division.amount) {
      return relativeFormatter.format(Math.round(duration), division.unit);
    }
    duration /= division.amount;
  }

  return 'Unknown time';
}

export function formatTimestampTitle(value: string | null | undefined): string {
  return value && parseTimestamp(value) !== null ? value : 'Timestamp unavailable';
}

export function formatHeartRate(value: number | null | undefined): string {
  return typeof value === 'number' && Number.isFinite(value) ? `${Math.round(value)} bpm` : 'Unavailable';
}

export function formatCoordinate(value: number | null | undefined): string {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(5) : '—';
}

export function formatCoordinates(
  latitude: number | null | undefined,
  longitude: number | null | undefined,
): string {
  if (
    typeof latitude !== 'number' ||
    !Number.isFinite(latitude) ||
    typeof longitude !== 'number' ||
    !Number.isFinite(longitude)
  ) {
    return 'Coordinates unavailable';
  }
  return `${formatCoordinate(latitude)}, ${formatCoordinate(longitude)}`;
}

export function formatDistance(distanceMeters: number | null | undefined): string {
  if (typeof distanceMeters !== 'number' || !Number.isFinite(distanceMeters) || distanceMeters < 0) {
    return 'Distance unavailable';
  }
  if (distanceMeters < 1000) {
    return `${Math.round(distanceMeters)} m`;
  }
  return `${(distanceMeters / 1000).toFixed(1)} km`;
}

export function getReadingAgeSeconds(
  observedAt: string | null | undefined,
  now = Date.now(),
): number | null {
  const parsed = parseTimestamp(observedAt);
  return parsed === null ? null : Math.max(0, Math.round((now - parsed) / 1000));
}

export function isReadingStale(
  reading: HealthReading,
  staleAfterSeconds: number | null | undefined,
  now = Date.now(),
): boolean {
  if (reading.is_stale === true) {
    return true;
  }
  const age = getReadingAgeSeconds(reading.observed_at, now);
  if (age === null) {
    return true;
  }
  const threshold =
    typeof staleAfterSeconds === 'number' && staleAfterSeconds > 0
      ? staleAfterSeconds
      : DEFAULT_STALE_AFTER_SECONDS;
  return age > threshold;
}

export function isLocationStale(
  location: LocationSnapshot,
  now = Date.now(),
): boolean {
  if (location.is_stale === true) {
    return true;
  }
  const captured = parseTimestamp(location.captured_at);
  if (captured === null) {
    return true;
  }
  const threshold =
    typeof location.stale_after_seconds === 'number' && location.stale_after_seconds > 0
      ? location.stale_after_seconds
      : 300;
  return now - captured > threshold * 1000;
}

const SOURCE_LABELS: Record<string, string> = {
  SIMULATED: 'Simulated',
  DEVICE: 'Device',
  GPS: 'Device location',
  SEEDED: 'Seeded demo data',
  SEEDED_DEMO: 'Seeded demo data',
};

export function formatSource(value: string | null | undefined): string {
  if (!value) {
    return 'Source not reported';
  }
  return SOURCE_LABELS[value.toUpperCase()] ?? value;
}

export function isSimulatedSource(value: string | null | undefined): boolean {
  return value?.toUpperCase() === 'SIMULATED';
}

export function humanizeToken(value: string | null | undefined): string {
  if (!value) {
    return 'Unknown';
  }
  const normalized = value.replace(/[_-]+/g, ' ').trim().toLowerCase();
  if (normalized.length === 0) {
    return value;
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

export function shortId(value: string | null | undefined): string {
  if (!value) {
    return 'Unknown ID';
  }
  return value.length <= 12 ? value : `${value.slice(0, 8)}…`;
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return count === 1 ? singular : (plural ?? `${singular}s`);
}
