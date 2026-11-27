import type {
  DashboardOverviewResponse,
  IncidentResponse,
  LocationSnapshot,
  NearbyHospitalsResponse,
} from '../api/types';

export const SUBJECT_ID = 'a1b2c3d4-1111-4111-8111-111111111111';
export const SECOND_SUBJECT_ID = 'd4e5f6a7-4444-4444-8444-444444444444';
export const INCIDENT_ID = 'b2c3d4e5-2222-4222-8222-222222222222';
export const DEMO_RUN_ID = 'c3d4e5f6-3333-4333-8333-333333333333';

export function timestamp(offsetSeconds = 0): string {
  return new Date(Date.now() + offsetSeconds * 1000).toISOString();
}

export function overviewResponse(
  subjectId = SUBJECT_ID,
  options: { activeIncident?: string | null; status?: string; bpm?: number | null } = {},
): DashboardOverviewResponse {
  const activeIncident = options.activeIncident ?? null;
  const status = options.status ?? (activeIncident ? 'INCIDENT_ACTIVE' : 'NORMAL');
  const bpm = options.bpm === undefined ? 78 : options.bpm;
  return {
    subject_user_id: subjectId,
    monitoring_status: status,
    latest_reading:
      bpm === null
        ? null
        : {
            reading_id: 'e4f5a6b7-5555-4555-8555-555555555555',
            heart_rate_bpm: bpm,
            observed_at: timestamp(-30),
            source_kind: 'SIMULATED',
          },
    active_incident: activeIncident,
    incident_status: activeIncident ? 'ESCALATED' : null,
    latest_update_at: timestamp(-20),
  };
}

export function incidentResponse(
  status: string,
  subjectId = SUBJECT_ID,
  incidentId = INCIDENT_ID,
): IncidentResponse {
  return {
    incident_id: incidentId,
    subject_user_id: subjectId,
    demo_run_id: DEMO_RUN_ID,
    run_generation: 1,
    status,
    created_at: timestamp(-300),
    updated_at: timestamp(-30),
    verification_deadline_at: null,
    resolved_at: status.startsWith('RESOLVED') ? timestamp(-20) : null,
  };
}

export function locationSnapshot(subjectId = SUBJECT_ID): LocationSnapshot {
  return {
    location_snapshot_id: 'f5a6b7c8-6666-4666-8666-666666666666',
    subject_user_id: subjectId,
    incident_id: null,
    demo_run_id: null,
    latitude: 18.5204,
    longitude: 73.8567,
    accuracy_meters: 8,
    captured_at: timestamp(-10),
    received_at: timestamp(-9),
    source_kind: 'SIMULATED',
    is_stale: false,
    stale_after_seconds: 300,
  };
}

export function hospitalsResponse(): NearbyHospitalsResponse {
  return {
    hospitals: [
      {
        hospital_id: 'a6b7c8d9-7777-4777-8777-777777777777',
        name: 'SAHYOG Demo General Hospital',
        address: 'Demo address, Pune',
        latitude: 18.521,
        longitude: 73.857,
        distance_meters: 1200,
        source_kind: 'SEEDED_DEMO',
      },
    ],
    provider: 'SEEDED_DEMO',
    disclaimer: 'Demo directory only; availability is not confirmed.',
    generated_at: timestamp(),
  };
}
