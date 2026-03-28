import type { SessionConfig } from "@/types";

export const SESSION_CONFIG: SessionConfig = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  connectEndpoint: "/connect",
};

export const AUDIO_SAMPLE_RATE = 16000;
