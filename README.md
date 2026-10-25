<div align="center">

# ⚡ Instagram Reel Counter & DM Radar

**The local-first terminal engine to settle who spams more reels, audit late-night streaks, and read DMs in total stealth.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Storage](https://img.shields.io/badge/Cloud_Servers-ZERO-00C853?style=for-the-badge)](https://github.com/prashanth-karanam/instagram-reel-counter)
[![Privacy](https://img.shields.io/badge/Privacy-100%25_Local-blueviolet?style=for-the-badge)](https://github.com/prashanth-karanam/instagram-reel-counter)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<br/>

```text
╭───────────────── 🎬 REEL COUNTER SCORECARD ─────────────────╮
│ Chat: @best_friend                                          │
│ Total Reels Exchanged: 1,482                                │
│                                                             │
│ You Sent:    918 (62.0%)  [████████████░░░░░░░░]            │
│ They Sent:   564 (38.0%)  [████████░░░░░░░░░░░░]            │
│                                                             │
│ Verdict: You are carrying this friendship.                  │
╰─────────────────────────────────────────────────────────────╯
```

</div>

---

### ⚡ 1-Line Quick Install

Paste this into your terminal to install dependencies, fetch the project, and launch instantly:

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/prashanth-karanam/instagram-reel-counter/main/install.ps1 | iex
```

**macOS / Linux (Bash):**
```bash
curl -sSL https://raw.githubusercontent.com/prashanth-karanam/instagram-reel-counter/main/install.sh | bash
```

*(No Git required. The installer auto-extracts and runs on Python 3.10+).*

---

### Settle The Debate Once And For All

We all have that one friend where 90% of the conversation is just sending Instagram Reels back and forth. 

Yet Instagram never tells you what is actually going on:

* **Who is really sending more reels?** Are you spamming them, or are they spamming you?
* **What are your peak hours?** What ungodly time of night are you two trading clips?
* **Did they actually miss your message?** Or did they open five other chats and broadcast reels while leaving yours on "Delivered"?

Most online Instagram counters make you type your password into a random website that routes your session through sketchy cloud servers. 

**This tool runs 100% locally on your computer.** It talks straight to Instagram's official endpoints, stores your session on your own hard drive, and never sends a single byte to any middleman.

---

### What You Can Do

#### 1. ⚡ The Reel Scorecard
Pulls your conversation history and calculates the exact split. You get total reel counts, percentages, visual balance bars, and an indisputable verdict on who carries the chat.

#### 2. 🌙 The 3 AM Heatmap
Maps the timestamps of every shared reel onto a 24-hour visual activity clock to show your peak sharing habits.

#### 3. 🏆 The Inbox Leaderboard
Scans your top direct message conversations in parallel and builds a ranked leaderboard of who shares the most content with you.

#### 4. 👻 Ghost Mode Reader
Browse full DM transcripts and open reel links without dispatching read receipts. On the sender's phone, your status stays at "Delivered" with their unread badge intact.

#### 5. 🛰️ The Ignored Radar
Cross-references outgoing timestamps with your friend's read receipts to verify when they were last active or chatting elsewhere while leaving your message unread.

---

### Terminal Preview

```text
🔥 Peak Reel Sharing Hour: 01:00 - 02:00

Hour Range       Reels Count   Activity Bar
──────────────────────────────────────────
21:00 - 22:00    42            ████░░░░░░░░░░░░
22:00 - 23:00    89            ████████░░░░░░░░
23:00 - 00:00    134           ████████████░░░░
00:00 - 01:00    186           ████████████████
01:00 - 02:00    210           ████████████████
```

---

### How It Works Under The Hood

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        DIRECT LOCAL PIPELINE                           │
│                                                                        │
│   [ Local Terminal ] ──( Direct WinSock HTTPS )──> [ Meta Endpoints ]  │
│          │                                                             │
│          └──> [ Local Session File: ~/.ig_toolkit/session.json ]       │
│                                                                        │
│   Zero Cloud Relays  •  Zero Telemetry  •  Read-Only GET Mutations     │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Local Sandbox:** Sessions are saved directly to `~/.ig_toolkit/session.json`. You log in once, and passwords are never cached in plain text.
2. **WinSock Transport Adapter:** Bypasses the known `curl_cffi` DNS crash bugs on Windows by utilizing native sockets with a 250ms rate-limit buffer.
3. **No Seen Mutations:** Queries use read-only GET endpoints to prevent triggering Meta's `seen/` receipts.

---

### Manual Setup

If you prefer to clone and run manually:

```bash
git clone https://github.com/prashanth-karanam/instagram-reel-counter.git
cd instagram-reel-counter
pip install -r requirements.txt
python app.py
```

On Windows, you can also double-click `run.bat`.

To switch accounts or purge your local session, choose option 5 in the menu or delete `~/.ig_toolkit/session.json`.

---

<div align="center">

Built for private, local-first Instagram telemetry.  
Distributed under the [MIT License](LICENSE).

</div>
