"use client";

import { useCallback, useState } from "react";
import { useRTVIClient, useRTVIClientEvent } from "@pipecat-ai/client-react";
import { RTVIEvent, TransportState } from "@pipecat-ai/client-js";
import { VoiceState } from "@/types";

export function useVoiceState() {
  const client = useRTVIClient();
  const [voiceState, setVoiceState] = useState<VoiceState>(VoiceState.IDLE);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useRTVIClientEvent(RTVIEvent.TransportStateChanged, (state: TransportState) => {
    switch (state) {
      case "connecting":
      case "authenticating":
        setVoiceState(VoiceState.CONNECTING);
        break;
      case "connected":
      case "ready":
        setIsConnected(true);
        setVoiceState(VoiceState.LISTENING);
        break;
      case "disconnected":
        setIsConnected(false);
        setVoiceState(VoiceState.IDLE);
        break;
    }
  });

  useRTVIClientEvent(RTVIEvent.BotStartedSpeaking, () => {
    setVoiceState(VoiceState.SPEAKING);
  });

  useRTVIClientEvent(RTVIEvent.BotStoppedSpeaking, () => {
    if (isConnected) setVoiceState(VoiceState.LISTENING);
  });

  useRTVIClientEvent(RTVIEvent.Error, (err: Error) => {
    setError(err.message);
    setVoiceState(VoiceState.ERROR);
  });

  const connect = useCallback(async () => {
    if (!client) return;
    setError(null);
    try {
      await client.connect();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connection failed");
      setVoiceState(VoiceState.ERROR);
    }
  }, [client]);

  const disconnect = useCallback(async () => {
    if (!client) return;
    try {
      await client.disconnect();
    } catch {
      // Already disconnected
    }
    setVoiceState(VoiceState.IDLE);
    setIsConnected(false);
  }, [client]);

  return { voiceState, isConnected, error, connect, disconnect };
}
