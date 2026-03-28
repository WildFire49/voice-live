# Gemini Voice Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real-time voice assistant with Gemini 3.1 Flash Live, FastAPI + Pipecat backend, Next.js frontend with premium VC-demo-worthy UI.

**Architecture:** FastAPI WebSocket endpoint creates a Pipecat pipeline per session (Silero VAD + GeminiLiveLLMService). Frontend uses `@pipecat-ai/client-react` for transport/audio, custom UI components for the premium orb-based interface. RTVI protocol connects both sides via protobuf-serialized WebSocket frames.

**Tech Stack:** Python 3.11+, FastAPI, Pipecat (`pipecat-ai[google,silero,websocket]`), Next.js 14+, TypeScript, Tailwind CSS, `@pipecat-ai/client-react`, Inter font.

**Spec:** `docs/superpowers/specs/2026-03-28-gemini-voice-assistant-design.md`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/config/__init__.py`, `backend/app/core/__init__.py`, `backend/app/services/__init__.py`, `backend/app/transport/__init__.py`, `backend/app/api/__init__.py`
- Create: `backend/requirements.txt`, `backend/.env.example`, `backend/.env`
- Create: `.gitignore`

- [ ] **Step 1: Initialize git and create folder structure**

```bash
cd /Users/vaishakh/Code/personal/voice-live
git init
mkdir -p backend/app/{config,core,services,transport,api}
touch backend/app/__init__.py backend/app/config/__init__.py backend/app/core/__init__.py
touch backend/app/services/__init__.py backend/app/transport/__init__.py backend/app/api/__init__.py
```

- [ ] **Step 2: Create .gitignore**

```gitignore
__pycache__/
*.pyc
.env
node_modules/
.next/
dist/
.DS_Store
venv/
*.egg-info/
```

- [ ] **Step 3: Create backend/requirements.txt**

```
pipecat-ai[google,silero,websocket]>=0.0.105
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-dotenv>=1.0.0
```

- [ ] **Step 4: Create backend/.env.example and backend/.env**

`.env.example`:
```
GOOGLE_API_KEY=your-api-key-here
HOST=0.0.0.0
PORT=8000
GEMINI_MODEL=gemini-3.1-flash-live-preview
GEMINI_VOICE=Charon
```

`.env` (actual):
```
GOOGLE_API_KEY=AIzaSyCxx0hn0NjlWGbjbd6wc5QI60KFPr1y-B8
HOST=0.0.0.0
PORT=8000
GEMINI_MODEL=gemini-3.1-flash-live-preview
GEMINI_VOICE=Charon
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: scaffold project structure"
```

---

### Task 2: Backend Config Module

**Files:**
- Create: `backend/app/config/settings.py`
- Create: `backend/app/config/gemini.py`

- [ ] **Step 1: Create backend/app/config/settings.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str
    host: str = "0.0.0.0"
    port: int = 8000
    gemini_model: str = "gemini-3.1-flash-live-preview"
    gemini_voice: str = "Charon"
    allowed_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 2: Create backend/app/config/gemini.py**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class GeminiConfig:
    model: str
    voice: str
    system_instruction: str = "You are a helpful voice assistant."
    thinking_budget: int = 0

    @classmethod
    def from_settings(cls, settings) -> "GeminiConfig":
        return cls(model=settings.gemini_model, voice=settings.gemini_voice)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/config/
git commit -m "feat: add backend config module with settings and gemini config"
```

---

### Task 3: Backend Services

**Files:**
- Create: `backend/app/services/gemini_service.py`
- Create: `backend/app/services/vad_service.py`

- [ ] **Step 1: Create backend/app/services/gemini_service.py**

```python
from google.genai.types import ThinkingConfig
from pipecat.services.google.gemini_live import GeminiLiveLLMService

from app.config.gemini import GeminiConfig


def create_gemini_service(api_key: str, config: GeminiConfig) -> GeminiLiveLLMService:
    """Factory function to create a configured GeminiLiveLLMService."""
    return GeminiLiveLLMService(
        api_key=api_key,
        settings=GeminiLiveLLMService.Settings(
            model=config.model,
            voice=config.voice,
            thinking=ThinkingConfig(thinking_budget=config.thinking_budget),
        ),
        system_instruction=config.system_instruction,
    )
```

- [ ] **Step 2: Create backend/app/services/vad_service.py**

