"use client";

import { VoiceState } from "@/types";

interface StatusLabelProps {
  state: VoiceState;
  error?: string | null;
}

const stateLabels: Record<VoiceState, string> = {
  [VoiceState.IDLE]: "Ready to talk",
  [VoiceState.CONNECTING]: "Connecting...",
  [VoiceState.LISTENING]: "Listening to you...",
  [VoiceState.SPEAKING]: "Speaking...",
  [VoiceState.ERROR]: "Something went wrong",
};

export default function StatusLabel({ state, error }: StatusLabelProps) {
  const label = error && state === VoiceState.ERROR ? error : stateLabels[state];

  return (
    <p
      key={label}
      className="text-[13px] text-zinc-500 h-5 animate-fade-in"
    >
      {label}
    </p>
  );
}
