import { ApiError } from '../api/client';
import { API_BASE_URL } from '../api/config';
import { Icon } from './Icon';

interface ErrorStateProps {
  title?: string;
  error: Error;
  onRetry: () => void;
  compact?: boolean;
}

function isAuthError(error: Error): boolean {
  return (
    error instanceof ApiError &&
    (error.status === 401 || error.status === 403)
  );
}

export function ErrorState({
  title,
  error,
  onRetry,
  compact = false,
}: ErrorStateProps) {
  const authError = isAuthError(error);
  const resolvedTitle = title ?? (authError ? 'Dashboard access expired' : 'Unable to load backend data');

  return (
    <div className={`error-state${compact ? ' error-state--compact' : ''}`} role="alert">
      <span className="error-state__icon">
        <Icon name={authError ? 'shield' : 'alert'} size={22} />
      </span>
      <div className="error-state__content">
        <h3>{resolvedTitle}</h3>
        <p>{error.message}</p>
        {authError ? (
          <p className="error-state__meta">
            The backend rejected this dashboard request. Sign in again or ask the backend owner to
            grant this caregiver account access. No data was fabricated while access is unavailable.
          </p>
        ) : null}
        <p className="error-state__meta">
          Backend: <code>{API_BASE_URL}</code>
        </p>
        <button className="btn btn--secondary btn--sm" onClick={onRetry} type="button">
          <Icon name="refresh" size={15} />
          Retry
        </button>
      </div>
    </div>
  );
}
