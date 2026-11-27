import { getJson, ApiError } from './client';
import { HOSPITAL_RESULT_LIMIT, INCIDENT_PAGE_LIMIT } from './config';
import type {
  AuthorizedSubject,
  DashboardOverview,
  DashboardOverviewResponse,
  Hospital,
  IncidentDetail,
  IncidentSummary,
  IncidentResponse,
  LocationSnapshot,
  NearbyHospitalsResponse,
  AuthorizedSubjectsResponse,
} from './types';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function requiredString(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.length === 0) {
    throw new ApiError(`The backend response is missing ${field}.`, { code: 'INVALID_RESPONSE' });
  }
  return value;
}

function nullableString(value: unknown, field: string): string | null {
  if (value === null || typeof value === 'string') return value;
  throw new ApiError(`The backend response contains an invalid ${field}.`, { code: 'INVALID_RESPONSE' });
}

function nullableTimestamp(value: unknown, field: string): string | null {
  if (value === null) return null;
  if (typeof value === 'string' && Number.isFinite(Date.parse(value))) return value;
  throw new ApiError(`The backend response contains an invalid ${field}.`, { code: 'INVALID_RESPONSE' });
}

function parseIncident(value: unknown): IncidentResponse {
  if (!isRecord(value)) {
    throw new ApiError('The incident response was not readable.', { code: 'INVALID_RESPONSE' });
  }
  const runGeneration = value.run_generation;
  if (runGeneration !== null && (typeof runGeneration !== 'number' || !Number.isInteger(runGeneration))) {
    throw new ApiError('The incident response contains an invalid run_generation.', { code: 'INVALID_RESPONSE' });
  }
  const createdAt = requiredString(value.created_at, 'created_at');
  const updatedAt = requiredString(value.updated_at, 'updated_at');
  if (!Number.isFinite(Date.parse(createdAt)) || !Number.isFinite(Date.parse(updatedAt))) {
    throw new ApiError('The incident response contains an invalid timestamp.', { code: 'INVALID_RESPONSE' });
  }
  return {
    incident_id: requiredString(value.incident_id, 'incident_id'),
    subject_user_id: requiredString(value.subject_user_id, 'subject_user_id'),
    demo_run_id: nullableString(value.demo_run_id, 'demo_run_id'),
    run_generation: runGeneration,
    status: requiredString(value.status, 'status'),
    created_at: createdAt,
    updated_at: updatedAt,
    verification_deadline_at: nullableTimestamp(value.verification_deadline_at, 'verification_deadline_at'),
    resolved_at: nullableTimestamp(value.resolved_at, 'resolved_at'),
  };
}

function parseAuthorizedSubject(value: unknown): AuthorizedSubject {
  if (!isRecord(value)) {
    throw new ApiError('The authorization response contains an invalid subject.', { code: 'INVALID_RESPONSE' });
  }
  const grantedAt = requiredString(value.granted_at, 'granted_at');
  if (!Number.isFinite(Date.parse(grantedAt))) {
    throw new ApiError('The authorization response contains an invalid granted_at.', { code: 'INVALID_RESPONSE' });
  }
  return {
    subject_user_id: requiredString(value.subject_user_id, 'subject_user_id'),
    granted_at: grantedAt,
    revoked_at: nullableTimestamp(value.revoked_at, 'revoked_at'),
  };
}

