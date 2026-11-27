import type { DashboardOverview, IncidentSummary } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { Icon } from '../components/Icon';
import { IncidentList } from '../components/IncidentList';
import { LatestReadingCard } from '../components/LatestReadingCard';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { LocationCard } from '../components/LocationCard';
import { PageHeader } from '../components/PageHeader';
import { PersonCard } from '../components/PersonCard';
import { SectionCard } from '../components/SectionCard';
import { SimulatedNotice } from '../components/SimulatedNotice';
import { StatCard } from '../components/StatCard';
import { StatusBadge } from '../components/StatusBadge';
import type { ViewKey } from '../components/Sidebar';
import { formatHeartRate, formatRelativeTime } from '../lib/format';
import { getStatusMeta, isEscalatedStatus } from '../lib/status';
import { selectLatestReading, selectRecentReadings } from '../lib/readings';

interface OverviewViewProps {
  overview: DashboardOverview | null;
  overviewError: Error | null;
  overviewLoading: boolean;
  incidents: IncidentSummary[];
  incidentsError: Error | null;
  onRetry: () => void;
  onNavigate: (view: ViewKey) => void;
  onSelectIncident: (incidentId: string) => void;
}

function ActiveIncidentSummary({
  incident,
  onSelectIncident,
}: {
  incident: IncidentSummary;
  onSelectIncident: (incidentId: string) => void;
}) {
  const status = getStatusMeta(incident.status);
  return (
    <div className="active-response">
      <div className="active-response__head">
        <div>
          <StatusBadge {...status} dot />
          <p className="active-response__title">
            Incident <span className="mono">{incident.incident_id.slice(0, 8)}…</span>
          </p>
          <p className="muted">Created {formatRelativeTime(incident.created_at)}</p>
        </div>
        <button
          className="btn btn--secondary btn--sm"
          onClick={() => onSelectIncident(incident.incident_id)}
          type="button"
        >
          Open incident
          <Icon name="chevronRight" size={15} />
        </button>
      </div>

      <p className="muted">The overview API reports status and timestamps only; verification and delivery details are not included.</p>
    </div>
  );
}

