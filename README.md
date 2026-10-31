# claude-discord-channel (patched)

The official Claude Code Discord channel plugin (`discord@claude-plugins-official`, v0.0.4) with ten patches
that make it work for a **long-running agent bot**: one Claude session that lives in Discord, follows
conversations, reads other bots safely and answers only when it is actually spoken to.

Built for Dispatch, an always-on supervisor agent, and kept in sync with what it runs. Nothing here is specific
to it: every ID and path is a setting.

## What the patches do

| # | Patch | Why |
|---|-------|-----|
| 1 | **A role ping is not addressed.** Only an @mention of the bot itself (or a reply to it) counts; a role it holds or `@everyone` does not. | discord.js `mentions.has(user)` also matches roles, so every team-wide ping looked like a direct question. |
| 2 | **A thread's own entry wins over its parent's** in `access.json`. | The stock gate looks only at the parent channel, so one thread could never "hear everything" under a mention-only channel. |
| 3 | **Listening is not being spoken to.** Messages delivered without an @mention, reply or DM are tagged `addressed="no"` and get no 👀 or typing indicator. A thread the bot is addressed in is recorded in `engaged.json`. | The bot can follow a conversation without looking as if it is about to answer every line. |
| 4 | **Other bots are read by allowlist; no loops.** Never the bot's own messages; other bots and webhooks only if listed in `bots.json`, tagged `author_is_bot="yes"`. The `reply` tool refuses to answer a bot, or to post where a bot spoke in the last 3 minutes, unless a reply window is open. | Read useful bots (release bots, other agents) without bot-to-bot loops or prompt injection by bot. |
| 5 | **Bare PR numbers become links** in `reply` and `edit_message`, when `DISCORD_PR_REPO` is set; never inside `[..]`, a URL, `<..>` or a code span. | Readers can click through. |
| 6 | **A conversation stays open while the bot is in it.** A person addressing the bot in a thread or channel records it in `engaged.json`; every reply the bot sends there renews it. `tools/discord-listen follow` listens there for a while after. | People had to @ the bot on every follow-up. |
| 7 | **Bot replies are rare.** Answering a bot needs an open window (`tools/discord-bots open-reply`: at most 10 minutes, with a reason, logged); then one reply per bot message and at most 3 per chat per hour. | Occasional, relevant replies to other bots; never loops or piling on. |
| 8 | **A forwarded message arrives with its text.** Discord puts a forward's text in `messageSnapshots` and leaves `content` empty; inbound messages and `fetch_messages` now include it as `[forwarded message] ...`. | A forwarded message reached the bot completely empty. |
| 9 | **Long replies split at words, files on the last part.** Default chunking is paragraph, then line, then word; attachments go with the final chunk. | A long reply was cut mid-word and its files landed on a middle part. |
| 10 | **A signed bot message is its person asking.** A message from a bot listed in `on_behalf.json` that @mentions this bot and *ends with* that person's signature is treated as that person asking (tagged `on_behalf_of`), and opens a short reply window. Anything else that bot posts stays bot data. | A teammate's own Claude posts through a shared bot whose server appends a signature from the caller's API key. |

Every change in `server.ts` is marked `PATCHED(dispatch)`; `patches/upstream-to-patched.diff` shows them all.

## Quick start

1. Install the official plugin the normal way: `/plugin install discord@claude-plugins-official`, then
   `/discord:configure <bot token>`.
2. Patch it: `python3 patch-plugin`. It is idempotent; `python3 patch-plugin --check` exits 1 if a patch is
   missing. **Re-run it after every plugin update** (an update installs a new, unpatched version directory), for
   example at every start of your agent. If upstream code changed, it names the patch it could not apply and
   changes nothing.
3. Start the bot's session with the channel on, and the plugin enabled **only** for that session:
   ```sh
   claude --channels plugin:discord@claude-plugins-official \
          --settings bot.settings.json   # {"enabledPlugins": {"discord@claude-plugins-official": true}}
   ```
   Keep the plugin **off** in `~/.claude/settings.json`, or every Claude session on the machine (workers,
   subagents) loads it and holds the bot's reply tools. Without `--channels` the plugin still reacts 👀 but
   Claude Code drops every message: the classic "it reacts but never answers".
4. Set up `access.json` (below) and, if wanted, `bots.json` with `tools/discord-bots`.

## Settings

| Setting | Used by | What |
|---|---|---|
| `DISCORD_HOME_GUILD` | `tools/discord-listen`, `tools/scope_by_server.py` | Your team's server: anyone there may talk to the bot. |
| `DISCORD_OWNER_ID` | the same | The person the bot works for: the only one who may address it in any other server. The tools refuse to run without it. |
| `DISCORD_BOT_ID` | `tools/discord-bots` | The bot's own user ID, so it is never allowlisted as "another bot". |
| `DISCORD_PR_REPO` | patch 5 | `owner/repo` for PR links. Unset: no links. |
| `DISCORD_STATE_DIR` | tools | The plugin's state dir (default `~/.claude/channels/discord`). |
| `DISCORD_BOTS_LOG` | patch 7 and 10, `tools/discord-bots` | Where reply windows are logged (default `<state dir>/bot-replies.log`). |
| `<state dir>/on_behalf.json` | patch 10 | `{"senders": [{"bot_id": "...", "signature": "\n\n*— Sent by name's Claude*", "user": "name", "user_id": "...", "rule": "what their asks allow"}]}`. No file: patch 10 does nothing. |

## Access conventions (`access.json`)

- `dmPolicy: "allowlist"` (not `"allowFrom"`, which is not a policy: the plugin falls through to pairing and
  hands a code to anyone who DMs it). `allowFrom`: the owner's user ID.
- `groups`: every channel the bot may hear, `requireMention: true`. `tools/optin_all.py` opts every channel of
  every server in; `tools/scope_by_server.py` sets who may speak per server.
- A thread gets its own entry (`requireMention: false`) to hear everything in it: `tools/discord-listen`.
- Always write `access.json` **atomically** (temp file and rename). The plugin re-reads it on every message,
  and a half-written file makes it start over with no channels at all.

## Tools

```
tools/discord-listen       listen in a thread or channel (on the owner's word), follow conversations the bot is in
tools/discord-bots         allowlist other bots; open a short, logged reply window
tools/optin_all.py         opt every channel the bot can see into the gate, mention required
tools/scope_by_server.py   who may speak: the team server open, everywhere else owner-only
```

Each prints its usage with no arguments; `optin_all.py` and `scope_by_server.py` only show what they would
change until you pass `--write` (a timestamped backup of `access.json` is kept).

## Layout and tests

```
patch-plugin                       applies / checks the patches (--file <server.ts> patches any copy)
plugin/                            the official plugin v0.0.4 with the patches applied, for reference
patches/upstream-to-patched.diff   every change against upstream
tools/                             the companion tools above
tests/check_patch.sh               pristine upstream -> patch-plugin -> bun build -> unit tests
tests/on_behalf.test.ts            patch 10's matching rules
```

`bash tests/check_patch.sh` (needs `bun` and the official plugin from the Claude Code marketplace, or
`UPSTREAM=<path>`) proves the patches still apply to upstream, that the result builds, and that the patched
logic behaves.

## Licence

The plugin is Apache License 2.0 (see `LICENSE`); `NOTICE` lists what was changed.