function parseLocation(value: unknown): LocationSnapshot {
  if (!isRecord(value)) {
    throw new ApiError('The location response was not readable.', { code: 'INVALID_RESPONSE' });
  }
  const numeric = ['latitude', 'longitude', 'stale_after_seconds'] as const;
  if (numeric.some((field) => typeof value[field] !== 'number' || !Number.isFinite(value[field]))) {
    throw new ApiError('The location response contains invalid coordinates or staleness.', { code: 'INVALID_RESPONSE' });
  }
  if (value.accuracy_meters !== null && (typeof value.accuracy_meters !== 'number' || !Number.isFinite(value.accuracy_meters))) {
    throw new ApiError('The location response contains invalid accuracy_meters.', { code: 'INVALID_RESPONSE' });
  }
  if (typeof value.is_stale !== 'boolean') {
    throw new ApiError('The location response contains invalid is_stale.', { code: 'INVALID_RESPONSE' });
  }
  const capturedAt = requiredString(value.captured_at, 'captured_at');
  const receivedAt = requiredString(value.received_at, 'received_at');
  if (!Number.isFinite(Date.parse(capturedAt)) || !Number.isFinite(Date.parse(receivedAt))) {
    throw new ApiError('The location response contains an invalid timestamp.', { code: 'INVALID_RESPONSE' });
  }
  return {
    location_snapshot_id: requiredString(value.location_snapshot_id, 'location_snapshot_id'),
    subject_user_id: requiredString(value.subject_user_id, 'subject_user_id'),
    incident_id: nullableString(value.incident_id, 'incident_id'),
    demo_run_id: nullableString(value.demo_run_id, 'demo_run_id'),
    latitude: value.latitude as number,
    longitude: value.longitude as number,
    accuracy_meters: value.accuracy_meters as number | null,
    captured_at: capturedAt,
    received_at: receivedAt,
    source_kind: requiredString(value.source_kind, 'source_kind'),
    is_stale: value.is_stale,
    stale_after_seconds: value.stale_after_seconds as number,
  };
}

function sortIncidentsNewestFirst(incidents: IncidentSummary[]): IncidentSummary[] {
  return [...incidents].sort(
    (left, right) => Date.parse(right.created_at) - Date.parse(left.created_at),
  );
}

export async function fetchOverview(
  signal: AbortSignal,
  subjectUserId: string,
): Promise<DashboardOverview> {
  const query = new URLSearchParams({ subject_user_id: subjectUserId });
  const body = await getJson<unknown>(`/dashboard/overview?${query.toString()}`, { signal });
  if (!isRecord(body)) {
    throw new ApiError('The dashboard overview response was not readable.', { code: 'INVALID_RESPONSE' });
  }
  const latest = body.latest_reading;
  let latestReading: DashboardOverviewResponse['latest_reading'] = null;
  if (latest !== null) {
    if (!isRecord(latest) || typeof latest.heart_rate_bpm !== 'number' || !Number.isInteger(latest.heart_rate_bpm)) {
      throw new ApiError('The latest reading response was not readable.', { code: 'INVALID_RESPONSE' });
    }
    const observedAt = requiredString(latest.observed_at, 'latest_reading.observed_at');
    if (!Number.isFinite(Date.parse(observedAt))) {
      throw new ApiError('The latest reading timestamp was invalid.', { code: 'INVALID_RESPONSE' });
    }
    latestReading = {
      reading_id: requiredString(latest.reading_id, 'latest_reading.reading_id'),
      heart_rate_bpm: latest.heart_rate_bpm,
      observed_at: observedAt,
      source_kind: requiredString(latest.source_kind, 'latest_reading.source_kind'),
    };
  }
  const response: DashboardOverviewResponse = {
    subject_user_id: requiredString(body.subject_user_id, 'subject_user_id'),
    monitoring_status: requiredString(body.monitoring_status, 'monitoring_status'),
    latest_reading: latestReading,
    active_incident: nullableString(body.active_incident, 'active_incident'),
    incident_status: nullableString(body.incident_status, 'incident_status'),
    latest_update_at: nullableTimestamp(body.latest_update_at, 'latest_update_at'),
  };
  if (response.subject_user_id !== subjectUserId) {
    throw new ApiError('The dashboard overview belongs to a different subject.', { code: 'SUBJECT_MISMATCH' });
  }
  return {
    subject_user_id: response.subject_user_id,
    monitoring: {
      status: response.monitoring_status,
      data_source: response.latest_reading?.source_kind ?? null,
      latest_reading: response.latest_reading,
      recent_readings: response.latest_reading ? [response.latest_reading] : [],
      stale_after_seconds: null,
    },
    active_incident_id: response.active_incident,
    incident_status: response.incident_status,
    latest_update_at: response.latest_update_at,
  };
}

