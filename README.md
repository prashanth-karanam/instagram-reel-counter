# Instagram Reel Counter

A local-first terminal engine to audit your Instagram DM habits, calculate who spams more Reels, and inspect conversations in ghost mode without triggering seen receipts.

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

### Why This Exists

We all have friends where 90% of the conversation is just sharing Instagram Reels. Yet Instagram gives you zero data on how you actually interact.

You never get clear answers to the questions you actually wonder about:

1. Who is really carrying the conversation and sending more reels?
2. What ungodly hours of the night are you both trading clips?
3. Did your friend genuinely miss your message, or were they active in five other chats while leaving yours on delivered?

Most third-party Instagram tools online are sketchy web apps that demand your password, route your traffic through unknown cloud servers, and risk account checkpoints.

We built this tool to be the exact opposite. It runs 100% locally on your machine, talks directly to Instagram's official API, and never sends your data anywhere.

### What It Does

1. The Reel Scorecard
Scans your chat history and gives you the exact numbers. You get the total reel count, sent versus received ratio, percentage bars, and a verdict on who spams more.

2. Peak Activity Heatmap
Analyzes the timestamps of every shared reel across a 24-hour clock to show your peak sharing hours and late-night habits.

3. Inbox Leaderboard
Scans your active conversations in parallel and ranks your top friends by total reel volume.

4. 100% Ghost Mode Reader
Lets you read conversation transcripts and grab direct links to shared reels without triggering "Seen" receipts. On the sender's phone, your status stays as "Delivered".

5. Delivery and Activity Telemetry
Checks outgoing message timestamps against your friend's read cursors to detect when someone is active elsewhere while leaving your chat unread.

### Privacy and Security Model

1. Local Credentials
Your login credentials and session cookies are stored strictly in your own operating system user directory at `~/.ig_toolkit/session.json`.

2. Direct Connection
Network traffic travels directly between your machine and Meta's servers over TLS 1.3. No middleman servers, no proxy relays, and zero telemetry tracking.

3. Windows Socket Stability
Forces a dedicated WinSock requests transport with 250ms batch pacing to eliminate the common DNS resolution crashes caused by libcurl on Windows.

### Technical Specifications

```
Runtime:         Python 3.10+
Transport:       Native WinSock Requests (HTTPS / TLS 1.3)
Batch Pacing:    250ms rate limit buffer
Session Path:    ~/.ig_toolkit/session.json
Interface:       Rich Terminal Engine (UTF-8 ANSI)
License:         MIT
```

### Setup and Running

Install dependencies:
```bash
pip install instagrapi rich requests
```

Windows:
Double-click `run.bat` or run:
```cmd
python app.py
```

Linux or macOS:
```bash
python3 app.py
```

To switch accounts or clear saved credentials, select option 5 in the menu or delete `~/.ig_toolkit/session.json`.
