import { Icon, type IconName } from './Icon';

export type ViewKey = 'overview' | 'monitoring' | 'incidents' | 'location';

export const VIEW_LABELS: Record<ViewKey, string> = {
  overview: 'Overview',
  monitoring: 'Health monitoring',
  incidents: 'Incidents',
  location: 'Location & support',
};

const NAV_ITEMS: Array<{ key: ViewKey; icon: IconName }> = [
  { key: 'overview', icon: 'overview' },
  { key: 'monitoring', icon: 'heart' },
  { key: 'incidents', icon: 'incident' },
  { key: 'location', icon: 'location' },
];

interface SidebarProps {
  activeView: ViewKey;
  onNavigate: (view: ViewKey) => void;
  activeIncidentCount: number | null;
}

export function Sidebar({ activeView, onNavigate, activeIncidentCount }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="brand-mark" aria-hidden="true">
          <span className="brand-mark__pulse" />
        </span>
        <div>
          <p className="sidebar__name">SAHYOG</p>
          <p className="sidebar__tagline">Detect. Verify. Respond.</p>
        </div>
      </div>

      <nav aria-label="Dashboard sections" className="sidebar__nav">
        <p className="sidebar__section-label">Caregiver console</p>
        {NAV_ITEMS.map((item) => {
          const isActive = activeView === item.key;
          return (
            <button
              aria-current={isActive ? 'page' : undefined}
              className={`sidebar__link${isActive ? ' sidebar__link--active' : ''}`}
              key={item.key}
              onClick={() => onNavigate(item.key)}
              type="button"
            >
              <Icon name={item.icon} size={18} />
              <span>{VIEW_LABELS[item.key]}</span>
              {item.key === 'incidents' && activeIncidentCount !== null && activeIncidentCount > 0 ? (
                <span className="sidebar__count" aria-label={`${activeIncidentCount} active incidents`}>
                  {activeIncidentCount}
                </span>
              ) : null}
            </button>
          );
        })}
      </nav>

      <div className="sidebar__footer">
        <div className="sidebar__footer-card">
          <Icon name="shield" size={18} />
          <div>
            <p className="sidebar__footer-title">Prototype build</p>
            <p className="sidebar__footer-text">
              Simulated monitoring. Not a medical device or emergency-dispatch service.
            </p>
          </div>
        </div>
        <p className="sidebar__owner">Caregiver dashboard · Role R2</p>
      </div>
    </aside>
  );
}
