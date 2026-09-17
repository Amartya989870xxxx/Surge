import React, { useState, useEffect } from 'react';
import type { AppType, ConnectorsOut } from '../../types/api';
import { listConnectors, startOAuth } from '../../lib/api/connectors';
import { Button } from '../ui/Button';
import { SourceIcon } from '../ui/SourceIcon';
import { Badge } from '../ui/Badge';
import { StatusDot } from '../ui/StatusDot';

interface Step04ConnectProps {
  selectedApps: AppType[];
  onNext: () => void;
  onBack: () => void;
}

export const Step04Connect: React.FC<Step04ConnectProps> = ({
  selectedApps,
  onNext,
  onBack,
}) => {
  const [connectorsData, setConnectorsData] = useState<ConnectorsOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectingApp, setConnectingApp] = useState<string | null>(null);
  const [oauthError, setOauthError] = useState<string | null>(null);

  useEffect(() => {
    listConnectors()
      .then((data) => {
        setConnectorsData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to list connectors:', err);
        setLoading(false);
      });
  }, []);

  const handleStartOAuth = async (app: string) => {
    setConnectingApp(app);
    setOauthError(null);
    try {
      const res = await startOAuth(app);
      if (res.auth_url || res.url) {
        window.location.href = res.auth_url || res.url || '';
      } else {
        setOauthError(
          `OAuth is not configured for ${app} in the backend environment. Running in seeded DEMO mode.`
        );
      }
    } catch (err: any) {
      setOauthError(err.message || `Failed to initiate OAuth for ${app}`);
    } finally {
      setConnectingApp(null);
    }
  };

  const getConnectorForApp = (app: AppType) => {
    return connectorsData?.connectors.find(
      (c) => c.app.toLowerCase() === app.toLowerCase()
    );
  };

  return (
    <div className="max-w-xl mx-auto py-8 font-mono">
      <div className="mb-6">
        <span className="text-xs text-[#818CF8] uppercase tracking-wider">Step 4 of 5</span>
        <h2 className="text-2xl font-bold text-[#F5F5F5] mt-1 mb-2">
          Verify Signal Connections
        </h2>
        <p className="text-xs text-[#A1A1AA] leading-relaxed">
          Surge verifies connectivity with each selected data provider. In this demo workspace,
          deterministic seeded worlds provide realistic test traces.
        </p>
      </div>

      {oauthError && (
        <div className="p-3 bg-amber-950/30 border border-amber-800/60 rounded text-xs text-amber-300 mb-4">
          {oauthError}
        </div>
      )}

      {loading ? (
        <div className="p-8 text-center text-xs text-[#71717A]">
          Checking backend connector health...
        </div>
      ) : (
        <div className="space-y-3 mb-8">
          {selectedApps.map((app) => {
            const connector = getConnectorForApp(app);
            const isDemo = connector?.mode === 'DEMO';
            const isConnected = connector?.status === 'demo' || connector?.status === 'connected';

            return (
              <div
                key={app}
                className="p-4 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3">
                  <SourceIcon app={app} size={20} />
                  <div>
                    <div className="text-sm font-bold text-[#F5F5F5] uppercase">
                      {connector?.display_name || app}
                    </div>
                    <div className="text-[11px] text-[#71717A] mt-0.5">
                      {connector?.account_label || 'Seeded Acme Storefront demo environment'}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant={isDemo ? 'demo' : 'real'}>
                    <StatusDot status={isConnected ? 'success' : 'danger'} size="sm" />
                    <span>{isConnected ? (isDemo ? 'SEEDED DEMO' : 'CONNECTED') : 'NOT CONNECTED'}</span>
                  </Badge>

                  {connector?.oauth_configured && !isConnected && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleStartOAuth(app)}
                      loading={connectingApp === app}
                      className="text-xs"
                    >
                      Authorize
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="flex items-center justify-between pt-4 border-t border-[#1A1A1F]">
        <Button size="md" variant="ghost" onClick={onBack} className="text-xs">
          ← Back
        </Button>

        <Button size="md" variant="primary" onClick={onNext} className="text-xs">
          Complete Setup →
        </Button>
      </div>
    </div>
  );
};
