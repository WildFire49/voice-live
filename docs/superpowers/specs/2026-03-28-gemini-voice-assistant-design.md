# Gemini 3.1 Flash Live Voice Assistant — Design Spec

## Overview

A real-time voice assistant using Google Gemini 3.1 Flash Live Preview with continuous conversation. FastAPI + Pipecat backend, Next.js frontend. Modular pipeline architecture with factory pattern.

## System Architecture

```
Browser (Next.js) <--WebSocket--> FastAPI <--Pipeline--> Pipecat <--API--> Gemini Live
```

- **Frontend:** Next.js captures mic audio via AudioWorklet, sends PCM over WebSocket, plays received audio via AudioContext
- **Backend:** FastAPI serves WebSocket endpoint. Pipecat pipeline handles VAD + Gemini Live API
- **Audio format:** PCM Int16 — **16kHz input (mic), 24kHz output (Gemini response)**. Gemini Live API has asymmetric sample rates.

## Development Setup

- Next.js dev server on `:3000`, FastAPI on `:8000`
- CORS configured to allow `localhost:3000` in dev
- Both started independently (`npm run dev` / `python run.py`)

## Data Flow

1. User clicks "Start Conversation"
2. Frontend opens WebSocket to `/ws/voice`
3. Backend creates Pipecat pipeline via `PipelineFactory`
4. Frontend AudioWorklet captures mic → PCM Int16 16kHz chunks → binary WS frames
5. Pipecat pipeline: Silero VAD detects speech → notifies frontend of speech state → all audio flows to Gemini → Gemini returns 24kHz audio
6. Audio response → binary WS frames → AudioContext playback at 24kHz
7. Continuous until user clicks "End"

## VAD Strategy

Two VAD layers with distinct roles:
- **Silero VAD (local, in Pipecat pipeline):** Detects user speech start/stop for UI feedback (`vad` events to frontend). Provides responsive orb animation. Runs before audio reaches Gemini.
- **Gemini Server VAD (remote):** Handles turn-taking and interruption detection server-side. This is the source of truth for conversation flow boundaries.

Both coexist: Silero drives the UI, Gemini drives the conversation turns.

## WebSocket Protocol

### Client to Server
- Text: `{ type: "start_session" }` / `{ type: "stop_session" }`
- Binary: Raw PCM Int16 audio frames @ 16kHz mono

### Server to Client
- Text: `{ type: "session_started", sessionId }` / `{ type: "session_stopped" }`
- Text: `{ type: "vad", speaking: boolean }` — user speech state (from Silero)
- Text: `{ type: "bot_state", state: "speaking" | "idle" }` — AI state
- Text: `{ type: "error", message }` — error messages
- Binary: Raw PCM Int16 audio frames @ **24kHz** mono (Gemini response)

## Error Handling

- **WebSocket disconnect:** Frontend shows "Connection lost" status, does not auto-reconnect. User clicks "Start" again.
- **Pipeline error:** Backend catches exceptions, sends `{ type: "error" }` to client, tears down session.
- **Session cleanup:** `SessionManager` runs cleanup on WebSocket close — stops pipeline, removes session from tracking.

## Backend Design

### Folder Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app, CORS, lifespan
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py              # Pydantic BaseSettings (env vars)
│   │   └── gemini.py                # Model name, session config
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pipeline_factory.py      # Creates Pipecat pipelines
│   │   ├── session_manager.py       # Tracks active sessions
│   │   └── events.py                # Event enums + dataclasses
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_service.py        # GeminiLiveLLMService wrapper
│   │   ├── vad_service.py           # Silero VAD config factory
│   │   └── audio_processor.py       # PCM format utils
│   ├── transport/
│   │   ├── __init__.py
│   │   └── websocket_transport.py   # FastAPI WS <-> Pipecat adapter
│   └── api/
│       ├── __init__.py
│       ├── routes.py                # GET /health, GET /config
│       └── ws.py                    # WS /ws/voice handler
├── requirements.txt
├── .env.example
└── run.py
```

### Transport Approach

Uses Pipecat's `FastAPIWebsocketTransport` with a custom `FrameSerializer` that:
- Deserializes incoming binary frames as `AudioRawFrame` (PCM Int16 16kHz)
- Serializes outgoing `AudioRawFrame` as raw PCM binary (24kHz)
- Routes JSON text frames to/from control messages
- Maps Pipecat internal frames (`UserStartedSpeakingFrame`, `BotStartedSpeakingFrame`) to our JSON protocol

### Pipeline Factory Pattern
```
PipelineFactory.create(transport, config)
    ├── transport.input()
    ├── context_aggregator.user()     ← conversation context
    ├── SileroVADAnalyzer(config)     ← local VAD for UI
    ├── GeminiLiveLLMService(config)  ← Gemini Live API
    ├── transport.output()
    └── context_aggregator.assistant() ← response context
