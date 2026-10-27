import os
import sys
import io
import time
import json
import datetime
from pathlib import Path
from collections import defaultdict, Counter
from getpass import getpass

# ---------------------------------------------------------
# Windows UTF-8 Terminal Stream Handling
# ---------------------------------------------------------
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    else:
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass

# Dependency verification
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.prompt import Prompt, Confirm
    from rich import box
    from instagrapi import Client
    from instagrapi.exceptions import (
        BadPassword,
        TwoFactorRequired,
        ChallengeRequired,
        ClientError,
        LoginRequired,
        ClientConnectionError
    )
except ImportError:
    print("Missing packages. Run: pip install instagrapi rich requests")
    sys.exit(1)

console = Console()

# ---------------------------------------------------------
# Storage Paths
# ---------------------------------------------------------
TOOLKIT_DIR = Path.home() / ".ig_toolkit"
SESSION_FILE = TOOLKIT_DIR / "session.json"
USER_FILE = TOOLKIT_DIR / "user.txt"
CACHE_DIR = TOOLKIT_DIR / "cache"

TOOLKIT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# Network Client Initialization
# ---------------------------------------------------------
def get_instagram_client() -> Client:
    cl = Client()
    # Enforce native WinSock requests transport to eliminate curl_cffi DNS crash on Windows
    cl.private_transport = "requests"
    cl.public_transport = "requests"
    cl.request_timeout = 0
    return cl


def login_flow():
    cl = get_instagram_client()

    # 1. Existing local session check
    if SESSION_FILE.exists():
        try:
            cl.load_settings(SESSION_FILE)
            cl.request_timeout = 0
            cached_user = USER_FILE.read_text(encoding="utf-8").strip() if USER_FILE.exists() else None
            return cl, cached_user or f"User_{cl.user_id}"
        except LoginRequired:
            console.print("[yellow]Saved session expired. Re-authentication required.[/yellow]")
            SESSION_FILE.unlink(missing_ok=True)
            USER_FILE.unlink(missing_ok=True)
        except Exception as e:
            cached_user = USER_FILE.read_text(encoding="utf-8").strip() if USER_FILE.exists() else None
            return cl, cached_user or f"User_{cl.user_id}"

    # 2. Transparent authentication notice
    console.print(
        Panel.fit(
            "[bold cyan]PRIVACY NOTICE: 100% LOCAL STORAGE[/bold cyan]\n"
            "Your login session is stored strictly on your local machine:\n"
            f"[dim green]{SESSION_FILE}[/dim green]\n"
            "Direct communication with Meta servers. No third-party proxy.",
            border_style="cyan",
            title="Instagram Toolkit",
            padding=(1, 2)
        )
    )

    try:
        username = Prompt.ask("[bold green]Instagram Username[/bold green]").strip()
        password = getpass("Instagram Password (hidden): ").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("\nAborted.")
        sys.exit(0)

    with console.status("[bold cyan]Connecting to Instagram...", spinner="dots"):
        try:
            cl.login(username, password)
        except TwoFactorRequired:
            code = Prompt.ask("[bold yellow]Enter 2FA Code[/bold yellow]").strip()
            cl.two_factor_login(code)
        except BadPassword:
            console.print("[bold red]Incorrect password. Please verify credentials.[/bold red]")
            sys.exit(1)
        except ChallengeRequired:
            console.print("[bold red]Instagram checkpoint triggered. Confirm login in your official mobile app.[/bold red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]Login failed: {e}[/bold red]")
            sys.exit(1)

    cl.request_timeout = 0
    cl.dump_settings(SESSION_FILE)
    try:
        USER_FILE.write_text(username, encoding="utf-8")
    except Exception:
        pass
    console.print(f"[bold green]Connected as @{username}[/bold green]\n")
    return cl, username


def logout_account():
    if Confirm.ask("[bold red]Clear saved session from this machine?[/bold red]"):
        try:
            SESSION_FILE.unlink(missing_ok=True)
            USER_FILE.unlink(missing_ok=True)
            console.print("[bold green]Session cleared.[/bold green]")
        except Exception as e:
            console.print(f"[red]Error removing file: {e}[/red]")
        time.sleep(1)
        sys.exit(0)
        time.sleep(1)
        sys.exit(0)

