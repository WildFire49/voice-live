import VoiceProvider from "@/providers/RTVIProvider";
import VoiceChat from "@/components/voice-chat/VoiceChat";

export default function Home() {
  return (
    <VoiceProvider>
      <VoiceChat />
    </VoiceProvider>
  );
}