```python
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams


def create_vad_analyzer(
    confidence: float = 0.7,
    start_secs: float = 0.2,
    stop_secs: float = 0.2,
) -> SileroVADAnalyzer:
    """Factory function to create a configured SileroVADAnalyzer."""
    return SileroVADAnalyzer(
        params=VADParams(
            confidence=confidence,
            start_secs=start_secs,
            stop_secs=stop_secs,
        ),
    )
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/
git commit -m "feat: add gemini and vad service factories"
```

---

### Task 4: Backend Pipeline Factory & Session Manager

**Files:**
- Create: `backend/app/core/pipeline_factory.py`
- Create: `backend/app/core/session_manager.py`
- Create: `backend/app/core/events.py`

- [ ] **Step 1: Create backend/app/core/events.py**

```python
from enum import Enum


class SessionState(str, Enum):
    CONNECTING = "connecting"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
```

- [ ] **Step 2: Create backend/app/core/pipeline_factory.py**

```python
from loguru import logger
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.transports.base_transport import BaseTransport

from app.config.gemini import GeminiConfig
from app.config.settings import Settings
from app.services.gemini_service import create_gemini_service
from app.services.vad_service import create_vad_analyzer


class PipelineFactory:
    """Creates configured Pipecat pipelines for voice sessions."""

    @staticmethod
    def create(
        transport: BaseTransport,
        settings: Settings,
        gemini_config: GeminiConfig | None = None,
    ) -> PipelineTask:
        if gemini_config is None:
            gemini_config = GeminiConfig.from_settings(settings)

        llm = create_gemini_service(settings.google_api_key, gemini_config)
        vad = create_vad_analyzer()

        context = LLMContext()
        user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
            context,
            user_params=LLMUserAggregatorParams(vad_analyzer=vad),
        )

        pipeline = Pipeline(
            [
                transport.input(),
                user_aggregator,
                llm,
                transport.output(),
                assistant_aggregator,
            ]
        )

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )

        logger.info(f"Pipeline created with model={gemini_config.model}")
        return task
```

- [ ] **Step 3: Create backend/app/core/session_manager.py**

```python
import asyncio
from uuid import uuid4

from loguru import logger
from pipecat.pipeline.task import PipelineTask

from app.core.events import SessionState


class Session:
    def __init__(self, session_id: str, task: PipelineTask):
        self.session_id = session_id
        self.task = task
        self.state = SessionState.CONNECTING


class SessionManager:
    """Tracks active voice sessions with cleanup."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self, task: PipelineTask) -> Session:
        session_id = str(uuid4())
        session = Session(session_id, task)
        self._sessions[session_id] = session
        logger.info(f"Session created: {session_id}")
        return session

    async def remove_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session and session.task:
            try:
                await session.task.cancel()
            except Exception as e:
                logger.warning(f"Error cancelling session {session_id}: {e}")
        logger.info(f"Session removed: {session_id}")

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    async def cleanup_all(self) -> None:
        tasks = [self.remove_session(sid) for sid in list(self._sessions)]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All sessions cleaned up")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/
git commit -m "feat: add pipeline factory and session manager"
```

---

### Task 5: Backend API & Main App

**Files:**
- Create: `backend/app/transport/websocket_transport.py`
- Create: `backend/app/api/routes.py`
- Create: `backend/app/api/ws.py`
- Create: `backend/app/main.py`
- Create: `backend/run.py`

- [ ] **Step 1: Create backend/app/transport/websocket_transport.py**

```python
from fastapi import WebSocket
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)


def create_websocket_transport(websocket: WebSocket) -> FastAPIWebsocketTransport:
    """Factory to create a Pipecat WebSocket transport from a FastAPI WebSocket."""
    return FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=ProtobufFrameSerializer(),
        ),
    )
```

- [ ] **Step 2: Create backend/app/api/routes.py**

```python
from fastapi import APIRouter

from app.config.settings import settings
from app.core.session_manager import SessionManager

router = APIRouter()


def create_router(session_manager: SessionManager) -> APIRouter:
    @router.get("/health")
    async def health():
        return {
            "status": "ok",
            "active_sessions": session_manager.active_count,
        }

    @router.get("/config")
    async def config():
        return {
            "model": settings.gemini_model,
            "voice": settings.gemini_voice,
        }

    return router
```