# ---------------------------------------------------------
# Formatting & Detection Utilities
# ---------------------------------------------------------
def parse_timestamp(ts) -> datetime.datetime:
    try:
        val = float(ts or 0)
        if val <= 0:
            return datetime.datetime.now()
        if val > 1e11:
            val /= 1_000_000
        return datetime.datetime.fromtimestamp(val)
    except Exception:
        return datetime.datetime.now()


def is_reel(item: dict) -> bool:
    itype = str(item.get("item_type", "")).lower()
    if itype in ("clip", "xma_clip", "felix_share"):
        return True
    if itype in ("media_share", "xma_media_share"):
        xma_list = item.get("xma_media_share") or item.get("xma") or []
        if isinstance(xma_list, list) and xma_list:
            x0 = xma_list[0]
            # Detect playable video streams or video codecs in feed shares
            if x0.get("playable_url") or x0.get("video_dash_manifest") or x0.get("video_codec"):
                return True
            target = str(x0.get("target_url", "")).lower()
            if "/reel/" in target or "/reels/" in target or "clips_chaining" in target:
                return True
            prod_type = str(x0.get("product_type", "")).lower()
            if "clip" in prod_type or "reel" in prod_type:
                return True
        media = item.get("media_share") or item.get("clip") or {}
        if media.get("media_type") == 2:  # media_type 2 is video/clip
            return True
        if "/reel/" in str(item.get("target_url", "")).lower():
            return True
    return False


def make_ascii_bar(ratio: float, length: int = 20) -> str:
    filled = int(round(ratio * length))
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


def compute_streak(dates_set) -> int:
    if not dates_set:
        return 0
    try:
        sorted_dates = sorted([datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in dates_set])
        longest = 1
        current = 1
        for i in range(1, len(sorted_dates)):
            diff = (sorted_dates[i] - sorted_dates[i-1]).days
            if diff == 1:
                current += 1
                if current > longest:
                    longest = current
            elif diff > 1:
                current = 1
        return longest
    except Exception:
        return 1


def get_archetype(sent_ratio: float, night_owl_pct: float, streak: int) -> tuple[str, str]:
    if sent_ratio >= 0.65:
        title = "The Content Broadcaster 📢"
        desc = "You carry the conversation. You send over 65% of the reels while they watch."
    elif sent_ratio <= 0.35:
        title = "The Content Consumer 🍿"
        desc = "They feed you content non-stop. You sit back and enjoy the show."
    else:
        title = "Reel Soulmates ☯️"
        desc = "Balanced dynamic. You trade brainrot back and forth in near-perfect sync."

    badges = []
    if night_owl_pct >= 20.0:
        badges.append("🌙 Midnight Gremlins (20%+ sent after midnight)")
    if streak >= 7:
        badges.append(f"🔥 Addicted Streak ({streak} days in a row)")

    full_desc = desc + (" | " + " • ".join(badges) if badges else "")
    return title, full_desc


def get_thread_display_name(t: dict) -> str:
    title = t.get("thread_title")
    if title:
        return title[:35]
    users = t.get("users", [])
    usernames = [u.get("username", "") for u in users if u.get("username")]
    if len(usernames) > 2:
        return f"{usernames[0]}, {usernames[1]} +{len(usernames)-2}"
    return ", ".join(usernames)[:35] or "Direct Message"

