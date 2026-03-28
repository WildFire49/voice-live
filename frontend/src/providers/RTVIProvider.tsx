"use client";

import { RTVIClient } from "@pipecat-ai/client-js";
import { RTVIClientProvider, RTVIClientAudio } from "@pipecat-ai/client-react";
import { WebSocketTransport } from "@pipecat-ai/websocket-transport";
import { useRef, type ReactNode } from "react";
import { SESSION_CONFIG } from "@/lib/constants";

export default function VoiceProvider({ children }: { children: ReactNode }) {
  const clientRef = useRef<RTVIClient | null>(null);

  if (!clientRef.current) {
    const transport = new WebSocketTransport();
    clientRef.current = new RTVIClient({
      transport,
      params: {
        baseUrl: SESSION_CONFIG.baseUrl,
        endpoints: {
          connect: SESSION_CONFIG.connectEndpoint,
        },
      },
      enableMic: true,
      enableCam: false,
    });
  }

  return (
    <RTVIClientProvider client={clientRef.current}>
      {children}
      <RTVIClientAudio />
    </RTVIClientProvider>
  );
}