- [ ] **Step 3: Create backend/app/api/ws.py**

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.runner import PipelineRunner

from app.config.settings import Settings
from app.core.pipeline_factory import PipelineFactory
from app.core.session_manager import SessionManager
from app.transport.websocket_transport import create_websocket_transport

ws_router = APIRouter()


def create_ws_router(
    session_manager: SessionManager,
    settings: Settings,
) -> APIRouter:
    @ws_router.websocket("/ws/{session_id}")
    async def websocket_voice(websocket: WebSocket, session_id: str):
        await websocket.accept()
        logger.info(f"WebSocket connected: {session_id}")

        transport = create_websocket_transport(websocket)
        task = PipelineFactory.create(transport, settings)
        session = session_manager.create_session(task)

        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            logger.info(f"Client connected to session {session.session_id}")
            session.state = "active"
            await task.queue_frames([LLMRunFrame()])

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            logger.info(f"Client disconnected from session {session.session_id}")
            await task.cancel()

        try:
            runner = PipelineRunner(handle_sigint=False)
            await runner.run(task)
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Pipeline error in session {session_id}: {e}")
        finally:
            await session_manager.remove_session(session.session_id)

    return ws_router
```

- [ ] **Step 4: Create backend/app/main.py**

```python
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import create_router
from app.api.ws import create_ws_router
from app.config.settings import settings
from app.core.session_manager import SessionManager

session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting voice assistant server")
    yield
    logger.info("Shutting down — cleaning up sessions")
    await session_manager.cleanup_all()


app = FastAPI(title="Gemini Voice Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(create_router(session_manager))
app.include_router(create_ws_router(session_manager, settings))


@app.post("/connect")
async def connect():
    """RTVI client calls this to get a WebSocket URL."""
    session_id = str(uuid4())
    return {"url": f"ws://localhost:{settings.port}/ws/{session_id}"}
```

- [ ] **Step 5: Create backend/run.py**

```python
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from app.config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
```

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add backend API, WebSocket handler, and main app"
```

---

### Task 6: Frontend Scaffolding

**Files:**
- Create: Next.js project in `frontend/`
- Modify: `frontend/tailwind.config.ts`
- Create: `frontend/src/app/globals.css`
- Create: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Create Next.js project**

```bash
cd /Users/vaishakh/Code/personal/voice-live
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias --use-npm
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install @pipecat-ai/client-js @pipecat-ai/client-react @pipecat-ai/websocket-transport
```

- [ ] **Step 3: Update frontend/tailwind.config.ts**

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      colors: {
        accent: {
          DEFAULT: "#6366F1",
          glow: "#818CF8",
          light: "#C7D2FE",
        },
      },
      animation: {
        "breathe": "breathe 4s ease-in-out infinite",
        "ripple": "ripple 2s ease-out infinite",
        "morph": "morph 3s ease-in-out infinite",
        "spin-slow": "spin 3s linear infinite",
        "fade-in": "fadeIn 0.4s ease-out",
      },
      keyframes: {
        breathe: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.8" },
          "50%": { transform: "scale(1.05)", opacity: "1" },
        },
        ripple: {
          "0%": { transform: "scale(1)", opacity: "0.6" },
          "100%": { transform: "scale(1.8)", opacity: "0" },
        },
        morph: {
          "0%, 100%": { borderRadius: "60% 40% 30% 70% / 60% 30% 70% 40%" },
          "50%": { borderRadius: "30% 60% 70% 40% / 50% 60% 30% 60%" },
        },
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 4: Write frontend/src/app/globals.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg: #FFFFFF;
  --bg-subtle: #FAFAFA;
  --text: #09090B;
  --text-muted: #71717A;
  --border: #E4E4E7;
  --accent: #6366F1;
  --accent-glow: #818CF8;
  --accent-light: #C7D2FE;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-inter), system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Orb glow layers */
.orb-glow {
  box-shadow:
    0 0 60px rgba(99, 102, 241, 0.15),
    0 0 120px rgba(99, 102, 241, 0.08);
}

.orb-glow-active {
  box-shadow:
    0 0 40px rgba(99, 102, 241, 0.3),
    0 0 80px rgba(129, 140, 248, 0.2),
    0 0 160px rgba(99, 102, 241, 0.1);
}

.orb-glow-speaking {
  box-shadow:
    0 0 30px rgba(99, 102, 241, 0.4),
    0 0 60px rgba(139, 92, 246, 0.3),
    0 0 120px rgba(99, 102, 241, 0.15);
}
```

- [ ] **Step 5: Write frontend/src/app/layout.tsx**

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Voice Assistant",
  description: "Real-time voice assistant powered by Gemini",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Next.js frontend with Tailwind and Inter font"
```

---

### Task 7: Frontend Types, Constants & RTVI Provider

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/lib/constants.ts`
- Create: `frontend/src/providers/RTVIProvider.tsx`
- Create: `frontend/src/hooks/useVoiceState.ts`

- [ ] **Step 1: Create frontend/src/types/index.ts**

```typescript
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
```

- [ ] **Step 2: Create frontend/src/lib/constants.ts**

```typescript
import type { SessionConfig } from "@/types";

export const SESSION_CONFIG: SessionConfig = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  connectEndpoint: "/connect",
};