# ---------------------------------------------------------
# Feature 1: Single Conversation Reel Metrics
# ---------------------------------------------------------
def fast_single_chat_counter(cl: Client):
    my_pk = str(cl.user_id)
    console.print("\n[bold cyan]Loading conversations...[/bold cyan]")
    
    with console.status("Fetching threads...", spinner="dots"):
        try:
            inbox = cl.private_request("direct_v2/inbox/?limit=20")
            threads = inbox.get("inbox", {}).get("threads", [])
        except Exception as e:
            console.print(f"[red]Failed to load inbox: {e}[/red]")
            return

    if not threads:
        console.print("[yellow]No active threads located.[/yellow]")
        return

    table = Table(title="Direct Message Conversations", box=box.ROUNDED)
    table.add_column("No", style="bold cyan", width=4)
    table.add_column("Participant / Title", style="bold white")
    table.add_column("Last Active", style="dim")

    for i, t in enumerate(threads, 1):
        name = get_thread_display_name(t)
        last_item = (t.get("items") or [{}])[0]
        ts = parse_timestamp(last_item.get("timestamp", 0))
        table.add_row(str(i), name, ts.strftime("%Y-%m-%d %H:%M"))

    console.print(table)
    
    try:
        choice = Prompt.ask("Select chat number (or 'b' to back)").strip()
    except (KeyboardInterrupt, EOFError):
        return
    if choice.lower() in ("b", "back", "q", "exit"):
        return

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(threads):
            console.print("[red]Selection out of range.[/red]")
            return
        selected_thread = threads[idx]
    except ValueError:
        console.print("[red]Invalid input number.[/red]")
        return

    thread_id = str(selected_thread.get("thread_id"))
    chat_title = get_thread_display_name(selected_thread)

    console.print("\nScan Depth:")
    console.print(" [1] 100 messages   (Fast)")
    console.print(" [2] 500 messages   (Standard)")
    console.print(" [3] 1,500 messages (Deep)")
    console.print(" [4] ALL Messages   (Total Conversation History from Day 1) 🚀")
    depth_choice = Prompt.ask("Select depth", choices=["1", "2", "3", "4"], default="4").strip()

    scan_all = (depth_choice == "4")
    limit_map = {"1": 100, "2": 500, "3": 1500}
    max_amount = None if scan_all else limit_map.get(depth_choice, 500)

    reels_sent = 0
    reels_rcvd = 0
    hourly_distribution = defaultdict(int)
    daily_distribution = defaultdict(int)
    day_of_week_distribution = defaultdict(int)
    creator_counter = Counter()
    total_messages = 0
    earliest_date = None
    latest_date = None

    interrupted = False
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn() if not scan_all else TextColumn(""),
        TaskProgressColumn() if not scan_all else TextColumn(""),
        console=console
    ) as progress:
        task = progress.add_task(f"Scanning {chat_title}", total=max_amount)
        cursor = None

        try:
            while True:
                if max_amount and total_messages >= max_amount:
                    break
                batch_size = 100 if scan_all else min(100, max_amount - total_messages)
                params = {"direction": "older", "limit": str(batch_size)}
                if cursor:
                    params["cursor"] = str(cursor)

                try:
                    res = cl.private_request(f"direct_v2/threads/{thread_id}/", params=params)
                    th = res.get("thread", {})
                    items = th.get("items", [])
                    if not items:
                        break

                    for item in items:
                        total_messages += 1
                        sender_id = str(item.get("user_id", ""))
                        is_me = (sender_id == my_pk)
                        ts = parse_timestamp(item.get("timestamp", 0))

                        if is_reel(item):
                            if is_me:
                                reels_sent += 1
                            else:
                                reels_rcvd += 1
                            hourly_distribution[ts.hour] += 1
                            d_str = ts.strftime("%Y-%m-%d")
                            daily_distribution[d_str] += 1
                            day_of_week_distribution[ts.strftime("%A")] += 1

                            if not latest_date or ts > latest_date:
                                latest_date = ts
                            if not earliest_date or ts < earliest_date:
                                earliest_date = ts

                            for k in ["xma_clip", "xma_media_share"]:
                                xl = item.get(k) or []
                                if isinstance(xl, list) and xl:
                                    c = xl[0].get("header_title_text")
                                    if c and not str(c).startswith("http") and len(str(c)) < 32:
                                        creator_counter[str(c)] += 1
                                        break

                    if scan_all:
                        progress.update(
                            task,
                            description=f"Scanning {chat_title} ({total_messages:,} msgs | {reels_sent + reels_rcvd:,} reels found)"
                        )
                    else:
                        progress.update(task, completed=total_messages)

                    cursor = th.get("oldest_cursor")
                    if not cursor:
                        break
                    time.sleep(0.15)
                except Exception as e:
                    console.print(f"[dim yellow]Warning: {e}[/dim yellow]")
                    break
        except (KeyboardInterrupt, EOFError):
            interrupted = True
            console.print("\n[yellow][!] Scan paused by user. Compiling dossier with data gathered so far...[/yellow]")

    total_reels = reels_sent + reels_rcvd
    if total_reels == 0:
        console.print(f"\n[yellow]No reels detected in {total_messages:,} messages checked.[/yellow]")
        Prompt.ask("\nPress Enter to return")
        return

    status_label = "Complete history analyzed" if (scan_all and not interrupted) else "Scan finished"
    console.print(f"\n[bold green]✔ {status_label}: {total_messages:,} messages checked ({total_reels:,} reels found)![/bold green]\n")

    # Analytics Computation
    sent_ratio = reels_sent / total_reels
    rcvd_ratio = reels_rcvd / total_reels
    active_days = len(daily_distribution)
    longest_streak = compute_streak(daily_distribution.keys())
    record_day, record_count = max(daily_distribution.items(), key=lambda x: x[1]) if daily_distribution else ("N/A", 0)
    night_owl_reels = sum(hourly_distribution[h] for h in range(0, 5))
    night_owl_pct = (night_owl_reels / total_reels * 100)
    est_watch_hours = (total_reels * 30) / 3600
    archetype_title, archetype_desc = get_archetype(sent_ratio, night_owl_pct, longest_streak)

    # 1. Main Dossier Wrapped Card
    time_span_str = f"{earliest_date.strftime('%b %d, %Y')} ➔ {latest_date.strftime('%b %d, %Y')}" if (earliest_date and latest_date) else "Unknown"
    dossier_text = (
        f"[bold white]Conversation:[/bold white] [bold cyan]{chat_title}[/bold cyan]\n"
        f"[bold white]Timeline:[/bold white]     {time_span_str} ([bold yellow]{active_days:,}[/bold yellow] active sharing days)\n"
        f"[bold white]Total Reels:[/bold white]  [bold yellow]{total_reels:,}[/bold yellow] (≈ [bold green]{est_watch_hours:.1f} hours[/bold green] of watch time)\n"
        f"[bold white]Velocity:[/bold white]     [bold white]{total_reels / max(1, active_days):.1f}[/bold white] reels per active day\n\n"
        f"[bold white]Dynamic:[/bold white]      [bold yellow]{archetype_title}[/bold yellow]\n"
        f"[dim]{archetype_desc}[/dim]"
    )
    console.print(Panel(dossier_text, title="🎬 REEL WRAPPED & FRIENDSHIP DOSSIER", border_style="cyan"))

    # 2. Power Balance
    balance_text = (
        f"[bold cyan]You Sent:[/bold cyan]   {reels_sent:,} ({sent_ratio*100:.1f}%)  [{make_ascii_bar(sent_ratio, 22)}]\n"
        f"[bold magenta]They Sent:[/bold magenta]  {reels_rcvd:,} ({rcvd_ratio*100:.1f}%)  [{make_ascii_bar(rcvd_ratio, 22)}]"
    )
    console.print(Panel(balance_text, title="⚖️ Power Balance", border_style="magenta"))

    # 3. Hall of Fame Records
    rec_table = Table(title="🏆 Hall of Fame Records", box=box.ROUNDED)
    rec_table.add_column("Achievement / Metric", style="bold white")
    rec_table.add_column("Score", style="bold yellow")
    rec_table.add_column("Context", style="dim")

    rec_table.add_row("Longest Daily Streak", f"{longest_streak} consecutive days", "Non-stop daily reel exchange")
    rec_table.add_row("All-Time Craziest Day", f"{record_count} reels", f"Record set on {record_day}")
    rec_table.add_row("3 AM Night Owl Club", f"{night_owl_reels:,} reels ({night_owl_pct:.1f}%)", "Exchanged between 00:00 and 05:00")
    console.print(rec_table)

    # 4. Top Shared Creators
    top_creators = creator_counter.most_common(5)
    if top_creators:
        c_table = Table(title="👑 Top Shared Creators & Pages", box=box.ROUNDED)
        c_table.add_column("Rank", justify="center", width=5)
        c_table.add_column("Creator / Page", style="bold cyan")
        c_table.add_column("Reels Shared", justify="right", style="bold white")
        c_table.add_column("Share %", justify="right", style="green")

        for r_idx, (c_name, c_cnt) in enumerate(top_creators, 1):
            c_table.add_row(str(r_idx), f"@{c_name}", f"{c_cnt:,}", f"{c_cnt/total_reels*100:.1f}%")
        console.print(c_table)

    # 5. Day of Week Distribution
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_table = Table(title="📅 Weekly Rhythm (Day of Week)", box=box.SIMPLE)
    dow_table.add_column("Day", style="cyan")
    dow_table.add_column("Reels", justify="right")
    dow_table.add_column("Activity Bar", style="green")

    max_dow = max(day_of_week_distribution.values()) or 1
    for d_name in dow_order:
        d_cnt = day_of_week_distribution.get(d_name, 0)
        if d_cnt > 0:
            dow_table.add_row(d_name, str(d_cnt), make_ascii_bar(d_cnt / max_dow, 16))
    console.print(dow_table)

    # 6. Peak 24-Hour Diurnal Clock
    if hourly_distribution:
        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0]
        console.print(f"\n[bold white]⏰ Peak Sharing Window:[/bold white] [bold yellow]{peak_hour:02d}:00 to {(peak_hour+1)%24:02d}:00[/bold yellow]\n")

    # Export Action
    export_choice = Prompt.ask("Actions: [bold green][S][/bold green] Save Shareable Card | [Enter] Back to Menu", default="").strip().lower()
    if export_choice in ("s", "save", "export"):
        safe_name = "".join(ch for ch in chat_title if ch.isalnum() or ch in ("_", "-")).strip() or "friend"
        filename = f"reel_wrapped_{safe_name}.txt"
        card_content = (
            f"🎬 INSTAGRAM REEL WRAPPED with {chat_title}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Total Reels Exchanged: {total_reels:,} (~{est_watch_hours:.1f} hours of watch time)\n\n"
            f"• You Sent:   {reels_sent:,} ({sent_ratio*100:.1f}%)\n"
            f"• They Sent:  {reels_rcvd:,} ({rcvd_ratio*100:.1f}%)\n"
            f"• Verdict:    {archetype_title}\n\n"
            f"🏆 HIGHLIGHTS:\n"
            f"• Timeline:         {time_span_str}\n"
            f"• Longest Streak:   {longest_streak} days in a row\n"
            f"• Record Binge Day: {record_count} reels on {record_day}\n"
            f"• Night Owl Reels:  {night_owl_reels:,} ({night_owl_pct:.1f}% sent after midnight)\n"
        )
        if top_creators:
            card_content += "\n👑 TOP CREATORS:\n"
            for r_idx, (c_name, c_cnt) in enumerate(top_creators, 1):
                card_content += f"{r_idx}. @{c_name} ({c_cnt} reels)\n"
        try:
            Path(filename).write_text(card_content, encoding="utf-8")
            console.print(f"[bold green]✔ Saved shareable card to: {Path(filename).resolve()}[/bold green]")
            Prompt.ask("\nPress Enter to return")
        except Exception as e:
            console.print(f"[red]Error saving file: {e}[/red]")

