"use client";

import dynamic from "next/dynamic";

const VoiceApp = dynamic(
  () => import("@/components/voice-chat/VoiceApp"),
  { ssr: false }
);

export default function Home() {
  return <VoiceApp />;
}
