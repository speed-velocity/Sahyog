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
import { formatHeartRate, formatRelativeTime, isReadingStale } from '../lib/format';
import {
  getNotificationMeta,
  getStatusMeta,
  isEscalatedStatus,
} from '../lib/status';
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

function ActiveResponseSummary({
  incident,
  onSelectIncident,
}: {
  incident: IncidentSummary;
  onSelectIncident: (incidentId: string) => void;
}) {
  const status = getStatusMeta(incident.status);
  const responses = incident.verification?.responses ?? [];
  const confirmed = responses.some(
    (response) => response.response_value.toUpperCase() === 'I_AM_OK',
  );
  const pending =
    incident.verification?.pending === true || incident.status.toUpperCase() === 'VERIFICATION_PENDING';
  const attempts = incident.escalation_attempts ?? [];
  const notificationResults = attempts.flatMap((attempt) => attempt.notifications ?? []);

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

      <dl className="active-response__grid">
        <div>
          <dt>Verification</dt>
          <dd>
            {pending
              ? 'Pending response'
              : confirmed
                ? "Explicit 'I'm okay' recorded"
                : statusValueOrFallback(incident.verification?.status)}
          </dd>
        </div>
        <div>
          <dt>Escalation attempts</dt>
          <dd>{attempts.length > 0 ? attempts.length : 'None recorded'}</dd>
        </div>
        <div>
          <dt>Notification results</dt>
          <dd>
            {notificationResults.length === 0 ? (
              'None recorded'
            ) : (
              <span className="inline-badges">
                {notificationResults.slice(0, 3).map((notification, index) => {
                  const result = getNotificationMeta(notification.result);
                  return <StatusBadge {...result} key={notification.notification_attempt_id ?? index} />;
                })}
              </span>
            )}
          </dd>
        </div>
      </dl>

      <p className="detail-disclaimer">
        <Icon name="shield" size={14} /> Status, verification, and notification results are read
        from the backend. A simulated notification was not sent to a real recipient.
      </p>
    </div>
  );
}

function statusValueOrFallback(value: string | null | undefined): string {
  return value ? getStatusMeta(value).label : 'No active verification';
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
  const subject = overview.subject;
  const latestReading = selectLatestReading(monitoring);
  const recentReadings = selectRecentReadings(monitoring);
  const activeIncidents = overview.active_incidents ?? null;
  const activeCount =
    typeof overview.active_incident_count === 'number'
      ? overview.active_incident_count
      : activeIncidents
        ? activeIncidents.length
        : null;
  const recentIncidents =
    overview.recent_incidents && overview.recent_incidents.length > 0
      ? overview.recent_incidents
      : incidents;
  const primaryIncident = activeIncidents?.[0] ?? recentIncidents[0] ?? null;
  const detectionStatus = monitoring?.detection_status;
  const detectionMeta = getStatusMeta(detectionStatus);
  const monitoringMeta = getStatusMeta(monitoring?.status);
  const stale = latestReading
    ? isReadingStale(latestReading, monitoring?.stale_after_seconds)
    : false;
  const location =
    overview.latest_location ?? recentIncidents.find((incident) => incident.location)?.location ?? null;

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
            <strong>Escalated incident reported by the backend.</strong> Open the incident timeline
            to review verification and notification results. No real emergency service is claimed
            to have been contacted.
          </p>
        </div>
      ) : primaryIncident?.status.toUpperCase() === 'VERIFICATION_PENDING' ? (
        <div className="notice notice--info">
          <span className="notice__icon">
            <Icon name="clock" size={18} />
          </span>
          <p>
            <strong>Verification is pending.</strong> The monitored person has been asked to
            confirm they are okay. A missing response is not a confirmation of safety.
          </p>
        </div>
      ) : detectionStatus?.toUpperCase() === 'ANOMALY_DETECTED' && !primaryIncident ? (
        <div className="notice notice--warning">
          <span className="notice__icon">
            <Icon name="incident" size={18} />
          </span>
          <p>
            <strong>Anomaly detected.</strong> The detector reports an unusual pattern, but no
            incident is currently reported by the backend. An anomaly is not a confirmed emergency.
          </p>
        </div>
      ) : detectionStatus?.toUpperCase() === 'NORMAL' && (activeCount === 0 || primaryIncident === null) ? (
        <div className="notice notice--success notice--compact">
          <span className="notice__icon">
            <Icon name="check" size={16} />
          </span>
          <p>
            <strong>Normal operation.</strong> The backend reports no active incident for this
            monitored person.
          </p>
        </div>
      ) : detectionStatus ? null : (
        <div className="notice notice--info notice--compact">
          <span className="notice__icon">
            <Icon name="activity" size={16} />
          </span>
          <p>The backend did not report a current detection status.</p>
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
              <StatusBadge
                label={stale ? 'Stale' : 'Fresh'}
                tone={stale ? 'warning' : 'success'}
              />
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
          aside={<StatusBadge {...detectionMeta} />}
          hint="Backend detector decision"
          icon="incident"
          label="Detection status"
          tone={
            detectionStatus?.toUpperCase() === 'ANOMALY_DETECTED' ? 'amber' : 'teal'
          }
          value={detectionMeta.label}
        />
        <StatCard
          hint={activeCount === null ? 'Not returned by the backend' : 'From the backend incident list'}
          icon="alert"
          label="Active incidents"
          tone={activeCount && activeCount > 0 ? 'red' : 'slate'}
          value={activeCount === null ? 'Unavailable' : String(activeCount)}
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
          subtitle="Latest reading and freshness reported by the backend."
          title="Latest reading"
        >
          <LatestReadingCard
            latestReading={latestReading}
            onViewHistory={() => onNavigate('monitoring')}
            recentReadings={recentReadings}
            staleAfterSeconds={monitoring?.stale_after_seconds}
          />
        </SectionCard>
      </div>

      <div className="overview-layout">
        <div className="overview-layout__main">
          <SectionCard
            subtitle="Verification and escalation state for the most relevant backend incident."
            title="Active response"
          >
            {primaryIncident ? (
              <ActiveResponseSummary
                incident={primaryIncident}
                onSelectIncident={onSelectIncident}
              />
            ) : (
              <EmptyState
                compact
                description="The backend does not currently report an active incident. This does not replace medical advice."
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
            subtitle="Latest authorised snapshot, when available."
            title="Location"
          >
            <LocationCard
              emptyDescription="No location snapshot was returned in the dashboard overview. The dashboard does not discover location independently."
              location={location}
            />
          </SectionCard>

          <SectionCard subtitle="How to read this dashboard." title="Status meaning">
            <dl className="status-key">
              <div>
                <dt>
                  <StatusBadge label="Anomaly detected" tone="warning" />
                </dt>
                <dd>An unusual pattern was detected. It is not a confirmed emergency.</dd>
              </div>
              <div>
                <dt>
                  <StatusBadge label="Verification pending" tone="info" />
                </dt>
                <dd>The person has been asked to confirm they are okay.</dd>
              </div>
              <div>
                <dt>
                  <StatusBadge label="False alarm resolved" tone="success" />
                </dt>
                <dd>The person confirmed they are okay and pending escalation was cancelled.</dd>
              </div>
              <div>
                <dt>
                  <StatusBadge label="Escalated" tone="danger" />
                </dt>
                <dd>Verification timed out and the backend initiated escalation.</dd>
              </div>
            </dl>
          </SectionCard>
        </div>
      </div>
    </>
  );
}