# ---------------------------------------------------------
# Feature 2: Complete Inbox Leaderboard
# ---------------------------------------------------------
def fast_inbox_leaderboard(cl: Client):
    my_pk = str(cl.user_id)
    console.print("\n[bold cyan]Inbox Leaderboard Scope:[/bold cyan]")
    console.print(" [1] Quick Scan    (Top 10 chats, 50 msgs each)")
    console.print(" [2] Standard Scan (Top 20 chats, 150 msgs each)")
    console.print(" [3] Deep Scan     (Top 30 chats, 300 msgs each)")
    console.print(" [4] ALL Messages  (Total History from Day 1 Across ALL Chats) 🚀")
    lb_choice = Prompt.ask("Select scan scope", choices=["1", "2", "3", "4"], default="2").strip()

    scan_all = (lb_choice == "4")
    scope_map = {
        "1": (10, 50),
        "2": (20, 150),
        "3": (30, 300),
        "4": (35, None)
    }
    thread_count, msgs_per_thread = scope_map.get(lb_choice, (20, 150))

    with console.status("Querying inbox threads...", spinner="dots"):
        try:
            inbox = cl.private_request(f"direct_v2/inbox/?limit={thread_count}")
            threads = inbox.get("inbox", {}).get("threads", [])
        except Exception as e:
            console.print(f"[red]Inbox load error: {e}[/red]")
            return

    results = []
    interrupted = False

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        overall_task = progress.add_task("Evaluating threads", total=len(threads))

        try:
            for i, t in enumerate(threads, 1):
                t_id = t.get("thread_id")
                title = get_thread_display_name(t)
                sent = 0
                rcvd = 0
                scanned = 0
                cursor = None

                progress.update(overall_task, description=f"[{i}/{len(threads)}] {title}")

                try:
                    while True:
                        if msgs_per_thread and scanned >= msgs_per_thread:
                            break
                        batch = 100 if scan_all else min(100, msgs_per_thread - scanned)
                        params = {"direction": "older", "limit": str(batch)}
                        if cursor:
                            params["cursor"] = str(cursor)

                        res = cl.private_request(f"direct_v2/threads/{t_id}/", params=params)
                        th = res.get("thread", {})
                        items = th.get("items", [])
                        if not items:
                            break

                        for item in items:
                            scanned += 1
                            if is_reel(item):
                                if str(item.get("user_id", "")) == my_pk:
                                    sent += 1
                                else:
                                    rcvd += 1

                        progress.update(
                            overall_task,
                            description=f"[{i}/{len(threads)}] {title} ({scanned:,} msgs | {sent+rcvd:,} reels)"
                        )

                        cursor = th.get("oldest_cursor")
                        if not cursor:
                            break
                        time.sleep(0.12)
                except Exception:
                    pass

                total = sent + rcvd
                if total > 0:
                    results.append({"title": title, "total": total, "sent": sent, "rcvd": rcvd})
                progress.advance(overall_task)
        except (KeyboardInterrupt, EOFError):
            interrupted = True
            console.print("\n[yellow][!] Inbox scan paused by user. Compiling leaderboard with data collected so far...[/yellow]")

    results.sort(key=lambda x: x["total"], reverse=True)

    table = Table(title="Top Reel Exchange Partners", box=box.ROUNDED)
    table.add_column("Rank", justify="center", width=5)
    table.add_column("Name", style="bold white")
    table.add_column("Total", justify="right", style="bold cyan")
    table.add_column("Sent", justify="right", style="green")
    table.add_column("Received", justify="right", style="magenta")

    for i, r in enumerate(results[:15], 1):
        table.add_row(str(i), r["title"], f"{r['total']:,}", f"{r['sent']:,}", f"{r['rcvd']:,}")

    console.print(table)
    Prompt.ask("\nPress Enter to return")

