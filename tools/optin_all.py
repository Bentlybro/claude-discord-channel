#!/usr/bin/env python3
"""Opt every channel the bot can see into the Discord plugin's gate, mention required.

    python3 optin_all.py            show what would change
    python3 optin_all.py --write    write access.json (a timestamped backup is kept beside it)

The plugin delivers a guild message only from a channel listed in access.json `groups`; a thread
is gated by its parent. So an @mention in a channel nobody opted in, or in a thread under one, was
dropped silently -- while the REST poller was a separate, leakier way of catching those. With every
channel listed and `requireMention: true`, the plugin itself delivers any @mention or reply to the
bot, anywhere, and nothing else.

Existing entries are never changed: the bot's own channel keeps `requireMention: false`, and any `allowFrom`
stays as it was. Only missing channels are added.
"""
from __future__ import annotations

import json
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
# Text, announcement, forum and media channels. Threads are never listed: they inherit a parent.
PARENTS = {0: "text", 5: "announcement", 15: "forum", 16: "media"}


def token() -> str:
    for line in ENV.read_text().splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("no DISCORD_BOT_TOKEN in " + str(ENV))


def get(tok: str, path: str):
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bot {tok}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def main() -> int:
    write = "--write" in sys.argv
    tok = token()
    access = json.loads(ACCESS.read_text())
    groups = access.setdefault("groups", {})
    added = []
    for guild in get(tok, "/users/@me/guilds"):
        for ch in get(tok, f"/guilds/{guild['id']}/channels"):
            if ch.get("type") in PARENTS and str(ch["id"]) not in groups:
                added.append((guild["name"], PARENTS[ch["type"]], ch.get("name"), str(ch["id"])))
    for g, kind, name, cid in added:
        groups[cid] = {"requireMention": True, "allowFrom": []}
    print(f"{len(added)} channels to add; {len(groups) - len(added)} already listed, left as they are")
    for g, kind, name, cid in added[:15]:
        print(f"  + {g} / #{name} ({kind})")
    if len(added) > 15:
        print(f"  ... and {len(added) - 15} more")
    if not write:
        print("dry run; pass --write to apply")
        return 0
    backup = ACCESS.with_name(f"access.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(ACCESS, backup)
    tmp = ACCESS.with_name("access.json.tmp")
    tmp.write_text(json.dumps(access, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(ACCESS)        # the plugin re-reads on every message: never let it see half a file
    print(f"written; backup at {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
