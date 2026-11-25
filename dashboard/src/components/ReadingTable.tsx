import type { HealthReading } from '../api/types';
import {
  formatClockTime,
  formatDateTime,
  formatHeartRate,
  formatSource,
  formatTimestampTitle,
  isReadingStale,
  isSimulatedSource,
} from '../lib/format';
import { EmptyState } from './EmptyState';
import { StatusBadge } from './StatusBadge';

interface ReadingTableProps {
  readings: HealthReading[];
  staleAfterSeconds: number | null | undefined;
  limit?: number;
}

export function ReadingTable({ readings, staleAfterSeconds, limit = 20 }: ReadingTableProps) {
  const sorted = [...readings]
    .sort((left, right) => Date.parse(right.observed_at) - Date.parse(left.observed_at))
    .slice(0, limit);

  if (sorted.length === 0) {
    return (
      <EmptyState
        compact
        description="No recent heart-rate readings were returned by the backend."
        icon="heart"
        title="No reading history"
      />
    );
  }

  return (
    <div className="table-wrapper">
      <table className="table">
        <caption className="visually-hidden">
          Recent simulated heart-rate readings returned by the backend
        </caption>
        <thead>
          <tr>
            <th scope="col">Observed</th>
            <th scope="col">Heart rate</th>
            <th scope="col">Source</th>
            <th scope="col">Activity</th>
            <th scope="col">Freshness</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((reading) => {
            const stale = isReadingStale(reading, staleAfterSeconds);
            const simulated = isSimulatedSource(reading.source_kind);
            return (
              <tr key={reading.reading_id}>
                <td>
                  <time
                    dateTime={reading.observed_at}
                    title={formatTimestampTitle(reading.observed_at)}
                  >
                    {formatDateTime(reading.observed_at)}
                  </time>
                  <span className="table__secondary">{formatClockTime(reading.observed_at)}</span>
                </td>
                <td className="table__strong">{formatHeartRate(reading.heart_rate_bpm)}</td>
                <td>
                  <div className="table__badges">
                    <StatusBadge
                      label={formatSource(reading.source_kind)}
                      tone={simulated ? 'accent' : 'neutral'}
                    />
                  </div>
                </td>
                <td>{reading.activity_context ?? 'Not reported'}</td>
                <td>
                  <StatusBadge label={stale ? 'Stale' : 'Fresh'} tone={stale ? 'warning' : 'success'} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