# ---------------------------------------------------------
# Feature 3: Read-Only Ghost DM Viewer
# ---------------------------------------------------------
def stealth_dm_browser(cl: Client):
    my_pk = str(cl.user_id)
    console.print("\n[bold cyan]Loading conversations (Ghost Mode: Read receipts suppressed)...[/bold cyan]")

    with console.status("Fetching inbox...", spinner="dots"):
        try:
            inbox = cl.private_request("direct_v2/inbox/?limit=15")
            threads = inbox.get("inbox", {}).get("threads", [])
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return

    table = Table(title="Select Conversation to Inspect", box=box.ROUNDED)
    table.add_column("No", style="bold cyan", width=4)
    table.add_column("Participant / Title", style="bold white")
    table.add_column("Snippet", style="dim")

    for i, t in enumerate(threads, 1):
        name = get_thread_display_name(t)
        last_item = (t.get("items") or [{}])[0]
        snippet = last_item.get("text") or last_item.get("item_type") or ""
        table.add_row(str(i), name, str(snippet)[:40])

    console.print(table)
    try:
        choice = Prompt.ask("Select chat number (or 'b' to back)").strip()
    except (KeyboardInterrupt, EOFError):
        return
    if choice.lower() in ("b", "back", "q"):
        return

    try:
        idx = int(choice) - 1
        t_id = threads[idx].get("thread_id")
        t_title = get_thread_display_name(threads[idx])
    except Exception:
        console.print("[red]Invalid selection.[/red]")
        return

    try:
        res = cl.private_request(f"direct_v2/threads/{t_id}/?limit=30")
        items = res.get("thread", {}).get("items", [])
    except Exception as e:
        console.print(f"[red]Failed to load thread: {e}[/red]")
        return

    reels_found = 0
    console.print(f"\n[bold green]Messages: {t_title}[/bold green]")

    for item in reversed(items):
        is_me = (str(item.get("user_id", "")) == my_pk)
        ts = parse_timestamp(item.get("timestamp", 0)).strftime("%H:%M")
        sender = "[cyan]You[/cyan]" if is_me else f"[magenta]{t_title[:15]}[/magenta]"
        itype = str(item.get("item_type", ""))

        if is_reel(item):
            reels_found += 1
            xma = item.get("xma_media_share") or item.get("xma_clip") or []
            url = "https://instagram.com"
            if isinstance(xma, list) and xma:
                url = xma[0].get("target_url") or url
            console.print(f"[{ts}] {sender}: [bold yellow][REEL #{reels_found}][/bold yellow] [dim]{url}[/dim]")
        elif itype == "text":
            console.print(f"[{ts}] {sender}: {item.get('text', '')}")
        else:
            console.print(f"[{ts}] {sender}: [dim]<{itype}>[/dim]")

    Prompt.ask("\nPress Enter to return")