export const AUDIO_SAMPLE_RATE = 16000;
```

- [ ] **Step 3: Create frontend/src/providers/RTVIProvider.tsx**

```tsx
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
```

- [ ] **Step 4: Create frontend/src/hooks/useVoiceState.ts**

```typescript
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
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/ frontend/src/lib/ frontend/src/providers/ frontend/src/hooks/
git commit -m "feat: add RTVI provider, voice state hook, types and constants"
```

---

### Task 8: Frontend Orb Component

**Files:**
- Create: `frontend/src/components/voice-chat/Orb.tsx`

- [ ] **Step 1: Create the Orb component**

```tsx
"use client";

import { VoiceState } from "@/types";

interface OrbProps {
  state: VoiceState;
}

const stateStyles: Record<VoiceState, string> = {
  [VoiceState.IDLE]:
    "animate-breathe orb-glow bg-gradient-to-br from-accent/20 to-accent-light/30",
  [VoiceState.CONNECTING]:
    "animate-spin-slow orb-glow bg-gradient-to-br from-accent/30 to-accent-glow/20",
  [VoiceState.LISTENING]:
    "animate-breathe orb-glow-active bg-gradient-to-br from-accent/40 to-accent-glow/30",
  [VoiceState.SPEAKING]:
    "animate-morph orb-glow-speaking bg-gradient-to-br from-accent to-purple-500/80",
  [VoiceState.ERROR]:
    "orb-glow bg-gradient-to-br from-red-400/30 to-red-500/20",
};

