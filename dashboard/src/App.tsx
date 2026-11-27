import { useCallback, useEffect, useState } from 'react';
import { API_BASE_URL } from './api/config';
import { Sidebar, type ViewKey } from './components/Sidebar';
import { Topbar, type ConnectionState } from './components/Topbar';
import { useDashboardData, useIncidentDetail } from './hooks/useDashboardData';
import { IncidentsView } from './views/IncidentsView';
import { LocationView } from './views/LocationView';
import { MonitoringView } from './views/MonitoringView';
import { OverviewView } from './views/OverviewView';

export default function App() {
  const [activeView, setActiveView] = useState<ViewKey>('overview');
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const { overview, incidents } = useDashboardData();
  const incidentDetail = useIncidentDetail(selectedIncidentId);

  useEffect(() => {
    if (selectedIncidentId === null && incidents.data && incidents.data.length > 0) {
      setSelectedIncidentId(incidents.data[0]?.incident_id ?? null);
    }
  }, [incidents.data, selectedIncidentId]);

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

  const overviewData = overview.data;
  const subjectName = overviewData?.subject_user_id ? 'Monitored person' : '';
  const dataSource =
    overviewData?.monitoring?.data_source ?? null;
  const activeIncidents = overviewData?.active_incidents ?? null;
  const activeCount =
    typeof overviewData?.active_incident_count === 'number'
      ? overviewData.active_incident_count
      : activeIncidents
        ? activeIncidents.length
        : null;

  let connection: ConnectionState = 'connecting';
  if (overview.error) {
    connection = 'error';
  } else if (!overview.isLoading || overviewData) {
    connection = 'connected';
  }

  const lastUpdatedAt = Math.max(
    overview.lastUpdatedAt ?? 0,
    incidents.lastUpdatedAt ?? 0,
  ) || null;

  const selectedIncident =
    incidentDetail.data?.incident_id === selectedIncidentId ? incidentDetail.data : null;

  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to dashboard content
      </a>

      <div className="app-shell">
        <Sidebar
          activeIncidentCount={activeCount}
          activeView={activeView}
          onNavigate={handleNavigate}
        />

        <div className="app-main">
          <Topbar
            activeView={activeView}
            connection={connection}
            dataSource={dataSource}
            isRefreshing={overview.isRefreshing || incidents.isRefreshing}
            lastUpdatedAt={lastUpdatedAt}
            onRefresh={refreshAll}
            subjectName={subjectName}
          />

          <main className="content" id="main-content">
            <div aria-live="polite" className="visually-hidden">
              {activeCount === null
                ? 'Active incident count not provided by the backend.'
                : `${activeCount} active incidents reported by the backend.`}
            </div>

            {activeView === 'overview' ? (
              <OverviewView
                incidents={incidents.data ?? []}
                incidentsError={incidents.error}
                onNavigate={handleNavigate}
                onRetry={refreshAll}
                onSelectIncident={handleSelectIncident}
                overview={overviewData}
                overviewError={overview.error}
                overviewLoading={overview.isLoading}
              />
            ) : null}

            {activeView === 'monitoring' ? (
              <MonitoringView
                onRetry={refreshAll}
                overview={overviewData}
                overviewError={overview.error}
                overviewLoading={overview.isLoading}
              />
            ) : null}

            {activeView === 'incidents' ? (
              <IncidentsView
                detailError={incidentDetail.error}
                detailLoading={incidentDetail.isLoading}
                incidents={incidents.data ?? []}
                incidentsError={incidents.error}
                incidentsLoading={incidents.isLoading}
                onRetry={refreshAll}
                onRetryDetail={incidentDetail.refresh}
                onSelectIncident={handleSelectIncident}
                selectedIncident={selectedIncident}
                selectedIncidentId={selectedIncidentId}
              />
            ) : null}

            {activeView === 'location' ? (
              <LocationView
                incidents={incidents.data ?? []}
                incidentsError={incidents.error}
                onRetry={refreshAll}
                onSelectIncident={handleSelectIncident}
                overview={overviewData}
                overviewError={overview.error}
                overviewLoading={overview.isLoading}
              />
            ) : null}
          </main>

          <footer className="app-footer">
            <p>
              SAHYOG prototype · Caregiver dashboard · Status is backend-authoritative. Not a
              medical device or emergency-dispatch service.
            </p>
            <p className="app-footer__api">
              API <code>{API_BASE_URL}</code>
            </p>
          </footer>
        </div>
      </div>
    </>
  );
}