```

Uses `GeminiLiveContextAggregatorPair` for conversation context management. Each processor is plug-and-play.

### Key Classes
- `Settings`: Pydantic BaseSettings — API key, host, port from env
- `GeminiConfig`: Model name, response modalities, system instruction, thinking config
- `PipelineFactory`: Static `create()` method builds a configured pipeline
- `SessionManager`: Dict-based tracker, creates/destroys sessions, async cleanup on disconnect
- `GeminiService`: Wraps Pipecat's `GeminiLiveLLMService` with our config
- `VADService`: Factory for Silero VAD with tuned parameters

## Frontend Design

### Folder Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   └── voice-chat/
│   │       ├── VoiceChat.tsx
│   │       ├── Orb.tsx
│   │       ├── ControlButton.tsx
│   │       ├── StatusLabel.tsx
│   │       └── WaveformBar.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── useAudioCapture.ts
│   │   ├── useAudioPlayback.ts
│   │   └── useVoiceSession.ts
│   ├── services/
│   │   ├── AudioService.ts
│   │   └── WebSocketService.ts
│   ├── types/
│   │   └── index.ts
│   └── lib/
│       └── constants.ts
├── public/
│   └── worklet/
│       └── audio-capture.js
├── package.json
├── next.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

### Audio Playback Approach

Playback uses `AudioBufferSourceNode` queuing (not a worklet). The `useAudioPlayback` hook:
1. Receives PCM Int16 binary frames
2. Converts to Float32 AudioBuffer at 24kHz sample rate
3. Queues buffers and schedules them sequentially via `AudioBufferSourceNode.start(time)`
4. Manages gap-free playback with a scheduling buffer

### UI/UX Design

**Design language:** Minimal premium. Linear meets Vercel aesthetic.

**Color palette:**
- Background: `#FFFFFF`
- Subtle bg: `#FAFAFA`
- Text: `#09090B` (zinc-950)
- Muted text: `#71717A` (zinc-500)
- Border: `#E4E4E7` (zinc-200)
- Accent: `#6366F1` (indigo-500)
- Accent glow: `#818CF8` (indigo-400)

**Typography:** Inter font. Three levels:
- Heading: 20px / 600 weight
- Body: 15px / 400 weight
- Caption: 13px / 400 / muted

**Layout:** Single centered card with orb, status label, and one button. Nothing else.

### The Orb (centerpiece)

| State | Animation |
|-------|-----------|
| Idle | Slow breathing pulse, soft indigo glow |
| Listening | Ripple rings expand, orb scales with mic volume |
| AI Speaking | Fluid morphing blob, gradient shift indigo to violet, amplitude-reactive |
| Connecting | Gentle spin with fade-in |

Implemented with CSS animations + radial-gradient + box-shadow layers.

### Micro-interactions
- Button hover: scale(1.02) + shadow lift, 200ms ease
- State transitions: 400ms crossfade
- Orb state changes: 600ms spring transition
- Card: subtle backdrop-filter blur at edges

### Hooks Architecture
- `useWebSocket`: Connect/disconnect/send, handles binary + text frames
- `useAudioCapture`: getUserMedia → AudioWorklet → PCM Int16 16kHz chunks
- `useAudioPlayback`: Receives PCM Int16 → converts to Float32 → queues AudioBufferSourceNode at 24kHz
- `useVoiceSession`: Orchestrates all three hooks, exposes session state

## Gemini Configuration

```python
model = "gemini-3.1-flash-live-preview"
config = {
    "response_modalities": ["AUDIO"],
    "system_instruction": {
        "parts": [{"text": "You are a helpful voice assistant."}]
    },
    "thinking_config": {"thinking_level": "MINIMAL"}
}
```

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Pipecat (`pipecat-ai[google,silero]`), uvicorn
- **Frontend:** Next.js 14+, TypeScript, Tailwind CSS, Inter font
- **Audio:** Web Audio API (AudioWorklet for capture, AudioBufferSourceNode for playback)
- **VAD:** Silero VAD via Pipecat (UI feedback) + Gemini server VAD (turn-taking)
- **LLM:** Gemini 3.1 Flash Live Preview via Pipecat's `GeminiLiveLLMService`

## Constraints

- No file exceeds ~500 lines
- Every module has a single responsibility
- Factory pattern for pipeline creation
- All config from environment variables (no hardcoded keys)
