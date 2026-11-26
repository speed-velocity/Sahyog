export type Tone = 'neutral' | 'success' | 'info' | 'warning' | 'danger' | 'accent';

export interface StatusMeta {
  label: string;
  tone: Tone;
  description?: string;
}

/**
 * Known backend lifecycle values only. Anything else is rendered verbatim with
 * a neutral tone so the dashboard never invents or renames a backend state.
 */
const STATUS_META: Record<string, StatusMeta> = {
  NORMAL: {
    label: 'Normal',
    tone: 'success',
    description: 'No anomaly is currently indicated by the backend.',
  },
  MONITORING: {
    label: 'Monitoring',
    tone: 'success',
    description: 'The monitored person has an active monitoring session.',
  },
  ANOMALY_DETECTED: {
    label: 'Anomaly detected',
    tone: 'warning',
    description: 'An unusual pattern was detected. This is not a confirmed emergency.',
  },
  VERIFICATION_PENDING: {
    label: 'Verification pending',
    tone: 'info',
    description: 'The monitored person has been asked to confirm they are okay.',
  },
  FALSE_ALARM_RESOLVED: {
    label: 'False alarm resolved',
    tone: 'success',
    description: 'The person confirmed they are okay and pending escalation was cancelled.',
  },
  ESCALATED: {
    label: 'Escalated',
    tone: 'danger',
    description: 'Verification received no response and the backend initiated escalation.',
  },
  RESOLVED: {
    label: 'Resolved',
    tone: 'neutral',
    description: 'The incident reached a terminal state.',
  },
  RUNNING: {
    label: 'Running',
    tone: 'info',
    description: 'The demo run is in progress.',
  },
  COMPLETED: {
    label: 'Completed',
    tone: 'neutral',
    description: 'The demo run has completed.',
  },
};

const SEVERITY_META: Record<string, StatusMeta> = {
  LOW: { label: 'Low', tone: 'neutral' },
  MEDIUM: { label: 'Medium', tone: 'warning' },
  HIGH: { label: 'High', tone: 'danger' },
  CRITICAL: { label: 'Critical', tone: 'danger' },
};

const NOTIFICATION_META: Record<string, StatusMeta> = {
  SIMULATED: {
    label: 'Simulated',
    tone: 'accent',
    description: 'Recorded by the demo notifier. No real message or call was delivered.',
  },
  SENT: {
    label: 'Provider accepted',
    tone: 'success',
    description: 'The provider accepted the request. Delivery is not confirmed.',
  },
  FAILED: {
    label: 'Failed',
    tone: 'danger',
    description: 'The notification attempt failed or was not accepted by a provider.',
  },
};

export function getStatusMeta(value: string | null | undefined): StatusMeta {
  if (!value) {
    return { label: 'Unavailable', tone: 'neutral' };
  }
  return (
    STATUS_META[value.toUpperCase()] ?? {
      label: value,
      tone: 'neutral',
      description: 'Value returned by the backend.',
    }
  );
}

export function getSeverityMeta(value: string | null | undefined): StatusMeta {
  if (!value) {
    return { label: 'Not reported', tone: 'neutral' };
  }
  return SEVERITY_META[value.toUpperCase()] ?? { label: value, tone: 'neutral' };
}

export function getNotificationMeta(value: string | null | undefined): StatusMeta {
  if (!value) {
    return { label: 'Not reported', tone: 'neutral' };
  }
  return NOTIFICATION_META[value.toUpperCase()] ?? { label: value, tone: 'neutral' };
}

export function getVerificationResponseLabel(value: string): string {
  return value.toUpperCase() === 'I_AM_OK' ? "I'm okay" : value;
}

export function isEscalatedStatus(value: string | null | undefined): boolean {
  return value?.toUpperCase() === 'ESCALATED';
}
