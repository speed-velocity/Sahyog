import type { LocationSnapshot } from '../api/types';
import {
  formatCoordinates,
  formatDateTime,
  formatRelativeTime,
  formatSource,
  formatTimestampTitle,
  isLocationStale,
} from '../lib/format';
import { EmptyState } from './EmptyState';
import { Icon } from './Icon';
import { StatusBadge } from './StatusBadge';

interface LocationCardProps {
  location: LocationSnapshot | null | undefined;
  emptyDescription?: string;
}

export function LocationCard({
  location,
  emptyDescription = 'No authorised location snapshot is available from the backend for this incident.',
}: LocationCardProps) {
  if (!location) {
    return <EmptyState compact description={emptyDescription} icon="location" title="Location unavailable" />;
  }

  const stale = isLocationStale(location);

  return (
    <div className="location-card">
      <div className="location-card__top">
        <div className="location-card__coordinates">
          <span className="location-card__pin">
            <Icon name="location" size={20} />
          </span>
          <div>
            <p className="location-card__value">
              {formatCoordinates(location.latitude, location.longitude)}
            </p>
            <p className="muted">
              Captured{' '}
              <time dateTime={location.captured_at} title={formatTimestampTitle(location.captured_at)}>
                {formatDateTime(location.captured_at)}
              </time>{' '}
              · {formatRelativeTime(location.captured_at)}
            </p>
          </div>
        </div>
        <div className="location-card__badges">
          <StatusBadge
            label={formatSource(location.source_kind)}
            tone={location.source_kind?.toUpperCase() === 'SIMULATED' ? 'accent' : 'neutral'}
          />
          <StatusBadge label={stale ? 'Stale location' : 'Fresh location'} tone={stale ? 'warning' : 'success'} />
        </div>
      </div>

      <dl className="detail-facts detail-facts--inline">
        <div>
          <dt>Latitude</dt>
          <dd>{location.latitude.toFixed(5)}</dd>
        </div>
        <div>
          <dt>Longitude</dt>
          <dd>{location.longitude.toFixed(5)}</dd>
        </div>
        <div>
          <dt>Accuracy</dt>
          <dd>
            {typeof location.accuracy_meters === 'number'
              ? `${Math.round(location.accuracy_meters)} m`
              : 'Not provided'}
          </dd>
        </div>
      </dl>

      {stale ? (
        <p className="detail-disclaimer">
          <Icon name="clock" size={14} /> This location is older than the freshness window. It may
          not reflect the person&apos;s current position.
        </p>
      ) : (
        <p className="detail-disclaimer">
          <Icon name="shield" size={14} /> Location is displayed only from an authorised backend
          snapshot. The dashboard does not discover location independently.
        </p>
      )}
    </div>
  );
}
