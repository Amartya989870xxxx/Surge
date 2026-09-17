import React, { useState, useEffect } from 'react';
import type { ConnectorsOut, ConnectorInfo } from '../../types/api';
import { listConnectors, startOAuth, disconnectConnector } from '../../lib/api/connectors';
import Integrations, { type IntegrationData } from '../ui/integrations-02';
import {
  GoogleSheetsIcon,
  GitHubIcon,
  SlackIcon,
} from '../ui/official-icons';

export const IntegrationsPage: React.FC = () => {
  const [data, setData] = useState<ConnectorsOut | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const fetchData = () => {
    listConnectors()
      .then((res) => {
        setData(res);
      })
      .catch((err) => {
        setMessage(err.message || 'Failed to fetch connectors');
      });
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleConnect = async (app: string) => {
    setMessage(null);
    try {
      const res = await startOAuth(app);
      if (res.auth_url || res.url) {
        window.location.href = res.auth_url || res.url || '';
      } else {
        setMessage(`OAuth for ${app} is not configured in environment. Using DEMO mode.`);
        fetchData();
      }
    } catch (err: any) {
      setMessage(err.message || `Failed to initiate connection for ${app}`);
    }
  };

  const handleDisconnect = async (app: string) => {
    setMessage(null);
    try {
      await disconnectConnector(app);
      setMessage(`Disconnected ${app}.`);
      fetchData();
    } catch (err: any) {
      setMessage(err.message || `Failed to disconnect ${app}`);
    }
  };

  const sheetsConn = data?.connectors.find((c: ConnectorInfo) => c.app === 'sheets');
  const githubConn = data?.connectors.find((c: ConnectorInfo) => c.app === 'github');
  const slackConn = data?.connectors.find((c: ConnectorInfo) => c.app === 'slack');

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

  return (
    <div className="p-6 h-full overflow-y-auto flex flex-col items-center">
      {message && (
        <div className="w-full max-w-lg p-3 bg-indigo-950/60 border border-indigo-800/80 rounded-xl text-indigo-300 text-xs text-center mb-4">
          {message}
        </div>
      )}

      <Integrations
        integrations={formattedIntegrations}
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
      />
    </div>
  );
};
