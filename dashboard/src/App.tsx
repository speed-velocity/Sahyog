import { useCallback, useEffect, useState } from 'react';
import { API_BASE_URL } from './api/config';
import { fetchAuthorizedSubjects } from './api/dashboard';
import type { AuthorizedSubject } from './api/types';
import { Sidebar, type ViewKey } from './components/Sidebar';
import { Topbar, type ConnectionState } from './components/Topbar';
import { useDashboardData, useIncidentDetail } from './hooks/useDashboardData';
import { IncidentsView } from './views/IncidentsView';
import { LocationView } from './views/LocationView';
import { MonitoringView } from './views/MonitoringView';
import { OverviewView } from './views/OverviewView';
import { LoginForm } from './components/LoginForm';

export default function App() {
  const [activeView, setActiveView] = useState<ViewKey>('overview');
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() =>
    typeof sessionStorage !== 'undefined' && Boolean(sessionStorage.getItem('sahyog_token')),
  );
  const [authorizedSubjects, setAuthorizedSubjects] = useState<AuthorizedSubject[]>([]);
  const [subjectsLoading, setSubjectsLoading] = useState(false);
  const [subjectsError, setSubjectsError] = useState<string | null>(null);
  const [selectedSubjectUserId, setSelectedSubjectUserId] = useState<string | null>(null);
  const [subjectsReloadKey, setSubjectsReloadKey] = useState(0);

  // Fetch authorized subjects after login
  useEffect(() => {
    if (!isAuthenticated) {
      setAuthorizedSubjects([]);
      setSelectedSubjectUserId(null);
      setSubjectsError(null);
      setSubjectsLoading(false);
      return;
    }

    const abort = new AbortController();
    setSubjectsLoading(true);
    setSubjectsError(null);
    fetchAuthorizedSubjects(abort.signal)
      .then((response) => {
        const subjects = response.authorized_subjects;
        setAuthorizedSubjects(subjects);
        setSelectedSubjectUserId((current) => {
          if (current && subjects.some((subject) => subject.subject_user_id === current)) return current;
          return subjects.length === 1 ? subjects[0].subject_user_id : null;
        });
      })
      .catch((error: unknown) => {
        if (!abort.signal.aborted) {
          setAuthorizedSubjects([]);
          setSelectedSubjectUserId(null);
          setSubjectsError(error instanceof Error ? error.message : 'Unable to load authorized subjects.');
        }
      })
      .finally(() => {
        if (!abort.signal.aborted) setSubjectsLoading(false);
      });

    return () => abort.abort();
  }, [isAuthenticated, subjectsReloadKey]);

  const { overview, incidents } = useDashboardData(selectedSubjectUserId, isAuthenticated);
  const overviewData = overview.data;
  const subjectDataReady = overviewData?.subject_user_id === selectedSubjectUserId;
  const currentOverview = subjectDataReady ? overviewData : null;
  const currentIncidents = subjectDataReady
    ? (incidents.data ?? []).filter((incident) => incident.subject_user_id === selectedSubjectUserId)
    : [];
  const incidentDetail = useIncidentDetail(
    selectedIncidentId,
    isAuthenticated && Boolean(selectedSubjectUserId) &&
      currentIncidents.some((incident) => incident.incident_id === selectedIncidentId),
  );

  useEffect(() => {
    if (
      selectedIncidentId === null &&
      currentIncidents.length > 0
    ) {
      setSelectedIncidentId(currentIncidents[0]?.incident_id ?? null);
    }
  }, [currentIncidents, selectedIncidentId]);

  const refreshAll = useCallback(() => {
    overview.refresh();
    incidents.refresh();
  }, [overview.refresh, incidents.refresh]);

  const handleNavigate = useCallback((view: ViewKey) => {
    setActiveView(view);
  }, []);

  const handleSelectIncident = useCallback((incidentId: string) => {
    setSelectedIncidentId(incidentId);
    setActiveView('incidents');
  }, []);

  const subjectName = selectedSubjectUserId ? 'Monitored person' : 'No subject selected';
  const dataSource = currentOverview?.monitoring.data_source ?? null;
  // The backend overview reports one active incident ID, not a total count.
  const activeCount: number | null = null;

  let connection: ConnectionState = 'connecting';
  if (!isAuthenticated || !selectedSubjectUserId) {
    connection = 'connecting';
  } else if (overview.error) {
    connection = 'error';
  } else if (!overview.isLoading || currentOverview) {
    connection = 'connected';
  }

  const lastUpdatedAt = subjectDataReady
    ? Math.max(overview.lastUpdatedAt ?? 0, incidents.lastUpdatedAt ?? 0) || null
    : null;

  const selectedIncident =
    incidentDetail.data?.incident_id === selectedIncidentId ? incidentDetail.data : null;
  const handleSelectSubject = useCallback((subjectUserId: string) => {
    setSelectedIncidentId(null);
    setSelectedSubjectUserId(subjectUserId || null);
  }, []);

  const handleLogout = useCallback(() => {
    if (typeof sessionStorage !== 'undefined') sessionStorage.removeItem('sahyog_token');
    setIsAuthenticated(false);
    setAuthorizedSubjects([]);
    setSelectedSubjectUserId(null);
    setSelectedIncidentId(null);
    setSubjectsError(null);
    setSubjectsLoading(false);
    setActiveView('overview');
  }, []);

  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to dashboard content
      </a>

      <div className="app-shell">
        {isAuthenticated ? (
          <Sidebar
            activeIncidentCount={activeCount}
            activeView={activeView}
            onNavigate={handleNavigate}
          />
        ) : null}

        <div className="app-main">
          {!isAuthenticated ? <LoginForm onLoginSuccess={() => setIsAuthenticated(true)} /> : null}

          {isAuthenticated ? (
            <Topbar
              activeView={activeView}
              connection={connection}
              dataSource={dataSource}
              isRefreshing={overview.isRefreshing || incidents.isRefreshing}
              lastUpdatedAt={lastUpdatedAt}
              onRefresh={refreshAll}
              subjectName={subjectName}
            />
          ) : null}

          <main className="content" id="main-content">
            {isAuthenticated ? (
              <section aria-label="Monitored subject" className="subject-control">
                {subjectsLoading ? <p role="status">Loading authorized subjects…</p> : null}
                {subjectsError ? (
                  <div role="alert">
                    <p>Could not load authorized subjects: {subjectsError}</p>
                    <button className="btn btn--secondary btn--sm" onClick={() => setSubjectsReloadKey((key) => key + 1)} type="button">
                      Retry subject discovery
                    </button>
                  </div>
                ) : null}
                {!subjectsLoading && !subjectsError && authorizedSubjects.length === 0 ? (
                  <p>No subjects are authorized for this caregiver account.</p>
                ) : null}
                {!subjectsLoading && !subjectsError && authorizedSubjects.length > 1 ? (
                  <label>
                    Monitored subject{' '}
                    <select
                      aria-label="Select monitored subject"
                      onChange={(event) => handleSelectSubject(event.target.value)}
                      value={selectedSubjectUserId ?? ''}
                    >
                      <option value="">Select a subject</option>
                      {authorizedSubjects.map((subject, index) => (
                        <option key={subject.subject_user_id} value={subject.subject_user_id}>
                          {`Authorized subject ${index + 1}`}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}
              </section>
            ) : null}

            <div aria-live="polite" className="visually-hidden">
              {activeCount === null
                ? 'Active incident count not provided by the backend.'
                : `${activeCount} active incidents reported by the backend.`}
            </div>

            {isAuthenticated && selectedSubjectUserId && activeView === 'overview' ? (
              <OverviewView
                incidents={currentIncidents}
                incidentsError={incidents.error}
                onNavigate={handleNavigate}
                onRetry={refreshAll}
                onSelectIncident={handleSelectIncident}
                overview={currentOverview}
                overviewError={overview.error}
                overviewLoading={(overview.isLoading || !subjectDataReady) && !overview.error}
              />
            ) : null}

            {isAuthenticated && selectedSubjectUserId && activeView === 'monitoring' ? (
              <MonitoringView
                onRetry={refreshAll}
                overview={currentOverview}
                overviewError={overview.error}
                overviewLoading={(overview.isLoading || !subjectDataReady) && !overview.error}
              />
            ) : null}

            {isAuthenticated && selectedSubjectUserId && activeView === 'incidents' ? (
              <IncidentsView
                detailError={incidentDetail.error}
                detailLoading={incidentDetail.isLoading}
                incidents={currentIncidents}
                incidentsError={incidents.error}
                incidentsLoading={(incidents.isLoading || !subjectDataReady) && !incidents.error}
                onRetry={refreshAll}
                onRetryDetail={incidentDetail.refresh}
                onSelectIncident={handleSelectIncident}
                selectedIncident={selectedIncident}
                selectedIncidentId={selectedIncidentId}
              />
            ) : null}

            {isAuthenticated && selectedSubjectUserId && activeView === 'location' ? (
              <LocationView
                onRetry={refreshAll}
                onSelectIncident={handleSelectIncident}
                overview={currentOverview}
                overviewError={overview.error}
                overviewLoading={(overview.isLoading || !subjectDataReady) && !overview.error}
                subjectUserId={selectedSubjectUserId}
              />
            ) : null}
          </main>

          {isAuthenticated ? <footer className="app-footer">
            <p>
              SAHYOG prototype · Caregiver dashboard · Status is backend-authoritative. Not a
              medical device or emergency-dispatch service.
            </p>
            <p className="app-footer__api">
              API <code>{API_BASE_URL}</code>
            </p>
            <button className="btn btn--secondary btn--sm" onClick={handleLogout} type="button">
              Log out
            </button>
          </footer> : null}
        </div>
      </div>
    </>
  );
}
