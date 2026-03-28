"use client";

import VoiceProvider from "@/providers/RTVIProvider";
import VoiceChat from "./VoiceChat";

export default function VoiceApp() {
  return (
    <VoiceProvider>
      <VoiceChat />
    </VoiceProvider>
  );
}
