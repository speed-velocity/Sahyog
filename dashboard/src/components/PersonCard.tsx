import type { SubjectSummary } from '../api/types';
import { formatSource, shortId } from '../lib/format';
import { getStatusMeta } from '../lib/status';
import { EmptyState } from './EmptyState';
import { Icon } from './Icon';
import { StatusBadge } from './StatusBadge';

interface PersonCardProps {
  subject: SubjectSummary | null | undefined;
  monitoringStatus: string | null | undefined;
  dataSource: string | null | undefined;
}

export function PersonCard({ subject, monitoringStatus, dataSource }: PersonCardProps) {
  if (!subject) {
    return (
      <EmptyState
        compact
        description="The backend did not return monitored-person details in the overview response."
        icon="user"
        title="Person details unavailable"
      />
    );
  }

  const name = subject.display_name?.trim() || 'Monitored person';
  const initial = name.charAt(0).toUpperCase();
  const status = getStatusMeta(monitoringStatus);

  return (
    <div className="person-card">
      <div className="person-card__identity">
        <span className="avatar avatar--large">{initial}</span>
        <div>
          <h3 className="person-card__name">{name}</h3>
          <p className="person-card__id">
            Subject <span className="mono">{shortId(subject.user_id)}</span>
          </p>
        </div>
        <StatusBadge {...status} dot />
      </div>

      <dl className="person-card__facts">
        <div>
          <dt>
            <Icon name="user" size={15} /> Age
          </dt>
          <dd>{typeof subject.age === 'number' ? `${subject.age} years` : 'Not provided'}</dd>
        </div>
        <div>
          <dt>
            <Icon name="activity" size={15} /> Monitoring
          </dt>
          <dd>{status.label}</dd>
        </div>
        <div>
          <dt>
            <Icon name="heart" size={15} /> Data source
          </dt>
          <dd>{formatSource(dataSource ?? subject.data_source)}</dd>
        </div>
      </dl>
    </div>
  );
}
