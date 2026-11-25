import { useCallback } from 'react';
import { POLL_INTERVAL_MS } from '../api/config';
import {
  fetchIncidentDetail,
  fetchIncidents,
  fetchLatestLocation,
  fetchNearbyHospitals,
  fetchOverview,
} from '../api/dashboard';
import type { LocationSnapshot } from '../api/types';
import { usePollingResource } from './usePollingResource';

export function useDashboardData() {
  const overview = usePollingResource(fetchOverview, { intervalMs: POLL_INTERVAL_MS });
  const incidents = usePollingResource(fetchIncidents, { intervalMs: POLL_INTERVAL_MS });

  return { overview, incidents };
}

export function useIncidentDetail(incidentId: string | null) {
  const load = useCallback(
    (signal: AbortSignal) => {
      if (!incidentId) {
        return Promise.reject(new Error('No incident selected.'));
      }
      return fetchIncidentDetail(incidentId, signal);
    },
    [incidentId],
  );

  return usePollingResource(load, {
    intervalMs: POLL_INTERVAL_MS,
    enabled: incidentId !== null,
    resetKey: incidentId ?? 'none',
  });
}

export function useNearbyHospitals(location: LocationSnapshot | null | undefined) {
  const latitude = location?.latitude;
  const longitude = location?.longitude;

  const load = useCallback(
    (signal: AbortSignal) => {
      if (typeof latitude !== 'number' || typeof longitude !== 'number') {
        return Promise.reject(new Error('No location is available for hospital lookup.'));
      }
      return fetchNearbyHospitals(latitude, longitude, signal);
    },
    [latitude, longitude],
  );

  return usePollingResource(load, {
    intervalMs: POLL_INTERVAL_MS,
    enabled: typeof latitude === 'number' && typeof longitude === 'number',
    resetKey:
      typeof latitude === 'number' && typeof longitude === 'number'
        ? `${latitude}:${longitude}`
        : 'none',
  });
}

export function useLatestLocation(subjectUserId: string | null | undefined) {
  const load = useCallback(
    (signal: AbortSignal) => {
      if (!subjectUserId) {
        return Promise.reject(new Error('No monitored subject is available.'));
      }
      return fetchLatestLocation(subjectUserId, signal);
    },
    [subjectUserId],
  );

  return usePollingResource(load, {
    intervalMs: POLL_INTERVAL_MS,
    enabled: Boolean(subjectUserId),
    resetKey: subjectUserId ?? 'none',
  });
}
