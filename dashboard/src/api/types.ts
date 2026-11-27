/**
 * Proposed dashboard read contract.
 *
 * These shapes follow the canonical endpoints documented in SYSTEM_DESIGN.md
 * (dashboard overview, incident list, incident detail) and the SAHYOG database
 * field names. The backend implementation is owned by Shubhankar and is not
 * present in this branch yet, so every field is optional except identifiers and
 * timestamps that the dashboard can safely render. Unknown status values are
 * displayed verbatim and are never mapped to a different backend state.
 *
 * Location and hospital endpoints are implemented in
 * backend/app/api/location.py and are owned by Vaishnavi.
 */

export type IsoTimestamp = string;

export interface SubjectSummary {
  user_id: string;
  display_name?: string | null;
  age?: number | null;
  data_source?: string | null;
}

export interface HealthReading {
  reading_id: string;
  subject_user_id?: string;
  demo_run_id?: string | null;
  source_kind?: string | null;
  heart_rate_bpm: number;
  observed_at: IsoTimestamp;
  received_at?: IsoTimestamp | null;
  activity_context?: string | null;
  is_stale?: boolean | null;
}

export interface AnomalyEvent {
  anomaly_event_id: string;
  detected_at: IsoTimestamp;
  detector_result: string;
  severity?: string | null;
  explanation?: string | null;
  detector_version?: string | null;
}

export interface VerificationResponse {
  verification_response_id?: string | null;
  response_value: string;
  responded_at: IsoTimestamp;
}

export interface VerificationSummary {
  status?: string | null;
  pending?: boolean | null;
  deadline_at?: IsoTimestamp | null;
  responses?: VerificationResponse[] | null;
}

export interface NotificationAttempt {
  notification_attempt_id?: string | null;
  notification_type?: string | null;
  recipient_reference?: string | null;
  result: string;
  attempted_at?: IsoTimestamp | null;
}

export interface EscalationAttempt {
  escalation_attempt_id: string;
  trigger_reason: string;
  status: string;
  started_at: IsoTimestamp;
  completed_at?: IsoTimestamp | null;
  notifications?: NotificationAttempt[] | null;
}

export interface TimelineEvent {
  timeline_event_id?: string | null;
  event_type: string;
  occurred_at: IsoTimestamp;
  actor_user_id?: string | null;
  details?: string | null;
}

export interface LocationSnapshot {
  subject_user_id?: string | null;
  incident_id?: string | null;
  latitude: number;
  longitude: number;
  accuracy_meters?: number | null;
  captured_at: IsoTimestamp;
  received_at?: IsoTimestamp | null;
  source_kind?: string | null;
  is_stale?: boolean | null;
  stale_after_seconds?: number | null;
}

export interface IncidentSummary {
  incident_id: string;
  subject_user_id?: string;
  demo_run_id?: string | null;
  status: string;
  created_at: IsoTimestamp;
  updated_at?: IsoTimestamp | null;
  verification_deadline_at?: IsoTimestamp | null;
  resolved_at?: IsoTimestamp | null;
  anomaly_event?: AnomalyEvent | null;
  verification?: VerificationSummary | null;
  escalation_attempts?: EscalationAttempt[] | null;
  location?: LocationSnapshot | null;
}

export interface IncidentDetail extends IncidentSummary {
  timeline?: TimelineEvent[] | null;
  timeline_events?: TimelineEvent[] | null;
  evidence?: AnomalyEvent[] | null;
}

export interface MonitoringSummary {
  status?: string | null;
  data_source?: string | null;
  detection_status?: string | null;
  latest_reading?: HealthReading | null;
  recent_readings?: HealthReading[] | null;
  stale_after_seconds?: number | null;
}

export interface DashboardOverview {
  generated_at?: IsoTimestamp | null;
  subject_user_id?: string | null;
  monitoring?: MonitoringSummary | null;
  active_incidents?: IncidentSummary[] | null;
  active_incident_count?: number | null;
  recent_incidents?: IncidentSummary[] | null;
  latest_location?: LocationSnapshot | null;
}

export interface Hospital {
  hospital_id?: string | null;
  name?: string | null;
  display_name?: string | null;
  address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  distance_meters?: number | null;
  source_kind?: string | null;
}

export interface NearbyHospitalsResponse {
  hospitals: Hospital[];
  provider?: string | null;
  disclaimer?: string | null;
  generated_at?: IsoTimestamp | null;
}

export type DashboardOverviewEnvelope = DashboardOverview | { overview: DashboardOverview };

export type IncidentsEnvelope = IncidentSummary[] | { incidents: IncidentSummary[] };

export type IncidentDetailEnvelope = IncidentDetail | { incident: IncidentDetail };

export type NearbyHospitalsEnvelope =
  | NearbyHospitalsResponse
  | Hospital[]
  | { hospitals: Hospital[]; provider?: string | null; disclaimer?: string | null };

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
  detail?: unknown;
}
