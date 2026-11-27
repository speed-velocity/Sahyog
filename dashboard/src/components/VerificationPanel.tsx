import type { IncidentSummary, VerificationSummary } from '../api/types';
import { formatDateTime, formatRelativeTime, formatTimestampTitle } from '../lib/format';
import { getStatusMeta, getVerificationResponseLabel } from '../lib/status';
import { Icon } from './Icon';
import { StatusBadge } from './StatusBadge';

interface VerificationPanelProps {
  incident: IncidentSummary;
  verification: VerificationSummary | null | undefined;
}

export function VerificationPanel({ incident, verification }: VerificationPanelProps) {
  if (verification == null) {
    return (
      <section className="detail-section" aria-labelledby="verification-heading">
        <div className="detail-section__header">
          <div>
            <h3 id="verification-heading">Verification</h3>
            <p className="muted">The current incident endpoint does not include verification records.</p>
          </div>
        </div>
        <p className="muted">Verification state and recorded responses are unavailable from this API response.</p>
      </section>
    );
  }

  const responses = verification?.responses ?? [];
  const pending =
    verification?.pending === true || incident.status.toUpperCase() === 'PENDING_VERIFICATION';
  const deadline = verification?.deadline_at ?? incident.verification_deadline_at;
  const statusValue = verification?.status ?? (pending ? 'PENDING_VERIFICATION' : null);
  const confirmed = responses.some(
    (response) => response.response_value.toUpperCase() === 'I_AM_OK',
  );

  return (
    <section className="detail-section" aria-labelledby="verification-heading">
      <div className="detail-section__header">
        <div>
          <h3 id="verification-heading">Verification</h3>
          <p className="muted">The backend decides whether verification is pending or complete.</p>
        </div>
        {statusValue ? (
          <StatusBadge {...getStatusMeta(statusValue)} />
        ) : (
          <StatusBadge label="Not provided" tone="neutral" />
        )}
      </div>

      <dl className="detail-facts">
        <div>
          <dt>Verification state</dt>
          <dd>{pending ? 'Pending response' : statusValue ? getStatusMeta(statusValue).label : 'No active verification'}</dd>
        </div>
        <div>
          <dt>Response deadline</dt>
          <dd>
            {deadline ? (
              <>
                {formatDateTime(deadline)}
                <span className="muted"> · {formatRelativeTime(deadline)}</span>
              </>
            ) : (
              'Not provided'
            )}
          </dd>
        </div>
        <div>
          <dt>Recorded responses</dt>
          <dd>{responses.length}</dd>
        </div>
      </dl>

      {pending && responses.length === 0 ? (
        <div className="notice notice--info notice--compact">
          <span className="notice__icon">
            <Icon name="clock" size={16} />
          </span>
          <p>
            <strong>No response recorded.</strong> A missing response is not a confirmation that
            the person is safe. The backend will apply its configured verification timeout.
          </p>
        </div>
      ) : null}

      {confirmed ? (
        <div className="notice notice--success notice--compact">
          <span className="notice__icon">
            <Icon name="check" size={16} />
          </span>
          <p>
            <strong>Explicit confirmation recorded.</strong> The monitored person confirmed they
            are okay.
          </p>
        </div>
      ) : null}

      {responses.length > 0 ? (
        <ul className="response-list">
          {responses.map((response, index) => (
            <li key={`${response.verification_response_id ?? 'response'}-${index}`}>
              <span className="response-list__value">
                {getVerificationResponseLabel(response.response_value)}
              </span>
              <span className="response-list__time" title={formatTimestampTitle(response.responded_at)}>
                {formatDateTime(response.responded_at)}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No verification responses have been recorded by the backend.</p>
      )}

      {!pending && responses.length === 0 && statusValue === null ? (
        <p className="muted">
          The backend did not return verification details for this incident.
        </p>
      ) : null}
    </section>
  );
}
