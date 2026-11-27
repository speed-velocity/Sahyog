import type { DashboardOverview } from '../api/types';
import { ErrorState } from '../components/ErrorState';
import { Icon } from '../components/Icon';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { LatestReadingCard } from '../components/LatestReadingCard';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { SimulatedNotice } from '../components/SimulatedNotice';
import { StatCard } from '../components/StatCard';
import { StatusBadge } from '../components/StatusBadge';
import { getStatusMeta } from '../lib/status';

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
  const latest = monitoring.latest_reading;
  const status = getStatusMeta(monitoring.status);

  return (
    <>
      <PageHeader
        actions={
          <button className="btn btn--ghost btn--sm" onClick={onRetry} type="button">
            <Icon name="refresh" size={15} />
            Reload
          </button>
        }
        description="The current backend overview provides a monitoring status and latest reading; no reading-history endpoint is available."
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
          aside={<StatusBadge {...status} />}
          hint="Exact value returned by the backend overview"
          icon="activity"
          label="Monitoring status"
          tone="teal"
          value={status.label}
        />
        <StatCard
          hint={latest ? `Source: ${latest.source_kind}` : 'No latest reading returned'}
          icon="heart"
          label="Latest heart rate"
          tone="blue"
          value={latest ? `${latest.heart_rate_bpm} bpm` : 'Unavailable'}
        />
      </div>

      <SectionCard
        subtitle="No freshness window or reading-history list is returned by the current endpoint."
        title="Latest backend reading"
      >
        <LatestReadingCard
          latestReading={latest}
          onViewHistory={onRetry}
          recentReadings={[]}
          staleAfterSeconds={null}
        />
      </SectionCard>

      <div className="notice notice--info notice--compact">
        <span className="notice__icon">
          <Icon name="activity" size={16} />
        </span>
        <p>Reading history, averages, freshness thresholds, and detector decisions are not included in the available dashboard overview response.</p>
      </div>

      <p className="detail-disclaimer">
        <Icon name="shield" size={14} /> SAHYOG is a prototype. Readings are simulated unless the
        backend explicitly reports another source. They are not clinical measurements.
      </p>
    </>
  );
}