# ---------------------------------------------------------
# Feature 4: Delivery & Read-Receipt Monitor
# ---------------------------------------------------------
def friend_activity_radar(cl: Client):
    my_pk = str(cl.user_id)
    console.print("\n[bold cyan]Inspecting delivery and read status...[/bold cyan]")

    with console.status("Fetching telemetry...", spinner="dots"):
        try:
            inbox = cl.private_request("direct_v2/inbox/?limit=12")
            threads = inbox.get("inbox", {}).get("threads", [])
        except Exception as e:
            console.print(f"[red]Telemetry query error: {e}[/red]")
            return

    table = Table(title="Delivery & Seen Receipt Monitor", box=box.ROUNDED)
    table.add_column("Conversation", style="bold white")
    table.add_column("Last Sent", style="dim")
    table.add_column("Time", style="cyan")
    table.add_column("Status", style="bold yellow")

    now = datetime.datetime.now()

    for t in threads:
        title = get_thread_display_name(t)
        users = t.get("users", [])
        other_user = users[0] if users else {}
        other_pk = str(other_user.get("pk", ""))

        last_item = (t.get("items") or [{}])[0]
        ts = parse_timestamp(last_item.get("timestamp", 0))
        is_me = (str(last_item.get("user_id", "")) == my_pk)
        sender_label = "You" if is_me else other_user.get("username", "Them")

        their_seen = t.get("last_seen_at", {}).get(other_pk, {})
        if their_seen:
            seen_ts = parse_timestamp(their_seen.get("timestamp", 0))
            if is_me and seen_ts < ts:
                status = "[bold red]UNSEEN (Delivered)[/bold red]"
            else:
                diff_m = int((now - seen_ts).total_seconds() / 60)
                status = f"[green]Seen ({diff_m}m ago)[/green]"
        else:
            status = "[dim]No receipt[/dim]"

        snippet = str(last_item.get("text") or last_item.get("item_type"))[:22]
        table.add_row(title, f"{sender_label}: {snippet}", ts.strftime("%H:%M:%S"), status)

    console.print(table)
    Prompt.ask("\nPress Enter to return")