export async function fetchIncidents(
  signal: AbortSignal,
  subjectUserId: string,
): Promise<IncidentSummary[]> {
  const query = new URLSearchParams({
    subject_user_id: subjectUserId,
    limit: String(INCIDENT_PAGE_LIMIT),
  });
  const body = await getJson<unknown>(`/incidents?${query.toString()}`, { signal });
  if (!Array.isArray(body)) {
    throw new ApiError('The incident list response was not readable.', { code: 'INVALID_RESPONSE' });
  }
  const incidents = body.map(parseIncident);
  if (incidents.some((incident) => incident.subject_user_id !== subjectUserId)) {
    throw new ApiError('The incident list contains another subject.', { code: 'SUBJECT_MISMATCH' });
  }
  return sortIncidentsNewestFirst(incidents).slice(0, INCIDENT_PAGE_LIMIT);
}

export async function fetchIncidentDetail(
  incidentId: string,
  signal: AbortSignal,
): Promise<IncidentDetail> {
  const body = await getJson<unknown>(
    `/incidents/${encodeURIComponent(incidentId)}`,
    { signal },
  );

  const incident = parseIncident(body) as IncidentDetail;
  if (incident.incident_id !== incidentId) {
    throw new ApiError('The incident detail response does not match the requested incident.', { code: 'INVALID_RESPONSE' });
  }
  return incident;
}

export async function fetchNearbyHospitals(
  latitude: number,
  longitude: number,
  signal: AbortSignal,
): Promise<NearbyHospitalsResponse> {
  const query = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    limit: String(HOSPITAL_RESULT_LIMIT),
  });
  const body = await getJson<unknown>(`/hospitals/nearby?${query.toString()}`, {
    signal,
  });
  if (isRecord(body) && Array.isArray(body.hospitals)) {
    const hospitals: Hospital[] = body.hospitals.map((item: unknown) => {
      if (!isRecord(item) || typeof item.latitude !== 'number' || typeof item.longitude !== 'number' || typeof item.distance_meters !== 'number') {
        throw new ApiError('The hospital response contains an invalid entry.', { code: 'INVALID_RESPONSE' });
      }
      return {
        hospital_id: requiredString(item.hospital_id, 'hospital_id'),
        name: requiredString(item.name, 'name'),
        address: requiredString(item.address, 'address'),
        latitude: item.latitude,
        longitude: item.longitude,
        distance_meters: item.distance_meters,
        source_kind: requiredString(item.source_kind, 'source_kind'),
      };
    });
    return {
      hospitals,
      provider: nullableString(body.provider, 'provider'),
      disclaimer: requiredString(body.disclaimer, 'disclaimer'),
      generated_at: requiredString(body.generated_at, 'generated_at'),
    };
  }
  throw new ApiError('The hospital response was not readable.', {
    code: 'INVALID_RESPONSE',
  });
}

export async function fetchLatestLocation(
  subjectUserId: string,
  signal: AbortSignal,
): Promise<LocationSnapshot | null> {
  const query = new URLSearchParams({ subject_user_id: subjectUserId });
  try {
    const location = parseLocation(await getJson<unknown>(`/location/latest?${query.toString()}`, { signal }));
    if (location.subject_user_id !== subjectUserId) {
      throw new ApiError('The location response belongs to a different subject.', { code: 'SUBJECT_MISMATCH' });
    }
    return location;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function fetchAuthorizedSubjects(
  signal: AbortSignal,
): Promise<AuthorizedSubjectsResponse> {
  const body = await getJson<unknown>('/authorizations/me', { signal });
  if (!isRecord(body) || !Array.isArray(body.authorized_subjects)) {
    throw new ApiError('The authorization response was not readable.', { code: 'INVALID_RESPONSE' });
  }
  const response: AuthorizedSubjectsResponse = {
    authorized_subjects: body.authorized_subjects.map(parseAuthorizedSubject),
  };
  return {
    authorized_subjects: response.authorized_subjects.filter((subject) => subject.revoked_at === null),
  };
}
