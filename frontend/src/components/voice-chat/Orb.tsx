"use client";

import { VoiceState } from "@/types";

interface OrbProps {
  state: VoiceState;
}

const stateStyles: Record<VoiceState, string> = {
  [VoiceState.IDLE]:
    "animate-breathe orb-glow bg-gradient-to-br from-accent/20 to-accent-light/30",
  [VoiceState.CONNECTING]:
    "animate-spin-slow orb-glow bg-gradient-to-br from-accent/30 to-accent-glow/20",
  [VoiceState.LISTENING]:
    "animate-breathe orb-glow-active bg-gradient-to-br from-accent/40 to-accent-glow/30",
  [VoiceState.SPEAKING]:
    "animate-morph orb-glow-speaking bg-gradient-to-br from-accent to-purple-500/80",
  [VoiceState.ERROR]:
    "orb-glow bg-gradient-to-br from-red-400/30 to-red-500/20",
};

export default function Orb({ state }: OrbProps) {
  return (
    <div className="relative flex items-center justify-center w-48 h-48">
      {/* Ripple rings (visible when listening) */}
      {state === VoiceState.LISTENING && (
        <>
          <div className="absolute inset-0 rounded-full bg-accent/10 animate-ripple" />
          <div
            className="absolute inset-0 rounded-full bg-accent/5 animate-ripple"
            style={{ animationDelay: "0.5s" }}
          />
        </>
      )}

      {/* Main orb */}
      <div
        className={[
          "w-32 h-32 rounded-full transition-all duration-600 ease-out",
          stateStyles[state],
        ].join(" ")}
      />

      {/* Center dot */}
      <div
        className={[
          "absolute w-3 h-3 rounded-full transition-all duration-300",
          state === VoiceState.SPEAKING
            ? "bg-white/90 scale-110"
            : state === VoiceState.LISTENING
              ? "bg-accent/80"
              : "bg-accent/40",
        ].join(" ")}
      />
    </div>
  );
}
