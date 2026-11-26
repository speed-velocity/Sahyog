import type { HealthReading, MonitoringSummary } from '../api/types';

export function selectLatestReading(
  monitoring: MonitoringSummary | null | undefined,
): HealthReading | null {
  if (monitoring?.latest_reading) {
    return monitoring.latest_reading;
  }
  const history = monitoring?.recent_readings ?? [];
  if (history.length === 0) {
    return null;
  }
  return [...history].sort(
    (left, right) => Date.parse(right.observed_at) - Date.parse(left.observed_at),
  )[0] ?? null;
}

export function selectRecentReadings(
  monitoring: MonitoringSummary | null | undefined,
): HealthReading[] {
  const byId = new Map<string, HealthReading>();
  for (const reading of monitoring?.recent_readings ?? []) {
    byId.set(reading.reading_id, reading);
  }
  const latest = monitoring?.latest_reading;
  if (latest && !byId.has(latest.reading_id)) {
    byId.set(latest.reading_id, latest);
  }
  return [...byId.values()].sort(
    (left, right) => Date.parse(right.observed_at) - Date.parse(left.observed_at),
  );
}
