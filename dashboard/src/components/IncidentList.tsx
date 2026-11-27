import type { IncidentSummary } from '../api/types';
import { formatRelativeTime, formatTimestampTitle, shortId } from '../lib/format';
import { getSeverityMeta, getStatusMeta } from '../lib/status';
import { EmptyState } from './EmptyState';
import { StatusBadge } from './StatusBadge';

interface IncidentListProps {
  incidents: IncidentSummary[];
  selectedId: string | null;
  onSelect: (incidentId: string) => void;
  emptyTitle?: string;
  emptyDescription?: string;
}

export function IncidentList({
  incidents,
  selectedId,
  onSelect,
  emptyTitle = 'No incidents recorded',
  emptyDescription = 'The backend has not reported any incidents for this monitored person.',
}: IncidentListProps) {
  if (incidents.length === 0) {
    return <EmptyState compact description={emptyDescription} icon="check" title={emptyTitle} />;
  }

  return (
    <div className="incident-list" role="list">
      {incidents.map((incident) => {
        const status = getStatusMeta(incident.status);
        const severity = getSeverityMeta(incident.anomaly_event?.severity);
        const isSelected = incident.incident_id === selectedId;

        return (
          <button
            aria-current={isSelected ? 'true' : undefined}
            className={`incident-item${isSelected ? ' incident-item--selected' : ''}`}
            key={incident.incident_id}
            onClick={() => onSelect(incident.incident_id)}
            role="listitem"
            type="button"
          >
            <span className="incident-item__top">
              <StatusBadge {...status} dot />
              {incident.anomaly_event?.severity ? <StatusBadge {...severity} /> : null}
            </span>
            <span className="incident-item__title">
              Incident <span className="mono">{shortId(incident.incident_id)}</span>
            </span>
            <span
              className="incident-item__meta"
              title={formatTimestampTitle(incident.created_at)}
            >
              Created {formatRelativeTime(incident.created_at)}
            </span>
            {incident.verification?.pending === true || incident.status === 'PENDING_VERIFICATION' ? (
              <span className="incident-item__flag">Awaiting verification</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
