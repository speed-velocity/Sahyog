import { formatRelativeTime, isSimulatedSource } from '../lib/format';
import { Icon } from './Icon';
import { VIEW_LABELS, type ViewKey } from './Sidebar';
import { StatusBadge } from './StatusBadge';

export type ConnectionState = 'connecting' | 'connected' | 'error';

interface TopbarProps {
  activeView: ViewKey;
  subjectName: string;
  dataSource: string | null | undefined;
  connection: ConnectionState;
  lastUpdatedAt: number | null;
  isRefreshing: boolean;
  onRefresh: () => void;
}

const CONNECTION_LABEL: Record<ConnectionState, string> = {
  connecting: 'Connecting to backend',
  connected: 'Backend connected',
  error: 'Backend unreachable',
};

export function Topbar({
  activeView,
  subjectName,
  dataSource,
  connection,
  lastUpdatedAt,
  isRefreshing,
  onRefresh,
}: TopbarProps) {
  const initial = subjectName.trim().charAt(0).toUpperCase() || 'S';

  return (
    <div className="topbar">
      <div className="topbar__context">
        <p className="topbar__breadcrumb">Caregiver dashboard</p>
        <p className="topbar__view">{VIEW_LABELS[activeView]}</p>
      </div>

      <div className="topbar__actions">
        <div className="topbar__person">
          <span className="avatar avatar--small">{initial}</span>
          <div>
            <p className="topbar__person-name">{subjectName}</p>
            <p className="topbar__person-meta">
              {isSimulatedSource(dataSource) ? (
                <StatusBadge label="Simulated data" tone="accent" />
              ) : (
                <StatusBadge label={dataSource ?? 'Source not reported'} tone="neutral" />
              )}
            </p>
          </div>
        </div>

        <div className="topbar__status">
          <span
            aria-hidden="true"
            className={`connection-dot connection-dot--${connection}`}
          />
          <div>
            <p className="topbar__status-label">{CONNECTION_LABEL[connection]}</p>
            <p className="topbar__status-meta">
              {lastUpdatedAt
                ? `Updated ${formatRelativeTime(new Date(lastUpdatedAt).toISOString())}`
                : 'No successful refresh yet'}
            </p>
          </div>
        </div>

        <button
          aria-label="Refresh dashboard data"
          className="btn btn--secondary btn--icon-text"
          disabled={isRefreshing}
          onClick={onRefresh}
          type="button"
        >
          <Icon className={isRefreshing ? 'spin' : undefined} name="refresh" size={16} />
          <span>{isRefreshing ? 'Refreshing' : 'Refresh'}</span>
        </button>
      </div>
    </div>
  );
}
