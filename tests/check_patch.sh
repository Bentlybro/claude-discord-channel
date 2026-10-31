#!/usr/bin/env bash
# Pristine upstream -> patch-plugin -> bun build, then the unit tests. Proves the patches still apply to the
# official plugin, that the result compiles, and that the patched logic behaves.
#   UPSTREAM=<path to the official discord plugin>   (default: the Claude Code marketplace copy)
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
UP=${UPSTREAM:-$HOME/.claude/plugins/marketplaces/claude-plugins-official/external_plugins/discord}
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
cp -r "$UP" "$t/discord"
[ -d "$t/discord/node_modules" ] || (cd "$t/discord" && bun install --silent >/dev/null)
python3 "$here/patch-plugin" --file "$t/discord/server.ts"
python3 "$here/patch-plugin" --check --file "$t/discord/server.ts"
(cd "$t/discord" && bun build server.ts --target=bun --outdir "$t/out" >/dev/null)
cmp -s "$t/discord/server.ts" "$here/plugin/server.ts" || echo "note: plugin/server.ts differs from a fresh patch of upstream; rebuild it with patch-plugin --file"
bun "$here/tests/on_behalf.test.ts"
echo "OK: all patches apply to upstream, the result builds, and the unit tests pass"
