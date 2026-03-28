"use client";

import { useCallback, useRef, useState } from "react";
import { usePipecatClient, useRTVIClientEvent } from "@pipecat-ai/client-react";
import { RTVIEvent, RTVIMessage, TransportStateEnum } from "@pipecat-ai/client-js";
import { VoiceState } from "@/types";
import { SESSION_CONFIG } from "@/lib/constants";

export function useVoiceState() {
  const client = usePipecatClient();
  const [voiceState, setVoiceState] = useState<VoiceState>(VoiceState.IDLE);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isConnectedRef = useRef(false);

  useRTVIClientEvent(RTVIEvent.TransportStateChanged, (state: string) => {
    switch (state) {
      case TransportStateEnum.CONNECTING:
      case TransportStateEnum.AUTHENTICATING:
        setVoiceState(VoiceState.CONNECTING);
        break;
      case TransportStateEnum.CONNECTED:
      case TransportStateEnum.READY:
        isConnectedRef.current = true;
        setIsConnected(true);
        setVoiceState(VoiceState.LISTENING);
        break;
      case TransportStateEnum.DISCONNECTED:
        isConnectedRef.current = false;
        setIsConnected(false);
        setVoiceState(VoiceState.IDLE);
        break;
      case TransportStateEnum.ERROR:
        setVoiceState(VoiceState.ERROR);
        break;
    }
  });

  useRTVIClientEvent(RTVIEvent.BotStartedSpeaking, () => {
    setVoiceState(VoiceState.SPEAKING);
  });

  useRTVIClientEvent(RTVIEvent.BotStoppedSpeaking, () => {
    if (isConnectedRef.current) setVoiceState(VoiceState.LISTENING);
  });

  useRTVIClientEvent(RTVIEvent.Error, (msg: RTVIMessage) => {
    setError(String(msg.data ?? "Connection error"));
    setVoiceState(VoiceState.ERROR);
  });

  const connect = useCallback(async () => {
    if (!client) return;
    setError(null);
    try {
      const connectUrl = `${SESSION_CONFIG.baseUrl}${SESSION_CONFIG.connectEndpoint}`;
      await client.startBotAndConnect({
        endpoint: connectUrl,
      });
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
