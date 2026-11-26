import type { TimelineEvent } from '../api/types';
import {
  formatDateTime,
  formatRelativeTime,
  formatTimestampTitle,
  humanizeToken,
  shortId,
} from '../lib/format';
import { EmptyState } from './EmptyState';

interface TimelineProps {
  events: TimelineEvent[];
}

export function Timeline({ events }: TimelineProps) {
  const sorted = [...events].sort(
    (left, right) => Date.parse(left.occurred_at) - Date.parse(right.occurred_at),
  );

  if (sorted.length === 0) {
    return (
      <EmptyState
        compact
        description="The backend did not return timeline events for this incident."
        icon="clock"
        title="Timeline unavailable"
      />
    );
  }

  return (
    <ol className="timeline">
      {sorted.map((event, index) => (
        <li className="timeline__item" key={event.timeline_event_id ?? `${event.event_type}-${index}`}>
          <span aria-hidden="true" className="timeline__dot" />
          <div className="timeline__content">
            <div className="timeline__header">
              <span className="timeline__type" title={event.event_type}>
                {humanizeToken(event.event_type)}
              </span>
              <time
                className="timeline__time"
                dateTime={event.occurred_at}
                title={formatTimestampTitle(event.occurred_at)}
              >
                {formatDateTime(event.occurred_at)} · {formatRelativeTime(event.occurred_at)}
              </time>
            </div>
            {event.details ? <p className="timeline__details">{event.details}</p> : null}
            {event.actor_user_id ? (
              <p className="timeline__actor">Actor: {shortId(event.actor_user_id)}</p>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
