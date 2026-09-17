import React, { useState, useRef, useEffect, useCallback } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import {
  ImageIcon,
  FileUp,
  MonitorIcon,
  CircleUserRound,
  ArrowUpIcon,
  Paperclip,
  Code2,
  Palette,
  Layers,
  Rocket,
} from "lucide-react";

interface AutoResizeProps {
  minHeight: number;
  maxHeight?: number;
}

export function useAutoResizeTextarea({ minHeight, maxHeight }: AutoResizeProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback(
    (reset?: boolean) => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      if (reset) {
        textarea.style.height = `${minHeight}px`;
        return;
      }

      textarea.style.height = `${minHeight}px`; // reset first
      const newHeight = Math.max(
        minHeight,
        Math.min(textarea.scrollHeight, maxHeight ?? Infinity)
      );
      textarea.style.height = `${newHeight}px`;
    },
    [minHeight, maxHeight]
  );

  useEffect(() => {
    if (textareaRef.current) textareaRef.current.style.height = `${minHeight}px`;
  }, [minHeight]);

  return { textareaRef, adjustHeight };
}

export interface QuickActionItem {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
}

export interface RuixenMoonChatProps {
  title?: string;
  subtitle?: string;
  placeholder?: string;
  value?: string;
  onChange?: (val: string) => void;
  onSubmit?: () => void;
  isLoading?: boolean;
  quickActions?: QuickActionItem[];
  headerBadge?: React.ReactNode;
  leftFooterSlot?: React.ReactNode;
  backgroundImageUrl?: string;
  className?: string;
}

export default function RuixenMoonChat({
  title = "Ruixen AI",
  subtitle = "Build something amazing — just start typing below.",
  placeholder = "Type your request...",
  value,
  onChange,
  onSubmit,
  isLoading = false,
  quickActions,
  headerBadge,
  leftFooterSlot,
  backgroundImageUrl = "/images/ruixen-moon.png",
  className,
}: RuixenMoonChatProps) {
  const [internalMessage, setInternalMessage] = useState("");
  const message = value !== undefined ? value : internalMessage;
  const setMessage = (val: string) => {
    if (onChange) onChange(val);
    else setInternalMessage(val);
  };

  const { textareaRef, adjustHeight } = useAutoResizeTextarea({
    minHeight: 48,
    maxHeight: 160,
  });

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (onSubmit && message.trim() && !isLoading) {
        onSubmit();
        adjustHeight(true);
      }
    }
  };

  const defaultQuickActions: QuickActionItem[] = [
    { icon: <Code2 className="w-4 h-4" />, label: "Generate Code" },
    { icon: <Rocket className="w-4 h-4" />, label: "Launch App" },
    { icon: <Layers className="w-4 h-4" />, label: "UI Components" },
    { icon: <Palette className="w-4 h-4" />, label: "Theme Ideas" },
    { icon: <CircleUserRound className="w-4 h-4" />, label: "User Dashboard" },
    { icon: <MonitorIcon className="w-4 h-4" />, label: "Landing Page" },
    { icon: <FileUp className="w-4 h-4" />, label: "Upload Docs" },
    { icon: <ImageIcon className="w-4 h-4" />, label: "Image Assets" },
  ];

  const actions = quickActions || defaultQuickActions;

  return (
    <div
      className={cn(
        "relative w-full min-h-screen bg-cover bg-center flex flex-col items-center justify-between overflow-hidden",
        className
      )}
      style={{
        backgroundImage: `url('${backgroundImageUrl}'), url('https://cdn.21st.dev/assets/mirror/c3/c333918af688a4a8a3d004652e6c0ee219457a9d84d380eeb31f513d4b59a09f.png')`,
        backgroundAttachment: "fixed",
        backgroundColor: "#000000",
      }}
    >
      {/* Ambient Celestial Glow Fallback & Aura */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/4 h-[550px] bg-gradient-to-t from-transparent via-indigo-600/25 to-blue-500/10 blur-3xl opacity-60 rounded-full"
      />

      {/* Centered AI Title */}
      <div className="flex-1 w-full flex flex-col items-center justify-center pt-16 pb-8 px-6 z-10">
        <div className="text-center max-w-2xl">
          {headerBadge && <div className="mb-4 flex justify-center">{headerBadge}</div>}
          <h1 className="text-4xl sm:text-5xl font-semibold text-white drop-shadow-sm font-caacupe tracking-tight">
            {title}
          </h1>
          <p className="mt-3 text-neutral-300 text-sm sm:text-base leading-relaxed">
            {subtitle}
          </p>
        </div>
      </div>

      {/* Input Box Section */}
      <div className="w-full max-w-3xl px-6 mb-16 sm:mb-20 z-10">
        <div className="relative bg-black/60 backdrop-blur-xl rounded-2xl border border-neutral-700/80 shadow-2xl shadow-black/80 transition-all focus-within:border-indigo-500/70 focus-within:ring-1 focus-within:ring-indigo-500/30">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => {
              setMessage(e.target.value);
              adjustHeight();
            }}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className={cn(
              "w-full px-5 py-4 resize-none border-none",
              "bg-transparent text-white text-sm",
              "focus-visible:ring-0 focus-visible:ring-offset-0",
              "placeholder:text-neutral-400 min-h-[52px]"
            )}
            style={{ overflow: "hidden" }}
          />

          {/* Footer Buttons */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-neutral-800/60">
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-neutral-400 hover:text-white hover:bg-neutral-800/80 rounded-xl size-9 transition-colors"
                title="Attach evidence files or traces"
              >
                <Paperclip className="w-4 h-4" />
              </Button>
              {leftFooterSlot}
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                onClick={() => {
                  if (onSubmit && message.trim() && !isLoading) {
                    onSubmit();
                    adjustHeight(true);
                  }
                }}
                disabled={!message.trim() || isLoading}
                className={cn(
                  "size-9 p-0 rounded-xl flex items-center justify-center transition-all",
                  message.trim() && !isLoading
                    ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 cursor-pointer"
                    : "bg-neutral-800 text-neutral-500 cursor-not-allowed border border-neutral-700/50"
                )}
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <ArrowUpIcon className="w-4 h-4" />
                )}
                <span className="sr-only">Send</span>
              </Button>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center justify-center flex-wrap gap-2.5 mt-6">
          {actions.map((action, idx) => (
            <QuickAction
              key={idx}
              icon={action.icon}
              label={action.label}
              onClick={action.onClick}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

interface QuickActionProps {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
}

export function QuickAction({ icon, label, onClick }: QuickActionProps) {
  return (
    <Button
      type="button"
      variant="outline"
      onClick={onClick}
      className="flex items-center gap-2 rounded-full border-neutral-700/80 bg-black/60 text-neutral-300 hover:text-white hover:bg-neutral-800/90 hover:border-neutral-600 transition-all backdrop-blur-md px-4 py-2 h-auto text-xs shadow-sm cursor-pointer"
    >
      {icon}
      <span className="text-xs font-medium">{label}</span>
    </Button>
  );
}
