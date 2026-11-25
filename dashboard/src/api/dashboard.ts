import { getJson, ApiError } from './client';
import { HOSPITAL_RESULT_LIMIT, INCIDENT_PAGE_LIMIT } from './config';
import type {
  DashboardOverview,
  DashboardOverviewEnvelope,
  Hospital,
  IncidentDetail,
  IncidentDetailEnvelope,
  IncidentSummary,
  IncidentsEnvelope,
  LocationSnapshot,
  NearbyHospitalsEnvelope,
  NearbyHospitalsResponse,
} from './types';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function sortIncidentsNewestFirst(incidents: IncidentSummary[]): IncidentSummary[] {
  return [...incidents].sort(
    (left, right) => Date.parse(right.created_at) - Date.parse(left.created_at),
  );
}

export async function fetchOverview(signal: AbortSignal): Promise<DashboardOverview> {
  const body = await getJson<DashboardOverviewEnvelope>('/dashboard/overview', { signal });
  if (!isRecord(body)) {
    throw new ApiError('The dashboard overview response was not readable.', {
      code: 'INVALID_RESPONSE',
    });
  }
  if ('overview' in body && isRecord(body.overview)) {
    return body.overview as DashboardOverview;
  }
  return body as DashboardOverview;
}

export async function fetchIncidents(signal: AbortSignal): Promise<IncidentSummary[]> {
  const body = await getJson<IncidentsEnvelope>(
    `/incidents?limit=${INCIDENT_PAGE_LIMIT}`,
    { signal },
  );

  if (Array.isArray(body)) {
    return sortIncidentsNewestFirst(body).slice(0, INCIDENT_PAGE_LIMIT);
  }
  if (isRecord(body) && Array.isArray(body.incidents)) {
    return sortIncidentsNewestFirst(body.incidents).slice(0, INCIDENT_PAGE_LIMIT);
  }
  throw new ApiError('The incident list response was not readable.', {
    code: 'INVALID_RESPONSE',
  });
}

export async function fetchIncidentDetail(
  incidentId: string,
  signal: AbortSignal,
): Promise<IncidentDetail> {
  const body = await getJson<IncidentDetailEnvelope>(
    `/incidents/${encodeURIComponent(incidentId)}`,
    { signal },
  );

  if (!isRecord(body)) {
    throw new ApiError('The incident detail response was not readable.', {
      code: 'INVALID_RESPONSE',
    });
  }
  const incident = (
    'incident' in body && isRecord(body.incident) ? body.incident : body
  ) as unknown as IncidentDetail;

  if (!incident.incident_id) {
    throw new ApiError('The incident detail response is missing an incident identifier.', {
      code: 'INVALID_RESPONSE',
    });
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
  const body = await getJson<NearbyHospitalsEnvelope>(`/hospitals/nearby?${query.toString()}`, {
    signal,
  });

  if (Array.isArray(body)) {
    return { hospitals: body as Hospital[] };
  }
  if (isRecord(body) && Array.isArray(body.hospitals)) {
    return {
      hospitals: body.hospitals as Hospital[],
      provider: typeof body.provider === 'string' ? body.provider : null,
      disclaimer: typeof body.disclaimer === 'string' ? body.disclaimer : null,
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
    return await getJson<LocationSnapshot>(`/location/latest?${query.toString()}`, { signal });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}
