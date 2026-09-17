import React, { useState, useEffect } from 'react';
import type { ConnectorsOut, ConnectorInfo } from '../../types/api';
import { listConnectors, startOAuth, disconnectConnector } from '../../lib/api/connectors';
import { onAuthChanged } from '../../lib/auth/firebase';
import IntegrationsSection from '../ui/integrations-3';
import Integrations, { type IntegrationData } from '../ui/integrations-02';
import {
  GoogleSheetsIcon,
  GitHubIcon,
  SlackIcon,
} from '../ui/official-icons';
import { WorkspaceFaviconButton } from '../ui/WorkspaceFaviconButton';

interface ConnectorsScreenProps {
  onContinueToWorkspace: () => void;
  connectedCallbackApp?: string | null;
  initialViewMode?: 'intro' | 'integrations';
}

export const ConnectorsScreen: React.FC<ConnectorsScreenProps> = ({
  onContinueToWorkspace,
  connectedCallbackApp,
  initialViewMode,
}) => {
  const [viewMode, setViewMode] = useState<'intro' | 'integrations'>(
    connectedCallbackApp || initialViewMode === 'integrations' ? 'integrations' : (initialViewMode || 'intro')
  );
  const [data, setData] = useState<ConnectorsOut | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const fetchConnectors = async () => {
    try {
      const res = await listConnectors();
      setData(res);
    } catch (err: any) {
      console.error('Failed to list connectors:', err);
    }
  };

  useEffect(() => {
    fetchConnectors();
    const unsub = onAuthChanged(() => {
      fetchConnectors();
    });

    if (connectedCallbackApp) {
      setNotice(`Returned from ${connectedCallbackApp} authorization flow.`);
      setViewMode('integrations');
    }

    return () => unsub();
  }, [connectedCallbackApp]);

  const handleConnect = async (app: string) => {
    setNotice(null);
    try {
      const res = await startOAuth(app);
      if (res.authorization_url || res.auth_url || res.url) {
        window.location.href = res.authorization_url || res.auth_url || res.url || '';
      } else {
        setNotice(`OAuth is not configured for ${app} on the backend. Deterministic DEMO mode will be used.`);
        await fetchConnectors();
      }
    } catch (err: any) {
      setNotice(err.message || `Failed to start connection for ${app}`);
    }
  };

  const handleDisconnect = async (app: string) => {
    setNotice(null);
    try {
      await disconnectConnector(app);
      setNotice(`Disconnected ${app}.`);
      await fetchConnectors();
    } catch (err: any) {
      setNotice(err.message || `Failed to disconnect ${app}`);
    }
  };

  // Map backend connectors to IntegrationData
  const sheetsConn = data?.connectors.find((c: ConnectorInfo) => c.app === 'sheets');
  const githubConn = data?.connectors.find((c: ConnectorInfo) => c.app === 'github');
  const slackConn = data?.connectors.find((c: ConnectorInfo) => c.app === 'slack');

  // account_label must only ever reflect a real, currently-connected account - never a
  // hardcoded fallback string, which would claim a connection that may not actually exist.
  const isLive = (c: ConnectorInfo | undefined) => c?.status === 'connected' || c?.status === 'demo';

  const formattedIntegrations: IntegrationData[] = [
    {
      title: 'Google Sheets',
      app: 'sheets',
      status: isLive(sheetsConn) ? 'connected' : 'not_connected',
      account_label: isLive(sheetsConn) ? sheetsConn?.account_label : undefined,
      description: sheetsConn?.detail || 'Read-only access to operational metric spreadsheets and checkout funnels.',
      icon: <GoogleSheetsIcon />,
    },
    {
      title: 'GitHub',
      app: 'github',
      status: isLive(githubConn) ? 'connected' : 'not_connected',
      account_label: isLive(githubConn) ? githubConn?.account_label : undefined,
      description: githubConn?.detail || 'Inspect recent releases, view commit diffs, and create verified incident issues.',
      icon: <GitHubIcon />,
    },
    {
      title: 'Slack',
      app: 'slack',
      status: isLive(slackConn) ? 'connected' : 'not_connected',
      account_label: isLive(slackConn) ? slackConn?.account_label : undefined,
      description: slackConn?.detail || 'Search public channel messages for customer incident reports and engineering discussion.',
      icon: <SlackIcon />,
    },
  ];

  if (viewMode === 'intro') {
    return (
      <div className="relative min-h-screen bg-[#000000]">
        <WorkspaceFaviconButton onNavigateWorkspace={onContinueToWorkspace} />
        <IntegrationsSection onGetStarted={() => setViewMode('integrations')} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#000000] text-[#F5F5F5] flex flex-col justify-center items-center px-4 py-12 relative">
      <WorkspaceFaviconButton onNavigateWorkspace={onContinueToWorkspace} />
      {notice && (
        <div className="w-full max-w-lg mb-4 p-3 bg-indigo-950/60 border border-indigo-800/80 rounded-xl text-indigo-300 text-xs text-center shadow-lg">
          {notice}
        </div>
      )}

      <Integrations
        integrations={formattedIntegrations}
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
        onContinueToWorkspace={onContinueToWorkspace}
        onBackToIntro={() => setViewMode('intro')}
      />
    </div>
  );
};
