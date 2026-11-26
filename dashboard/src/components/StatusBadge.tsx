import type { StatusMeta } from '../lib/status';

interface StatusBadgeProps extends StatusMeta {
  dot?: boolean;
}

export function StatusBadge({ label, tone, description, dot = false }: StatusBadgeProps) {
  return (
    <span className={`badge badge--${tone}`} title={description}>
      {dot ? <span aria-hidden="true" className="badge__dot" /> : null}
      {label}
    </span>
  );
}
