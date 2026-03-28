"use client";

import { VoiceState } from "@/types";

interface WaveformBarProps {
  state: VoiceState;
}

export default function WaveformBar({ state }: WaveformBarProps) {
  const isActive =
    state === VoiceState.LISTENING || state === VoiceState.SPEAKING;

  return (
    <div className="flex items-center justify-center gap-[3px] h-6">
      {Array.from({ length: 24 }).map((_, i) => (
        <div
          key={i}
          className={[
            "w-[2px] rounded-full transition-all duration-300",
            isActive ? "bg-accent/40" : "bg-zinc-200",
          ].join(" ")}
          style={{
            height: isActive
              ? `${4 + Math.sin((i * Math.PI) / 6) * 12 + Math.random() * 4}px`
              : "3px",
            transitionDelay: `${i * 20}ms`,
          }}
        />
      ))}
    </div>
  );
}