export function OverviewView({
  overview,
  overviewError,
  overviewLoading,
  incidents,
  incidentsError,
  onRetry,
  onNavigate,
  onSelectIncident,
}: OverviewViewProps) {
  if (overviewLoading && !overview) {
    return (
      <>
        <PageHeader
          description="Backend-authoritative monitoring and emergency activity."
          eyebrow="Caregiver console"
          title="Overview"
        />
        <LoadingSkeleton cards={4} rows={5} />
      </>
    );
  }

  if (!overview) {
    return (
      <>
        <PageHeader
          description="Backend-authoritative monitoring and emergency activity."
          eyebrow="Caregiver console"
          title="Overview"
        />
        <ErrorState
          error={overviewError ?? new Error('No dashboard overview is available.')}
          onRetry={onRetry}
        />
        <SimulatedNotice />
      </>
    );
  }

  const monitoring = overview.monitoring;
  const subject_user_id = overview.subject_user_id;
  const subject = subject_user_id ? { user_id: subject_user_id } : null;
  const latestReading = selectLatestReading(monitoring);
  const recentReadings = selectRecentReadings(monitoring);
  const recentIncidents = incidents;
  const primaryIncident = overview.active_incident_id
    ? incidents.find((incident) => incident.incident_id === overview.active_incident_id) ?? null
    : null;
  const monitoringMeta = getStatusMeta(monitoring.status);

  return (
    <>
      <PageHeader
        actions={
          <button className="btn btn--ghost btn--sm" onClick={onRetry} type="button">
            <Icon name="refresh" size={15} />
            Reload
          </button>
        }
        description="Backend-authoritative monitoring and emergency activity for the monitored person."
        eyebrow="Caregiver console"
        title="Overview"
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

      {isEscalatedStatus(primaryIncident?.status) ? (
        <div className="notice notice--danger">
          <span className="notice__icon">
            <Icon name="alert" size={18} />
          </span>
          <p>
            <strong>Escalated incident status reported by the backend.</strong> This API response
            does not include notification delivery or acknowledgement details.
          </p>
        </div>
      ) : primaryIncident?.status.toUpperCase() === 'PENDING_VERIFICATION' ? (
        <div className="notice notice--info">
          <span className="notice__icon">
            <Icon name="clock" size={18} />
          </span>
          <p>
            <strong>Pending verification status reported by the backend.</strong> The incident API
            does not return a verification response record.
          </p>
        </div>
      ) : monitoring.status.toUpperCase() === 'NORMAL' ? (
        <div className="notice notice--success notice--compact">
          <span className="notice__icon">
            <Icon name="check" size={16} />
          </span>
          <p>
            <strong>No active incident reported.</strong> The backend monitoring status is NORMAL.
          </p>
        </div>
      ) : (
        <div className="notice notice--info notice--compact">
          <span className="notice__icon">
            <Icon name="activity" size={16} />
          </span>
          <p>The backend did not provide a detector status in its dashboard overview.</p>
        </div>
      )}

      <div className="stat-grid">
        <StatCard
          aside={<StatusBadge {...monitoringMeta} />}
          hint="Reported by the monitoring summary"
          icon="activity"
          label="Monitoring status"
          tone="teal"
          value={monitoringMeta.label}
        />
        <StatCard
          aside={
            latestReading ? (
              <StatusBadge label="Freshness not reported" tone="neutral" />
            ) : null
          }
          hint={
            latestReading ? (
              <>
                {formatRelativeTime(latestReading.observed_at)} ·{' '}
                {latestReading.source_kind?.toUpperCase() === 'SIMULATED' ? 'Simulated' : 'Source reported'}
              </>
            ) : (
              'No reading returned'
            )
          }
          icon="heart"
          label="Latest heart rate"
          tone="blue"
          value={formatHeartRate(latestReading?.heart_rate_bpm)}
        />
        <StatCard
          hint={overview.active_incident_id ?? 'No active incident ID returned'}
          icon="alert"
          label="Active incident"
          tone={overview.active_incident_id ? 'red' : 'slate'}
          value={overview.active_incident_id ? 'Reported' : 'None reported'}
        />
      </div>

      <div className="overview-grid">
        <SectionCard
          actions={
            <button className="btn btn--ghost btn--sm" onClick={() => onNavigate('monitoring')} type="button">
              Monitoring
              <Icon name="chevronRight" size={15} />
            </button>
          }
          subtitle="Identity and monitoring context returned by the backend."
          title="Monitored person"
        >
          <PersonCard
            dataSource={monitoring?.data_source}
            monitoringStatus={monitoring?.status}
            subject={subject}
          />
        </SectionCard>

        <SectionCard
          actions={
            <button className="btn btn--ghost btn--sm" onClick={() => onNavigate('monitoring')} type="button">
              Reading history
              <Icon name="chevronRight" size={15} />
            </button>
          }
          subtitle="The backend overview returns the latest reading only; it does not report reading history or freshness."
          title="Latest reading"
        >
          <LatestReadingCard
            latestReading={latestReading}
            onViewHistory={() => onNavigate('monitoring')}
            recentReadings={recentReadings}
            staleAfterSeconds={null}
          />
        </SectionCard>
      </div>

      <div className="overview-layout">
        <div className="overview-layout__main">
          <SectionCard
            subtitle="The incident ID and status returned by the backend overview."
            title="Active response"
          >
            {primaryIncident ? (
              <ActiveIncidentSummary
                incident={primaryIncident}
                onSelectIncident={onSelectIncident}
              />
            ) : (
              <EmptyState
                compact
                description="The backend overview did not return an active incident ID."
                icon="check"
                title="No active emergency response"
              />
            )}
          </SectionCard>

          <SectionCard
            actions={
              <button className="btn btn--ghost btn--sm" onClick={() => onNavigate('incidents')} type="button">
                All incidents
                <Icon name="chevronRight" size={15} />
              </button>
            }
            subtitle="Most recent incidents returned by the backend."
            title="Recent emergency activity"
          >
            {incidentsError && incidents.length === 0 ? (
              <ErrorState
                compact
                error={incidentsError}
                onRetry={onRetry}
                title="Recent incidents unavailable"
              />
            ) : (
              <IncidentList
                emptyDescription="No incidents have been reported for this monitored person."
                emptyTitle="No recent incidents"
                incidents={recentIncidents.slice(0, 4)}
                onSelect={onSelectIncident}
                selectedId={null}
              />
            )}
          </SectionCard>
        </div>

        <div className="overview-layout__side">
          <SectionCard
            actions={
              <button className="btn btn--ghost btn--sm" onClick={() => onNavigate('location')} type="button">
                Location
                <Icon name="chevronRight" size={15} />
              </button>
            }
            subtitle="Location is loaded from the authorised location endpoint."
            title="Location"
          >
            <LocationCard
              emptyDescription="Open Location and support to load an authorised location snapshot."
              location={null}
            />
          </SectionCard>

          <SectionCard subtitle="Only fields returned by the current backend routes are displayed." title="Data availability">
            <p className="muted">The current overview returns monitoring status, one latest reading, and an active incident reference. The incident routes return status and timestamps; they do not include detector evidence, verification responses, notifications, or timeline events.</p>
          </SectionCard>
        </div>
      </div>
    </>
  );
}
