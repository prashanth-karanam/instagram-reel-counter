# Instagram Reel Counter & Local Telemetry Toolkit

A high-performance, local-first terminal engine designed to analyze Instagram Direct message activity, calculate bidirectional Reel exchange metrics, and inspect conversation streams without dispatching read receipts.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SYSTEM ARCHITECTURE                             │
│                                                                        │
│   [ Local Terminal ] ──( Direct WinSock HTTPS )──> [ Meta Endpoints ]  │
│          │                                                             │
│          └──> [ Encrypted Local Session: ~/.ig_toolkit/session.json ]  │
│                                                                        │
│   100% Client-Side  |  Zero Cloud Relay  |  No Read-Receipt Mutation   │
└────────────────────────────────────────────────────────────────────────┘
```

### Engineering Principles

1. Local-First Security Model
All credentials, session tokens, and cached metadata remain strictly inside the host machine at `~/.ig_toolkit/session.json`. Network calls interface directly with Instagram endpoints without intermediary proxies or telemetry collection.

2. Ghost-Mode Protocol
Standard Instagram mobile and web applications trigger a `direct_v2/threads/{id}/items/{id}/seen/` mutation whenever a conversation is loaded. This engine issues read-only queries against `direct_v2/threads/{id}/`, allowing complete transcript inspection while preserving unread states.

3. Resilient Transport Layer
Windows environments frequently encounter host resolution failures when invoking libcurl bindings via `curl_cffi`. The client forces a dedicated WinSock `requests` transport adapter with exponential backoff and controlled batch pacing (250ms delay) to prevent automated request throttling.

4. Precise Media Classification
Reel extraction relies on strict URI path matching (`/reel/`, `/reels/`) and cross-app media attribute parsing (`xma_clip`, `clips_metadata`, `felix_share`). Static photo posts, carousels, and stories are filtered out during stream ingestion.

### Capabilities

1. Bidirectional Reel Analytics
Computes sent versus received totals across any thread with visual percentage distribution bars, sharing ratios, and a 24-hour diurnal activity heatmap.

2. Parallel Inbox Ranking
Scans active threads to build a leaderboard of top reel exchange partners.

3. Read Receipt Telemetry
Cross-references outgoing delivery timestamps with participant receipt cursors to verify whether messages have been opened.

### Technical Specifications

```
Runtime:         Python 3.10+
Transport:       Native WinSock Requests (HTTPS / TLS 1.3)
Rate Pacing:     250ms batch intervals
Session Storage: Local JSON (Home Directory Sandbox)
Interface:       Rich Terminal Engine (UTF-8 ANSI)
License:         MIT
```

### Setup & Execution

Install dependencies:
```bash
pip install instagrapi rich requests
```

Windows Launcher:
```cmd
run.bat
```

Manual Execution:
```bash
python app.py
```

### Session Lifecycle

Saved sessions automatically authenticate subsequent runs without requiring re-entry of credentials. Sessions can be purged at any time by selecting option 5 in the menu or removing `~/.ig_toolkit/session.json`.
