"use client";

import { useVoiceState } from "@/hooks/useVoiceState";
import { VoiceState } from "@/types";
import Orb from "./Orb";
import ControlButton from "./ControlButton";
import StatusLabel from "./StatusLabel";
import WaveformBar from "./WaveformBar";

export default function VoiceChat() {
  const { voiceState, isConnected, error, connect, disconnect } =
    useVoiceState();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4">
      <div
        className="flex flex-col items-center gap-8 p-12 rounded-3xl
          bg-white border border-zinc-100
          shadow-[0_0_0_1px_rgba(0,0,0,0.02),0_2px_8px_rgba(0,0,0,0.04)]
          max-w-sm w-full"
      >
        {/* Header */}
        <h1 className="text-[20px] font-semibold text-zinc-900 tracking-tight">
          Voice Assistant
        </h1>

        {/* Orb */}
        <Orb state={voiceState} />

        {/* Status */}
        <StatusLabel state={voiceState} error={error} />

        {/* Control */}
        <ControlButton
          isConnected={isConnected}
          isConnecting={voiceState === VoiceState.CONNECTING}
          onConnect={connect}
          onDisconnect={disconnect}
        />

        {/* Waveform */}
        <WaveformBar state={voiceState} />
      </div>
    </div>
  );
}
