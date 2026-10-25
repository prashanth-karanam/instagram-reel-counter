# Instagram Reel Counter

A fast local CLI tool to count shared Instagram Reels, inspect DM activity, and view messages in ghost mode without triggering seen receipts.

### Privacy

All credentials and session tokens stay on your local disk at `~/.ig_toolkit/session.json`.
The application connects directly to Instagram API endpoints.
No intermediate proxy, no cloud database, no tracking telemetry.

### Features

1. Fast Reel Counter
Calculates reels sent versus received for any conversation with percentage balance bars and peak activity hours.

2. Inbox Leaderboard
Scans active threads to rank top reel exchange partners.

3. Ghost Mode DM Reader
Reads messages and reel links via read-only endpoints without sending seen receipts.

4. Read Receipt Monitor
Checks delivery timestamps against friend read receipts to detect unread messages.

### Installation

Requires Python 3.10 or higher.

Install dependencies:
```bash
pip install instagrapi rich requests
```

### Usage

Windows:
Run `run.bat` or launch via terminal:
```bash
python app.py
```

Linux or macOS:
```bash
python3 app.py
```

Follow the on-screen prompts. To clear saved sessions, choose option 5 from the main menu or delete `~/.ig_toolkit/session.json`.