# ---------------------------------------------------------
# Application Entrypoint
# ---------------------------------------------------------
def main():
    cl, username = login_flow()
    user_label = f"@{username}" if not username.startswith("@") else username

    while True:
        console.clear()
        menu_text = (
            f"[bold cyan]Instagram Reel Counter & Local Toolkit[/bold cyan]\n"
            f"Active: [bold green]{user_label}[/bold green] | Session: [dim]~/.ig_toolkit/session.json[/dim]\n\n"
            " [1] Single Chat Reel Counter (Sent vs Received, Peak Hours)\n"
            " [2] Inbox Leaderboard (Top Reel Exchange Partners)\n"
            " [3] Ghost Mode DM Reader (Read without Seen receipts)\n"
            " [4] Read-Receipt Telemetry (Delivery & Unseen Monitor)\n"
            " [5] Clear Session / Switch Account\n"
            " [q] Exit"
        )
        console.print(Panel(menu_text, border_style="cyan"))

        try:
            choice = Prompt.ask("Action", choices=["1", "2", "3", "4", "5", "q", "exit"], default="1").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == "1":
            fast_single_chat_counter(cl)
        elif choice == "2":
            fast_inbox_leaderboard(cl)
        elif choice == "3":
            stealth_dm_browser(cl)
        elif choice == "4":
            friend_activity_radar(cl)
        elif choice == "5":
            logout_account()
            break
        elif choice in ("q", "exit"):
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\nTerminated.")
        sys.exit(0)
