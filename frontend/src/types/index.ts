export enum VoiceState {
  IDLE = "idle",
  CONNECTING = "connecting",
  LISTENING = "listening",
  SPEAKING = "speaking",
  ERROR = "error",
}

export interface SessionConfig {
  baseUrl: string;
  connectEndpoint: string;
}
