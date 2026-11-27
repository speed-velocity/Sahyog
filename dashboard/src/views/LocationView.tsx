import type { DashboardOverview, IncidentSummary, LocationSnapshot } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { Icon } from '../components/Icon';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { LocationCard } from '../components/LocationCard';
import { NearbyHospitals } from '../components/NearbyHospitals';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { SimulatedNotice } from '../components/SimulatedNotice';
import { StatusBadge } from '../components/StatusBadge';
import { useLatestLocation } from '../hooks/useDashboardData';
import { formatDateTime, formatRelativeTime, shortId } from '../lib/format';

interface LocationViewProps {
  overview: DashboardOverview | null;
  overviewError: Error | null;
  overviewLoading: boolean;
  incidents: IncidentSummary[];
  incidentsError: Error | null;
  onRetry: () => void;
  onSelectIncident: (incidentId: string) => void;
}

interface ResolvedLocation {
  location: LocationSnapshot | null;
  origin: string;
  incidentId: string | null;
}

function resolveLocation(
  locationApi: LocationSnapshot | null,
  overview: DashboardOverview | null,
  incidents: IncidentSummary[],
): ResolvedLocation {
  if (locationApi) {
    return { location: locationApi, origin: 'Location service snapshot', incidentId: locationApi.incident_id ?? null };
  }
  if (overview?.latest_location) {
    return {
      location: overview.latest_location,
      origin: 'Dashboard overview',
      incidentId: overview.latest_location.incident_id ?? null,
    };
  }
  const incident = incidents.find((item) => item.location);
  if (incident?.location) {
    return {
      location: incident.location,
      origin: `Incident ${shortId(incident.incident_id)}`,
      incidentId: incident.incident_id,
    };
  }
  return { location: null, origin: 'No source', incidentId: null };
}

export function LocationView({
  overview,
  overviewError,
  overviewLoading,
  incidents,
  incidentsError,
  onRetry,
  onSelectIncident,
}: LocationViewProps) {
  const subjectUserId = overview?.subject_user_id ?? null;
  const locationResource = useLatestLocation(subjectUserId);
  const resolved = resolveLocation(locationResource.data ?? null, overview, incidents);
  const location = resolved.location;

  return (
    <>
      <PageHeader
        actions={
          <button className="btn btn--ghost btn--sm" onClick={onRetry} type="button">
            <Icon name="refresh" size={15} />
            Reload
          </button>
        }
        description="Authorised location snapshots and nearby-hospital fallback data. The dashboard never discovers location independently."
        eyebrow="Location & support"
        title="Location and nearby support"
      />

      <SimulatedNotice compact />

      {overviewError ? (
        <div className="notice notice--warning notice--compact">
          <span className="notice__icon">
            <Icon name="alert" size={16} />
          </span>
          <p>Overview refresh failed. Location and hospital data may be incomplete.</p>
        </div>
      ) : null}

      {overviewLoading && !overview ? (
        <LoadingSkeleton cards={2} rows={4} />
      ) : (
        <>
          <SectionCard
            actions={
              <div className="inline-badges">
                {resolved.origin !== 'No source' ? (
                  <StatusBadge label={`Source: ${resolved.origin}`} tone="neutral" />
                ) : null}
                {location ? (
                  <StatusBadge
                    label={`Updated ${formatRelativeTime(location.captured_at)}`}
                    tone="neutral"
                  />
                ) : null}
              </div>
            }
            subtitle="Location is permission-based and appears only after a backend snapshot is submitted by the mobile app."
            title="Latest known location"
          >
            <LocationCard
              emptyDescription="No location snapshot is available yet. The dashboard does not invent a location; check that location permission was granted in the Android app and that a snapshot reached the backend."
              location={location}
            />

            {locationResource.error && location ? (
              <p className="detail-disclaimer">
                <Icon name="alert" size={14} /> The location service refresh failed; the location
                shown is from another backend response.
              </p>
            ) : null}

            {resolved.incidentId ? (
              <div className="location-incident-link">
                <div>
                  <p className="location-incident-link__title">Linked incident</p>
                  <p className="muted mono">{resolved.incidentId}</p>
                </div>
                <button
                  className="btn btn--secondary btn--sm"
                  onClick={() => {
                    if (resolved.incidentId) {
                      onSelectIncident(resolved.incidentId);
                    }
                  }}
                  type="button"
                >
                  Open incident
                  <Icon name="chevronRight" size={15} />
                </button>
              </div>
            ) : null}
          </SectionCard>

          <SectionCard
            subtitle="Results come from the backend hospital directory. External providers are optional for the prototype."
            title="Nearby hospitals"
          >
            <NearbyHospitals location={location} />
          </SectionCard>

          {incidentsError && incidents.length === 0 ? (
            <ErrorState
              compact
              error={incidentsError}
              onRetry={onRetry}
              title="Incident locations unavailable"
            />
          ) : incidents.length > 0 ? (
            <SectionCard
              subtitle="Most recent incident with a backend-supplied location snapshot."
              title="Incident location"
            >
              {(() => {
                const incidentWithLocation = incidents.find((incident) => incident.location);
                if (!incidentWithLocation?.location) {
                  return (
                    <EmptyState
                      compact
                      description="No returned incident includes a location snapshot."
                      icon="location"
                      title="No incident location available"
                    />
                  );
                }
                return (
                  <>
                    <div className="incident-location-meta">
                      <div>
                        <p className="location-incident-link__title">Incident</p>
                        <p className="muted mono">{incidentWithLocation.incident_id}</p>
                      </div>
                      <StatusBadge label={incidentWithLocation.status} tone="neutral" />
                      <span className="muted">
                        Created {formatDateTime(incidentWithLocation.created_at)}
                      </span>
                    </div>
                    <LocationCard location={incidentWithLocation.location} />
                  </>
                );
              })()}
            </SectionCard>
          ) : null}

          <div className="notice notice--info notice--compact">
            <span className="notice__icon">
              <Icon name="shield" size={16} />
            </span>
            <p>
              Hospital entries are informational demo-directory records. No hospital has been
              contacted, is confirmed available, or has accepted an incident. Location is hidden
              when no authorised snapshot exists.
            </p>
          </div>
        </>
      )}
    </>
  );
}
