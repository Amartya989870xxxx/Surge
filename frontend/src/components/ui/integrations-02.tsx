import React, { useState } from "react";
import { ArrowUpRight, Check, X } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  GoogleSheetsIcon,
  GitHubIcon,
  SlackIcon,
} from "@/components/ui/official-icons";
import { cn } from "@/lib/utils";

export interface IntegrationData {
  title: string;
  description?: string;
  app: string;
  status: "connected" | "pending" | "not_connected" | "demo";
  account_label?: string;
  icon: React.ReactNode;
}

// Fallback shown only if this component is ever rendered without real fetched props - must
// never claim a connection that hasn't actually been verified against the backend.
const defaultIntegrations: IntegrationData[] = [
  {
    title: "Google Sheets",
    description: "Read-only access to operational metric spreadsheets and checkout funnels.",
    app: "sheets",
    status: "not_connected",
    icon: <GoogleSheetsIcon />,
  },
  {
    title: "GitHub",
    description: "Inspect recent releases, view commit diffs, and create verified incident issues.",
    app: "github",
    status: "not_connected",
    icon: <GitHubIcon />,
  },
  {
    title: "Slack",
    description: "Search public channel messages for customer incident reports and alerts.",
    app: "slack",
    status: "not_connected",
    icon: <SlackIcon />,
  },
];

interface IntegrationsProps {
  integrations?: IntegrationData[];
  onConnect?: (app: string) => void;
  onDisconnect?: (app: string) => void;
  onContinueToWorkspace?: () => void;
  onBackToIntro?: () => void;
  className?: string;
}

export default function Integrations({
  integrations: propIntegrations,
  onConnect,
  onDisconnect,
  onContinueToWorkspace,
  onBackToIntro,
  className,
}: IntegrationsProps) {
  const [items, setItems] = useState<IntegrationData[]>(
    propIntegrations || defaultIntegrations
  );
  const [hoveredApp, setHoveredApp] = useState<string | null>(null);

  // Keep internal items in sync if prop changes
  React.useEffect(() => {
    if (propIntegrations) {
      setItems(propIntegrations);
    }
  }, [propIntegrations]);

  const handleToggleConnect = (app: string, currentStatus: string) => {
    if (currentStatus === "connected") {
      if (onDisconnect) {
        onDisconnect(app);
      } else {
        setItems((prev) =>
          prev.map((item) =>
            item.app === app ? { ...item, status: "not_connected" } : item
          )
        );
      }
    } else {
      if (onConnect) {
        onConnect(app);
      } else {
        setItems((prev) =>
          prev.map((item) =>
            item.app === app ? { ...item, status: "connected" } : item
          )
        );
      }
    }
  };

  return (
    <div className={cn("my-10 px-4 sm:my-14 flex flex-col items-center justify-center select-none", className)}>
      <div className="mx-auto flex w-full max-w-lg flex-col rounded-2xl border border-white/10 bg-[#0B0C10]/95 p-1.5 shadow-2xl backdrop-blur-xl">
        <div className="rounded-xl border border-white/5 bg-[#0F1117] p-6 sm:p-8">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-bold text-2xl tracking-tight text-white">
                Our Integrations
              </h2>
              <p className="mt-1.5 text-sm text-[#A1A1AA] leading-relaxed">
                Connect your favorite tools and services to your account and start
                using them in your app.
              </p>
            </div>
            {onBackToIntro && (
              <button
                onClick={onBackToIntro}
                className="text-xs text-[#71717A] hover:text-white transition-colors cursor-pointer py-1 px-2 rounded hover:bg-white/5"
              >
                ← Overview
              </button>
            )}
          </div>

          {/* Integrations List matching 4th reference image */}
          <div className="mx-auto mt-8 flex w-full flex-col gap-3">
            {items.map((integration) => {
              const isConnected = integration.status === "connected";
              const isHovered = hoveredApp === integration.app;

              return (
                <div
                  className="flex items-center gap-3.5 rounded-xl border border-white/8 bg-[#141620]/90 px-4 py-3.5 transition-all duration-200 hover:border-white/20 hover:bg-[#181B26]"
                  key={integration.app || integration.title}
                  onMouseEnter={() => setHoveredApp(integration.app)}
                  onMouseLeave={() => setHoveredApp(null)}
                >
                  {/* Official Rounded Icon */}
                  <div className="shrink-0 size-9 rounded-lg overflow-hidden flex items-center justify-center shadow-md">
                    {integration.icon}
                  </div>

                  {/* Title & Account info */}
                  <div className="min-w-0 flex-1">
                    <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                      {integration.title}
                    </h3>
                    {integration.account_label && (
                      <p className="text-[11px] text-[#71717A] truncate font-mono">
                        {integration.account_label}
                      </p>
                    )}
                  </div>

                  {/* Status / Connect Action */}
                  <div className="ms-auto shrink-0 flex items-center gap-2">
                    {isConnected ? (
                      isHovered ? (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() =>
                            handleToggleConnect(integration.app, integration.status)
                          }
                          className="h-7 min-w-24 text-[11px] font-semibold rounded-lg bg-red-950/40 text-red-300 border border-red-800/40 hover:bg-red-900/60"
                        >
                          <X className="size-3 mr-1" /> Disconnect
                        </Button>
                      ) : (
                        <Badge
                          variant="outline"
                          className="h-7 min-w-24 justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold"
                        >
                          <Check className="size-3 mr-1" /> Connected
                        </Badge>
                      )
                    ) : (
                      <Button
                        className="h-7 min-w-24 text-xs font-semibold rounded-lg border-white/20 bg-white/5 hover:bg-white/10 text-white"
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          handleToggleConnect(integration.app, integration.status)
                        }
                      >
                        Connect <ArrowUpRight className="size-3.5 ml-1" />
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Bottom Action Footer */}
          {onContinueToWorkspace && (
            <div className="mt-8 pt-6 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3">
              <span className="text-[11px] text-[#71717A]">
                100% auditable evidence grounding
              </span>
              <Button
                variant="primary"
                size="default"
                onClick={onContinueToWorkspace}
                className="w-full sm:w-auto text-xs px-5 py-2 font-bold shadow-lg shadow-indigo-950/50 hover:scale-[1.02] transition-transform"
              >
                Continue to Workspace →
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
