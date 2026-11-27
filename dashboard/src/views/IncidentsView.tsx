import type { IncidentSummary } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { Icon } from '../components/Icon';
import { IncidentDetailPanel } from '../components/IncidentDetailPanel';
import { IncidentList } from '../components/IncidentList';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import type { IncidentDetail } from '../api/types';

interface IncidentsViewProps {
  incidents: IncidentSummary[];
  incidentsError: Error | null;
  incidentsLoading: boolean;
  selectedIncidentId: string | null;
  selectedIncident: IncidentDetail | null;
  detailError: Error | null;
  detailLoading: boolean;
  onSelectIncident: (incidentId: string) => void;
  onRetry: () => void;
  onRetryDetail: () => void;
}

export function IncidentsView({
  incidents,
  incidentsError,
  incidentsLoading,
  selectedIncidentId,
  selectedIncident,
  detailError,
  detailLoading,
  onSelectIncident,
  onRetry,
  onRetryDetail,
}: IncidentsViewProps) {
  return (
    <>
      <PageHeader
        actions={
          <button className="btn btn--ghost btn--sm" onClick={onRetry} type="button">
            <Icon name="refresh" size={15} />
            Reload
          </button>
        }
        description="Incident status and timestamps returned by the backend."
        eyebrow="Emergency activity"
        title="Incidents"
      />

      {incidentsError && incidents.length === 0 ? (
        <ErrorState error={incidentsError} onRetry={onRetry} title="Incident list unavailable" />
      ) : incidentsLoading && incidents.length === 0 ? (
        <LoadingSkeleton cards={2} rows={5} />
      ) : incidents.length === 0 ? (
        <SectionCard subtitle="Incidents are created only by the backend." title="Incident list">
          <EmptyState
            description="The backend has not reported any incidents for this monitored person. A normal scenario must not create an incident."
            icon="check"
            title="No incidents recorded"
          />
        </SectionCard>
      ) : (
        <>
          {incidentsError ? (
            <div className="notice notice--warning notice--compact">
              <span className="notice__icon">
                <Icon name="alert" size={16} />
              </span>
              <p>Incident refresh failed. Showing the last successful backend response.</p>
            </div>
          ) : null}

          <div className="incident-layout">
            <SectionCard
              actions={<span className="muted">{incidents.length} recent</span>}
              subtitle="Statuses are displayed exactly as returned by the backend."
              title="Recent incidents"
            >
              <IncidentList
                emptyDescription="No incidents were returned by the backend."
                emptyTitle="No incidents"
                incidents={incidents}
                onSelect={onSelectIncident}
                selectedId={selectedIncidentId}
              />
            </SectionCard>

            {selectedIncidentId === null ? (
              <SectionCard title="Incident detail">
                <EmptyState
                  description="Select an incident to review the status and timestamps returned by the backend."
                  icon="incident"
                  title="No incident selected"
                />
              </SectionCard>
            ) : selectedIncident === null && detailLoading ? (
              <SectionCard title="Incident detail">
                <LoadingSkeleton rows={8} />
              </SectionCard>
            ) : selectedIncident === null && detailError ? (
              <SectionCard title="Incident detail">
                <ErrorState
                  error={detailError}
                  onRetry={onRetryDetail}
                  title="Incident detail unavailable"
                />
              </SectionCard>
            ) : selectedIncident ? (
              <div className="incident-detail-wrapper">
                {detailError ? (
                  <div className="notice notice--warning notice--compact">
                    <span className="notice__icon">
                      <Icon name="alert" size={16} />
                    </span>
                    <p>Detail refresh failed. Showing the last successful backend response.</p>
                  </div>
                ) : null}
                <IncidentDetailPanel incident={selectedIncident} key={selectedIncident.incident_id} />
              </div>
            ) : (
              <SectionCard title="Incident detail">
                <EmptyState
                  description="The selected incident could not be loaded."
                  icon="incident"
                  title="Incident detail unavailable"
                />
              </SectionCard>
            )}
          </div>
        </>
      )}

      <p className="detail-disclaimer">
        <Icon name="shield" size={14} /> The dashboard never creates incidents or decides outcomes.
        Only the backend lifecycle status is displayed.
      </p>
    </>
  );
}
