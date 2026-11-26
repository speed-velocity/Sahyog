import type { ReactNode } from 'react';
import { Icon, type IconName } from './Icon';

interface StatCardProps {
  label: string;
  value: string;
  hint?: ReactNode;
  icon: IconName;
  tone?: 'teal' | 'amber' | 'red' | 'blue' | 'slate';
  aside?: ReactNode;
}

export function StatCard({ label, value, hint, icon, tone = 'teal', aside }: StatCardProps) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__top">
        <span className="stat-card__icon">
          <Icon name={icon} size={18} />
        </span>
        {aside}
      </div>
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value">{value}</p>
      {hint ? <div className="stat-card__hint">{hint}</div> : null}
    </article>
  );
}
