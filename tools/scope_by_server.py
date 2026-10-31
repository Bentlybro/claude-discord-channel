#!/usr/bin/env python3
"""Who may reach the bot through Discord: anyone in your team's server, and only the owner everywhere
else.

    scope_by_server.py            show what would change
    scope_by_server.py --write    apply it (a timestamped backup is kept)

Why: the team should be able to ask the bot for help and work in their server, but the bot is also
in other servers (bot testing and others), where a stranger's @mention reached an agent running in
auto mode. So channels in the team's server stay open to everyone (a mention is still needed outside
the bot's own threads), and every channel in any other server is owner-only.
Also run for a channel created later: an entry missing its scope is fixed the same way.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import sys
import time
import urllib.request

HOME = pathlib.Path.home()
ENV = HOME / ".claude/channels/discord/.env"
ACCESS = HOME / ".claude/channels/discord/access.json"
API = "https://discord.com/api/v10"
UA = "DiscordBot (https://github.com/Bentlybro/claude-discord-channel, 1.0)"
# Settings (environment): DISCORD_HOME_GUILD = your team's server, where anyone may talk to the bot;
# DISCORD_OWNER_ID = the person the bot works for, the only one who may address it anywhere else.
HOME_GUILD = os.environ.get("DISCORD_HOME_GUILD", "")
OWNER = os.environ.get("DISCORD_OWNER_ID", "")


def token() -> str:
    for line in ENV.read_text().splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("no token")


def get(tok, path):
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bot {tok}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def main() -> int:
    if not (HOME_GUILD and OWNER):
        sys.exit("scope_by_server.py: set DISCORD_HOME_GUILD and DISCORD_OWNER_ID first: see README")
    tok = token()
    access = json.loads(ACCESS.read_text())
    groups = access["groups"]
    where: dict[str, tuple[str, str]] = {}
    for g in get(tok, "/users/@me/guilds"):
        for ch in get(tok, f"/guilds/{g['id']}/channels"):
            where[str(ch["id"])] = (g["id"], g["name"])
        for th in (get(tok, f"/guilds/{g['id']}/threads/active").get("threads") or []):
            where[str(th["id"])] = (g["id"], g["name"])
    changed, unknown = [], []
    for cid, entry in groups.items():
        guild = where.get(cid)
        if guild is None:
            unknown.append(cid)          # archived thread or deleted channel: left as it is
            continue
        if guild[0] == HOME_GUILD:
            continue                     # the team: anyone may reach it
        if entry.get("allowFrom") != [OWNER]:
            changed.append((guild[1], cid, entry.get("allowFrom")))
            entry["allowFrom"] = [OWNER]
    by_server: dict[str, int] = {}
    for name, _, _ in changed:
        by_server[name] = by_server.get(name, 0) + 1
    print(f"{len(changed)} channels outside the team's server set to owner-only: {by_server}")
    print(f"{sum(1 for c in groups if (where.get(c) or ('',))[0] == HOME_GUILD)} team-server entries left open to the team")
    print(f"{len(unknown)} entries not currently visible (archived threads, deleted channels): unchanged")
    if "--write" not in sys.argv:
        print("dry run; pass --write to apply")
        return 0
    backup = ACCESS.with_name(f"access.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(ACCESS, backup)
    tmp = ACCESS.with_name("access.json.tmp")
    tmp.write_text(json.dumps(access, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(ACCESS)
    print(f"written; backup at {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