export default function Orb({ state }: OrbProps) {
  return (
    <div className="relative flex items-center justify-center w-48 h-48">
      {/* Ripple rings (visible when listening) */}
      {state === VoiceState.LISTENING && (
        <>
          <div className="absolute inset-0 rounded-full bg-accent/10 animate-ripple" />
          <div
            className="absolute inset-0 rounded-full bg-accent/5 animate-ripple"
            style={{ animationDelay: "0.5s" }}
          />
        </>
      )}

      {/* Main orb */}
      <div
        className={[
          "w-32 h-32 rounded-full transition-all duration-600 ease-out",
          stateStyles[state],
        ].join(" ")}
      />

      {/* Center dot */}
      <div
        className={[
          "absolute w-3 h-3 rounded-full transition-all duration-300",
          state === VoiceState.SPEAKING
            ? "bg-white/90 scale-110"
            : state === VoiceState.LISTENING
              ? "bg-accent/80"
              : "bg-accent/40",
        ].join(" ")}
      />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/voice-chat/Orb.tsx
git commit -m "feat: add animated orb component with state-driven visuals"
```

---

### Task 9: Frontend Control Components

**Files:**
- Create: `frontend/src/components/voice-chat/ControlButton.tsx`
- Create: `frontend/src/components/voice-chat/StatusLabel.tsx`
- Create: `frontend/src/components/voice-chat/WaveformBar.tsx`

- [ ] **Step 1: Create ControlButton**

```tsx
"use client";

interface ControlButtonProps {
  isConnected: boolean;
  isConnecting: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
}

export default function ControlButton({
  isConnected,
  isConnecting,
  onConnect,
  onDisconnect,
}: ControlButtonProps) {
  if (isConnecting) {
    return (
      <button
        disabled
        className="px-8 py-3 rounded-full text-[15px] font-medium
          border border-zinc-200 text-zinc-400 cursor-not-allowed
          transition-all duration-200"
      >
        Connecting...
      </button>
    );
  }

  if (isConnected) {
    return (
      <button
        onClick={onDisconnect}
        className="px-8 py-3 rounded-full text-[15px] font-medium
          border border-zinc-200 text-zinc-600
          hover:border-zinc-300 hover:text-zinc-800
          hover:scale-[1.02] hover:shadow-sm
          active:scale-[0.98]
          transition-all duration-200"
      >
        End
      </button>
    );
  }

  return (
    <button
      onClick={onConnect}
      className="px-8 py-3 rounded-full text-[15px] font-medium
        bg-accent text-white
        hover:bg-accent/90 hover:scale-[1.02] hover:shadow-lg hover:shadow-accent/20
        active:scale-[0.98]
        transition-all duration-200"
    >
      Start Conversation
    </button>
  );
}
```

- [ ] **Step 2: Create StatusLabel**

```tsx
"use client";

import { VoiceState } from "@/types";

interface StatusLabelProps {
  state: VoiceState;
  error?: string | null;
}

const stateLabels: Record<VoiceState, string> = {
  [VoiceState.IDLE]: "Ready to talk",
  [VoiceState.CONNECTING]: "Connecting...",
  [VoiceState.LISTENING]: "Listening to you...",
  [VoiceState.SPEAKING]: "Speaking...",
  [VoiceState.ERROR]: "Something went wrong",
};

export default function StatusLabel({ state, error }: StatusLabelProps) {
  const label = error && state === VoiceState.ERROR ? error : stateLabels[state];

  return (
    <p
      key={label}
      className="text-[13px] text-zinc-500 h-5 animate-fade-in"
    >
      {label}
    </p>
  );
}
```

- [ ] **Step 3: Create WaveformBar**

```tsx
"use client";

import { VoiceState } from "@/types";

interface WaveformBarProps {
  state: VoiceState;
}

export default function WaveformBar({ state }: WaveformBarProps) {
  const isActive =
    state === VoiceState.LISTENING || state === VoiceState.SPEAKING;

  return (
    <div className="flex items-center justify-center gap-[3px] h-6">
      {Array.from({ length: 24 }).map((_, i) => (
        <div
          key={i}
          className={[
            "w-[2px] rounded-full transition-all duration-300",
            isActive ? "bg-accent/40" : "bg-zinc-200",
          ].join(" ")}
          style={{
            height: isActive
              ? `${4 + Math.sin((i * Math.PI) / 6) * 12 + Math.random() * 4}px`
              : "3px",
            transitionDelay: `${i * 20}ms`,
          }}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/voice-chat/
git commit -m "feat: add control button, status label, and waveform bar components"
```

---

### Task 10: Frontend VoiceChat & Page

**Files:**
- Create: `frontend/src/components/voice-chat/VoiceChat.tsx`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Create VoiceChat orchestrator**

```tsx
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
```

- [ ] **Step 2: Write frontend/src/app/page.tsx**

```tsx
import VoiceProvider from "@/providers/RTVIProvider";
import VoiceChat from "@/components/voice-chat/VoiceChat";

export default function Home() {
  return (
    <VoiceProvider>
      <VoiceChat />
    </VoiceProvider>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add VoiceChat orchestrator and main page"
```

---

### Task 11: Integration Verification

- [ ] **Step 1: Install backend dependencies**

```bash
cd /Users/vaishakh/Code/personal/voice-live/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 2: Verify backend starts**

```bash
cd /Users/vaishakh/Code/personal/voice-live/backend
python run.py
# Expected: Uvicorn running on http://0.0.0.0:8000
# Health check: curl http://localhost:8000/health → {"status":"ok","active_sessions":0}
```

- [ ] **Step 3: Verify frontend builds**

```bash
cd /Users/vaishakh/Code/personal/voice-live/frontend
npm run build
# Expected: Build succeeds
```

- [ ] **Step 4: Run frontend dev**

```bash
npm run dev
# Expected: Next.js running on http://localhost:3000
# Open browser → see Voice Assistant card with orb
```

- [ ] **Step 5: End-to-end test**

1. Start backend: `cd backend && python run.py`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:3000
4. Click "Start Conversation" → orb animates to connecting → listening
5. Speak → orb reacts → Gemini responds with audio
6. Click "End" → returns to idle

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete Gemini voice assistant with Pipecat pipeline"
```
