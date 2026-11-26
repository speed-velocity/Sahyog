import type { AnomalyEvent, IncidentDetail } from '../api/types';
import {
  formatDateTime,
  formatRelativeTime,
  formatTimestampTitle,
  shortId,
} from '../lib/format';
import { getSeverityMeta, getStatusMeta, isEscalatedStatus } from '../lib/status';
import { EmptyState } from './EmptyState';
import { EscalationPanel } from './EscalationPanel';
import { Icon } from './Icon';
import { LocationCard } from './LocationCard';
import { NearbyHospitals } from './NearbyHospitals';
import { StatusBadge } from './StatusBadge';
import { Timeline } from './Timeline';
import { VerificationPanel } from './VerificationPanel';

interface IncidentDetailPanelProps {
  incident: IncidentDetail;
}

function collectAnomalies(incident: IncidentDetail): AnomalyEvent[] {
  const collected = new Map<string, AnomalyEvent>();
  if (incident.anomaly_event) {
    collected.set(incident.anomaly_event.anomaly_event_id, incident.anomaly_event);
  }
  for (const event of incident.evidence ?? []) {
    if (!collected.has(event.anomaly_event_id)) {
      collected.set(event.anomaly_event_id, event);
    }
  }
  return [...collected.values()];
}

export function IncidentDetailPanel({ incident }: IncidentDetailPanelProps) {
  const status = getStatusMeta(incident.status);
  const severity = getSeverityMeta(incident.anomaly_event?.severity);
  const anomalies = collectAnomalies(incident);
  const timeline = incident.timeline ?? incident.timeline_events ?? [];
  const escalated = isEscalatedStatus(incident.status);

  return (
    <article className="incident-detail">
      <header className="incident-detail__header">
        <div>
          <div className="incident-detail__badges">
            <StatusBadge {...status} dot />
            {incident.anomaly_event?.severity ? <StatusBadge {...severity} /> : null}
          </div>
          <h2>Incident {shortId(incident.incident_id)}</h2>
          <p className="incident-detail__id mono" title={incident.incident_id}>
            {incident.incident_id}
          </p>
        </div>
        <dl className="incident-detail__times">
          <div>
            <dt>Created</dt>
            <dd>
              <time dateTime={incident.created_at} title={formatTimestampTitle(incident.created_at)}>
                {formatDateTime(incident.created_at)}
              </time>
              <span className="muted"> · {formatRelativeTime(incident.created_at)}</span>
            </dd>
          </div>
          <div>
            <dt>Updated</dt>
            <dd>
              {incident.updated_at ? (
                <time dateTime={incident.updated_at} title={formatTimestampTitle(incident.updated_at)}>
                  {formatDateTime(incident.updated_at)}
                </time>
              ) : (
                'Not provided'
              )}
            </dd>
          </div>
          <div>
            <dt>Demo run</dt>
            <dd className="mono">{incident.demo_run_id ? shortId(incident.demo_run_id) : 'Not run-scoped'}</dd>
          </div>
          {incident.resolved_at ? (
            <div>
              <dt>Resolved</dt>
              <dd>
                <time dateTime={incident.resolved_at} title={formatTimestampTitle(incident.resolved_at)}>
                  {formatDateTime(incident.resolved_at)}
                </time>
              </dd>
            </div>
          ) : null}
        </dl>
      </header>

      {escalated ? (
        <div className="notice notice--danger notice--compact">
          <span className="notice__icon">
            <Icon name="alert" size={17} />
          </span>
          <p>
            <strong>Escalation recorded by the backend.</strong> This dashboard does not claim that
            a real emergency service, hospital, or contact has been reached or has acknowledged the
            incident.
          </p>
        </div>
      ) : null}

      <section className="detail-section" aria-labelledby="evidence-heading">
        <div className="detail-section__header">
          <div>
            <h3 id="evidence-heading">Anomaly and evidence</h3>
            <p className="muted">Detector output returned by the backend.</p>
          </div>
        </div>

        {anomalies.length > 0 ? (
          <div className="evidence-list">
            {anomalies.map((event) => (
              <div className="evidence-card" key={event.anomaly_event_id}>
                <div className="evidence-card__top">
                  <span className="evidence-card__result">
                    Detector result: <strong>{event.detector_result}</strong>
                  </span>
                  <StatusBadge {...getSeverityMeta(event.severity)} />
                </div>
                <dl className="detail-facts detail-facts--inline">
                  <div>
                    <dt>Detected</dt>
                    <dd>
                      <time dateTime={event.detected_at} title={formatTimestampTitle(event.detected_at)}>
                        {formatDateTime(event.detected_at)}
                      </time>
                    </dd>
                  </div>
                  <div>
                    <dt>Detector version</dt>
                    <dd>{event.detector_version ?? 'Not reported'}</dd>
                  </div>
                  <div>
                    <dt>Event</dt>
                    <dd className="mono">{shortId(event.anomaly_event_id)}</dd>
                  </div>
                </dl>
                <p className="evidence-card__explanation">
                  {event.explanation ?? 'The backend did not return an explanation for this event.'}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            compact
            description="The backend did not return anomaly evidence for this incident."
            icon="incident"
            title="No anomaly evidence returned"
          />
        )}
      </section>

      <VerificationPanel incident={incident} verification={incident.verification} />

      <EscalationPanel incident={incident} />

      <section className="detail-section" aria-labelledby="location-heading">
        <div className="detail-section__header">
          <div>
            <h3 id="location-heading">Incident location and support</h3>
            <p className="muted">Location is shown only when the backend supplies a snapshot.</p>
          </div>
        </div>
        <LocationCard location={incident.location} />
        {incident.location ? <NearbyHospitals location={incident.location} /> : null}
      </section>

      <section className="detail-section" aria-labelledby="timeline-heading">
        <div className="detail-section__header">
          <div>
            <h3 id="timeline-heading">Incident timeline</h3>
            <p className="muted">Sequence of events recorded by the backend.</p>
          </div>
        </div>
        <Timeline events={timeline} />
      </section>
    </article>
  );
}
