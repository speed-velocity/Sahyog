import type { ReactNode } from 'react';
import { Icon, type IconName } from './Icon';

interface EmptyStateProps {
  icon?: IconName;
  title: string;
  description: string;
  action?: ReactNode;
  compact?: boolean;
}

export function EmptyState({
  icon = 'activity',
  title,
  description,
  action,
  compact = false,
}: EmptyStateProps) {
  return (
    <div className={`empty-state${compact ? ' empty-state--compact' : ''}`}>
      <span className="empty-state__icon">
        <Icon name={icon} size={22} />
      </span>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
        {action ? <div className="empty-state__action">{action}</div> : null}
      </div>
    </div>
  );
}
