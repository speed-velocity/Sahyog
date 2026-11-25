import type { DashboardOverview } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { HeartRateChart } from '../components/HeartRateChart';
import { Icon } from '../components/Icon';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { PageHeader } from '../components/PageHeader';
import { ReadingTable } from '../components/ReadingTable';
import { SectionCard } from '../components/SectionCard';
import { SimulatedNotice } from '../components/SimulatedNotice';
import { StatCard } from '../components/StatCard';
import {
  formatDateTime,
  formatHeartRate,
  formatRelativeTime,
  isReadingStale,
} from '../lib/format';
import { selectLatestReading, selectRecentReadings } from '../lib/readings';

interface MonitoringViewProps {
  overview: DashboardOverview | null;
  overviewError: Error | null;
  overviewLoading: boolean;
  onRetry: () => void;
}

export function MonitoringView({
  overview,
  overviewError,
  overviewLoading,
  onRetry,
}: MonitoringViewProps) {
  if (overviewLoading && !overview) {
    return (
      <>
        <PageHeader
          description="Simulated heart-rate readings returned by the backend."
          eyebrow="Health monitoring"
          title="Health monitoring"
        />
        <LoadingSkeleton cards={4} rows={6} />
      </>
    );
  }

  if (!overview) {
    return (
      <>
        <PageHeader
          description="Simulated heart-rate readings returned by the backend."
          eyebrow="Health monitoring"
          title="Health monitoring"
        />
        <ErrorState
          error={overviewError ?? new Error('No monitoring summary is available.')}
          onRetry={onRetry}
        />
      </>
    );
  }

  const monitoring = overview.monitoring;
  const latest = selectLatestReading(monitoring);
  const readings = selectRecentReadings(monitoring);
  const staleAfter = monitoring?.stale_after_seconds;
  const stale = latest ? isReadingStale(latest, staleAfter) : false;
  const rates = readings.map((reading) => reading.heart_rate_bpm);
  const average = rates.length > 0 ? rates.reduce((sum, value) => sum + value, 0) / rates.length : null;
  const minimum = rates.length > 0 ? Math.min(...rates) : null;
  const maximum = rates.length > 0 ? Math.max(...rates) : null;
  const simulatedCount = readings.filter(
    (reading) => reading.source_kind?.toUpperCase() === 'SIMULATED',
  ).length;

  return (
    <>
      <PageHeader
        actions={
          <button className="btn btn--ghost btn--sm" onClick={onRetry} type="button">
            <Icon name="refresh" size={15} />
            Reload
          </button>
        }
        description="Heart-rate history supplied by the backend. The dashboard does not invent readings or clinical thresholds."
        eyebrow="Health monitoring"
        title="Health monitoring"
      />

      <SimulatedNotice compact />

      {overviewError ? (
        <div className="notice notice--warning notice--compact">
          <span className="notice__icon">
            <Icon name="alert" size={16} />
          </span>
          <p>Live refresh failed. Showing the last successful backend response.</p>
        </div>
      ) : null}

      <div className="stat-grid stat-grid--compact">
        <StatCard
          hint={
            latest ? (
              <>
                {formatRelativeTime(latest.observed_at)}
                {stale ? ' · stale reading' : ' · fresh reading'}
              </>
            ) : (
              'No reading returned'
            )
          }
          icon="heart"
          label="Latest reading"
          tone="blue"
          value={formatHeartRate(latest?.heart_rate_bpm)}
        />
        <StatCard
          hint={`From ${readings.length} returned readings`}
          icon="activity"
          label="Average"
          tone="teal"
          value={formatHeartRate(average)}
        />
        <StatCard
          hint={`${simulatedCount} marked simulated`}
          icon="shield"
          label="Minimum / maximum"
          tone="slate"
          value={
            minimum !== null && maximum !== null
              ? `${Math.round(minimum)} / ${Math.round(maximum)} bpm`
              : 'Unavailable'
          }
        />
        <StatCard
          hint={
            monitoring?.stale_after_seconds
              ? `Backend freshness window: ${Math.round(monitoring.stale_after_seconds)} s`
              : 'Freshness window not reported'
          }
          icon="clock"
          label="Last observed"
          tone={stale ? 'amber' : 'teal'}
          value={latest ? formatDateTime(latest.observed_at) : 'Unavailable'}
        />
      </div>

      <SectionCard
        actions={
          latest ? (
            <span className="muted">
              Latest {formatHeartRate(latest.heart_rate_bpm)} · {formatRelativeTime(latest.observed_at)}
            </span>
          ) : undefined
        }
        subtitle="Plotted from readings returned by the backend, in observed-time order. No clinical threshold lines are drawn."
        title="Heart-rate trend"
      >
        <HeartRateChart readings={readings} staleAfterSeconds={staleAfter} />
      </SectionCard>

      {latest && readings.length <= 1 ? (
        <div className="notice notice--info notice--compact">
          <span className="notice__icon">
            <Icon name="activity" size={16} />
          </span>
          <p>
            Only one reading was returned by the backend, so no trend line can be drawn. The latest
            reading is still shown above.
          </p>
        </div>
      ) : null}

      <SectionCard
        subtitle="Most recent first. Times are displayed in your local timezone."
        title="Reading history"
      >
        {readings.length === 0 ? (
          <EmptyState
            description="The backend has not returned recent heart-rate readings for this monitored person."
            icon="heart"
            title="No readings available"
          />
        ) : (
          <ReadingTable readings={readings} staleAfterSeconds={staleAfter} />
        )}
      </SectionCard>

      <p className="detail-disclaimer">
        <Icon name="shield" size={14} /> SAHYOG is a prototype. Readings are simulated unless the
        backend explicitly reports another source. They are not clinical measurements.
      </p>
    </>
  );
}
