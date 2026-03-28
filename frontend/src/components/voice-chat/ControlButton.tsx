"use client";

interface ControlButtonProps {
  isConnected: boolean;
  isConnecting: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
}

export default function ControlButton({
  isConnected,
  isConnecting,
  onConnect,
  onDisconnect,
}: ControlButtonProps) {
  if (isConnecting) {
    return (
      <button
        disabled
        className="px-8 py-3 rounded-full text-[15px] font-medium
          border border-zinc-200 text-zinc-400 cursor-not-allowed
          transition-all duration-200"
      >
        Connecting...
      </button>
    );
  }

  if (isConnected) {
    return (
      <button
        onClick={onDisconnect}
        className="px-8 py-3 rounded-full text-[15px] font-medium
          border border-zinc-200 text-zinc-600
          hover:border-zinc-300 hover:text-zinc-800
          hover:scale-[1.02] hover:shadow-sm
          active:scale-[0.98]
          transition-all duration-200"
      >
        End
      </button>
    );
  }

  return (
    <button
      onClick={onConnect}
      className="px-8 py-3 rounded-full text-[15px] font-medium
        bg-accent text-white
        hover:bg-accent/90 hover:scale-[1.02] hover:shadow-lg hover:shadow-accent/20
        active:scale-[0.98]
        transition-all duration-200"
    >
      Start Conversation
    </button>
  );
}
