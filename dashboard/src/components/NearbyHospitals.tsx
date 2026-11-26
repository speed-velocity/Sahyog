import type { LocationSnapshot } from '../api/types';
import { useNearbyHospitals } from '../hooks/useDashboardData';
import {
  formatCoordinates,
  formatDistance,
  formatSource,
  isLocationStale,
} from '../lib/format';
import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';
import { Icon } from './Icon';
import { LoadingSkeleton } from './LoadingSkeleton';
import { StatusBadge } from './StatusBadge';

interface NearbyHospitalsProps {
  location: LocationSnapshot | null | undefined;
}

function providerLabel(raw: string | null | undefined): string {
  if (!raw) {
    return 'Source not reported';
  }
  const normalized = raw.toUpperCase();
  if (normalized.includes('SEED')) {
    return 'Seeded demo directory';
  }
  return formatSource(raw);
}

export function NearbyHospitals({ location }: NearbyHospitalsProps) {
  const resource = useNearbyHospitals(location);

  if (!location) {
    return (
      <EmptyState
        compact
        description="Nearby hospitals can be listed once the backend provides a location snapshot."
        icon="hospital"
        title="Hospital lookup unavailable"
      />
    );
  }

  const stale = isLocationStale(location);
  const hospitals = resource.data?.hospitals ?? [];
  const provider = providerLabel(
    resource.data?.provider ?? hospitals.find((hospital) => hospital.source_kind)?.source_kind,
  );

  return (
    <div className="hospital-panel">
      <div className="hospital-panel__header">
        <div>
          <h3>Nearby hospitals</h3>
          <p className="muted">
            Directory results for {formatCoordinates(location.latitude, location.longitude)}
            {stale ? ' · based on a stale location' : ''}
          </p>
        </div>
        <div className="hospital-panel__actions">
          <StatusBadge label={provider} tone={provider.includes('Seeded') ? 'accent' : 'neutral'} />
          <button
            className="btn btn--ghost btn--sm"
            disabled={resource.isRefreshing}
            onClick={resource.refresh}
            type="button"
          >
            <Icon name="refresh" size={14} />
            Refresh
          </button>
        </div>
      </div>

      {resource.isLoading && resource.data === null ? (
        <LoadingSkeleton label="Loading nearby hospitals" rows={3} />
      ) : null}

      {resource.error && resource.data === null ? (
        <ErrorState
          compact
          error={resource.error}
          onRetry={resource.refresh}
          title="Hospital directory unavailable"
        />
      ) : null}

      {resource.error && resource.data !== null ? (
        <div className="notice notice--warning notice--compact">
          <span className="notice__icon">
            <Icon name="alert" size={16} />
          </span>
          <p>Hospital refresh failed. Showing the last result returned by the backend.</p>
        </div>
      ) : null}

      {resource.data !== null && hospitals.length === 0 ? (
        <EmptyState
          compact
          description="The hospital directory returned no results for this location."
          icon="hospital"
          title="No hospitals found"
        />
      ) : null}

      {hospitals.length > 0 ? (
        <ul className="hospital-list">
          {hospitals.map((hospital, index) => {
            const name = hospital.name ?? hospital.display_name ?? 'Hospital name not provided';
            const seeded = hospital.source_kind?.toUpperCase().includes('SEED') ?? false;
            return (
              <li className="hospital-item" key={hospital.hospital_id ?? `${name}-${index}`}>
                <span className="hospital-item__icon">
                  <Icon name="hospital" size={19} />
                </span>
                <div className="hospital-item__body">
                  <div className="hospital-item__top">
                    <h4>{name}</h4>
                    <span className="hospital-item__distance">
                      {formatDistance(hospital.distance_meters)}
                    </span>
                  </div>
                  <p className="hospital-item__address">
                    {hospital.address ?? 'Address not provided'}
                  </p>
                  <div className="hospital-item__meta">
                    {hospital.source_kind ? (
                      <StatusBadge
                        label={formatSource(hospital.source_kind)}
                        tone={seeded ? 'accent' : 'neutral'}
                      />
                    ) : null}
                    {typeof hospital.latitude === 'number' && typeof hospital.longitude === 'number' ? (
                      <span className="muted">
                        {formatCoordinates(hospital.latitude, hospital.longitude)}
                      </span>
                    ) : null}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      ) : null}

      <p className="detail-disclaimer">
        <Icon name="shield" size={14} />{' '}
        {resource.data?.disclaimer ??
          'Demo directory data only. No hospital has been contacted, is confirmed available, or has accepted this incident.'}
      </p>
    </div>
  );
}
