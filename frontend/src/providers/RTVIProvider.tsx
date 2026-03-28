"use client";

import { PipecatClient } from "@pipecat-ai/client-js";
import { PipecatClientProvider, PipecatClientAudio } from "@pipecat-ai/client-react";
import { WebSocketTransport } from "@pipecat-ai/websocket-transport";
import { useRef, type ReactNode } from "react";

export default function VoiceProvider({ children }: { children: ReactNode }) {
  const clientRef = useRef<PipecatClient | null>(null);

  if (!clientRef.current) {
    const transport = new WebSocketTransport();
    clientRef.current = new PipecatClient({
      transport,
      enableMic: true,
      enableCam: false,
    });
  }

  return (
    <PipecatClientProvider client={clientRef.current}>
      {children}
      <PipecatClientAudio />
    </PipecatClientProvider>
  );
}
