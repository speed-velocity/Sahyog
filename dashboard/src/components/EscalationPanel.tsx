import type { EscalationAttempt, IncidentSummary } from '../api/types';
import {
  formatDateTime,
  formatRelativeTime,
  formatTimestampTitle,
  humanizeToken,
  shortId,
} from '../lib/format';
import { getNotificationMeta, getStatusMeta } from '../lib/status';
import { Icon } from './Icon';
import { StatusBadge } from './StatusBadge';

interface EscalationPanelProps {
  incident: IncidentSummary;
}

function EscalationAttemptCard({ attempt }: { attempt: EscalationAttempt }) {
  const notifications = attempt.notifications ?? [];

  return (
    <article className="escalation-attempt">
      <header className="escalation-attempt__header">
        <div>
          <p className="escalation-attempt__title">
            Escalation attempt <span className="mono">{shortId(attempt.escalation_attempt_id)}</span>
          </p>
          <p className="muted">
            Started{' '}
            <time dateTime={attempt.started_at} title={formatTimestampTitle(attempt.started_at)}>
              {formatDateTime(attempt.started_at)}
            </time>
            {attempt.completed_at ? (
              <>
                {' '}
                · Completed{' '}
                <time
                  dateTime={attempt.completed_at}
                  title={formatTimestampTitle(attempt.completed_at)}
                >
                  {formatDateTime(attempt.completed_at)}
                </time>
              </>
            ) : null}
          </p>
        </div>
        <StatusBadge {...getStatusMeta(attempt.status)} />
      </header>

      <p className="escalation-attempt__reason">
        <span className="muted">Trigger:</span> {humanizeToken(attempt.trigger_reason)}
      </p>

      {notifications.length > 0 ? (
        <ul className="notification-list">
          {notifications.map((notification, index) => {
            const result = getNotificationMeta(notification.result);
            const simulated = notification.result.toUpperCase() === 'SIMULATED';
            return (
              <li className="notification-item" key={notification.notification_attempt_id ?? index}>
                <div className="notification-item__main">
                  <span className="notification-item__type">
                    {humanizeToken(notification.notification_type)}
                  </span>
                  <StatusBadge {...result} />
                </div>
                <p className="notification-item__recipient">
                  {notification.recipient_reference
                    ? `Recipient: ${notification.recipient_reference}`
                    : 'Recipient reference not disclosed'}
                </p>
                {notification.attempted_at ? (
                  <p className="muted">
                    Attempted{' '}
                    <time
                      dateTime={notification.attempted_at}
                      title={formatTimestampTitle(notification.attempted_at)}
                    >
                      {formatDateTime(notification.attempted_at)}
                    </time>{' '}
                    · {formatRelativeTime(notification.attempted_at)}
                  </p>
                ) : null}
                {simulated ? (
                  <p className="notification-item__simulated">
                    Simulated notification — no real message or call was delivered.
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="muted">
          No notification attempts were returned for this escalation attempt.
        </p>
      )}
    </article>
  );
}

export function EscalationPanel({ incident }: EscalationPanelProps) {
  const attempts = incident.escalation_attempts;
  const escalated = incident.status.toUpperCase() === 'ESCALATED';

  return (
    <section className="detail-section" aria-labelledby="escalation-heading">
      <div className="detail-section__header">
        <div>
          <h3 id="escalation-heading">Escalation</h3>
          <p className="muted">Exact notification results as recorded by the backend.</p>
        </div>
        {escalated ? <StatusBadge label="Escalated" tone="danger" /> : null}
      </div>

      {escalated && attempts?.length === 0 ? (
        <div className="notice notice--warning notice--compact">
          <span className="notice__icon">
            <Icon name="phone" size={16} />
          </span>
          <p>
            The backend reports this incident as <strong>ESCALATED</strong>, but no escalation
            attempts were returned. The dashboard does not infer delivery details.
          </p>
        </div>
      ) : null}

      {attempts && attempts.length > 0 ? (
        <div className="escalation-list">
          {attempts.map((attempt) => (
            <EscalationAttemptCard attempt={attempt} key={attempt.escalation_attempt_id} />
          ))}
        </div>
      ) : attempts === undefined ? (
        <p className="muted">Escalation attempt details are not included in the current incident response.</p>
      ) : !escalated ? (
        <p className="muted">No escalation attempts have been recorded for this incident.</p>
      ) : null}

      <p className="detail-disclaimer">
        <Icon name="shield" size={14} /> A notification marked <strong>Simulated</strong> was not
        sent to a real recipient. <strong>Provider accepted</strong> does not confirm that a person
        received or acknowledged the message.
      </p>
    </section>
  );
}
