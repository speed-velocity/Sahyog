import { Icon } from './Icon';

interface SimulatedNoticeProps {
  compact?: boolean;
}

export function SimulatedNotice({ compact = false }: SimulatedNoticeProps) {
  return (
    <div className={`notice notice--prototype${compact ? ' notice--compact' : ''}`}>
      <span className="notice__icon">
        <Icon name="shield" size={18} />
      </span>
      <p>
        <strong>Prototype data.</strong> Health readings and emergency notifications in this
        build are simulated unless the backend explicitly reports a live source. SAHYOG is not a
        clinical device or an emergency-dispatch service.
      </p>
    </div>
  );
}
