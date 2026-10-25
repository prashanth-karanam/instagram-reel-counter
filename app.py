import os
import sys
import io
import time
import json
import datetime
from pathlib import Path
from collections import defaultdict
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
            target = str(x0.get("target_url", "")).lower()
            if "/reel/" in target or "/reels/" in target:
                return True
            prod_type = str(x0.get("product_type", "")).lower()
            if "clip" in prod_type or "reel" in prod_type:
                return True
        media = item.get("media_share") or item.get("clip") or {}
        if media.get("media_type") == 2 and (media.get("product_type") == "clips" or "/reel/" in str(media.get("code", "")).lower()):
            return True
        if "/reel/" in str(item.get("target_url", "")).lower():
            return True
    return False


def make_ascii_bar(ratio: float, length: int = 20) -> str:
    filled = int(round(ratio * length))
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


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
    total_messages = 0

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
                url = f"direct_v2/threads/{thread_id}/?limit={batch_size}"
                if cursor:
                    url += f"&cursor={cursor}"

                try:
                    res = cl.private_request(url)
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

                    if scan_all:
                        progress.update(
                            task,
                            description=f"Scanning {chat_title} ({total_messages:,} msgs | {reels_sent + reels_rcvd:,} reels found)"
                        )
                    else:
                        progress.update(task, completed=total_messages)

                    cursor = th.get("oldest_cursor")
                    if not cursor or not th.get("has_older"):
                        break
                    time.sleep(0.2)
                except Exception as e:
                    console.print(f"[dim yellow]Warning: {e}[/dim yellow]")
                    break
        except (KeyboardInterrupt, EOFError):
            interrupted = True
            console.print("\n[yellow][!] Scan paused by user. Showing results scanned so far...[/yellow]")

    total_reels = reels_sent + reels_rcvd
    status_label = "Complete history parsed" if (scan_all and not interrupted) else "Scan finished"
    console.print(f"\n[bold green]✔ {status_label}: {total_messages:,} messages checked ({total_reels:,} reels found)![/bold green]\n")

    sent_ratio = (reels_sent / total_reels) if total_reels > 0 else 0.5
    rcvd_ratio = 1.0 - sent_ratio

    if reels_sent > reels_rcvd:
        verdict = f"You send more reels ({reels_sent} vs {reels_rcvd})"
    elif reels_rcvd > reels_sent:
        verdict = f"They send more reels ({reels_rcvd} vs {reels_sent})"
    else:
        verdict = "Even distribution"

    summary_content = (
        f"Thread: {chat_title}\n"
        f"Total Reels: {total_reels:,}\n\n"
        f"You Sent:    {reels_sent:,} ({sent_ratio*100:.1f}%)  [{make_ascii_bar(sent_ratio, 20)}]\n"
        f"They Sent:   {reels_rcvd:,} ({rcvd_ratio*100:.1f}%)  [{make_ascii_bar(rcvd_ratio, 20)}]\n\n"
        f"Result: {verdict}"
    )
    console.print(Panel(summary_content, title="Reel Exchange Metrics", border_style="cyan"))

    if hourly_distribution:
        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0]
        console.print(f"\nPeak Hour: {peak_hour:02d}:00 to {(peak_hour+1)%24:02d}:00")

        hour_table = Table(title="Activity Distribution (24h)", box=box.SIMPLE)
        hour_table.add_column("Hour", style="cyan")
        hour_table.add_column("Volume", justify="right")
        hour_table.add_column("Graph", style="green")

        max_h = max(hourly_distribution.values()) or 1
        for h in range(24):
            count = hourly_distribution.get(h, 0)
            if count > 0:
                hour_table.add_row(f"{h:02d}:00", str(count), make_ascii_bar(count / max_h, 15))
        console.print(hour_table)

    Prompt.ask("\nPress Enter to return")

# ---------------------------------------------------------
# Feature 2: Complete Inbox Leaderboard
# ---------------------------------------------------------
def fast_inbox_leaderboard(cl: Client):
    my_pk = str(cl.user_id)
    console.print("\n[bold cyan]Inbox Leaderboard Scope:[/bold cyan]")
    console.print(" [1] Quick Scan    (Top 10 chats, 50 msgs each)")
    console.print(" [2] Standard Scan (Top 20 chats, 150 msgs each)")
    console.print(" [3] Deep Scan     (Top 30 chats, 300 msgs each)")
    lb_choice = Prompt.ask("Select scan scope", choices=["1", "2", "3"], default="2").strip()

    scope_map = {
        "1": (10, 50),
        "2": (20, 150),
        "3": (30, 300)
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

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        overall_task = progress.add_task("Evaluating threads", total=len(threads))

        for t in threads:
            t_id = t.get("thread_id")
            title = get_thread_display_name(t)
            sent = 0
            rcvd = 0
            scanned = 0
            cursor = None

            try:
                while scanned < msgs_per_thread:
                    batch = min(100, msgs_per_thread - scanned)
                    url = f"direct_v2/threads/{t_id}/?limit={batch}"
                    if cursor:
                        url += f"&cursor={cursor}"
                    res = cl.private_request(url)
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

                    cursor = th.get("oldest_cursor")
                    if not cursor or not th.get("has_older"):
                        break
                    time.sleep(0.15)
            except Exception:
                pass

            total = sent + rcvd
            if total > 0:
                results.append({"title": title, "total": total, "sent": sent, "rcvd": rcvd})
            progress.advance(overall_task)

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
