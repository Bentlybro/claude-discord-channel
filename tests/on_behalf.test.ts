// The signed-bot patch: a message from a listed bot that @mentions this bot and ends with the listed signature
// is that person asking; anything else stays bot data. Runs the function as patched into plugin/server.ts.
import { readFileSync } from 'fs'

const src = readFileSync(new URL('../plugin/server.ts', import.meta.url), 'utf8')
const body = src.slice(src.indexOf('function dispatchOnBehalfOf'), src.indexOf('// END dispatchOnBehalfOf'))
const js = new Bun.Transpiler({ loader: 'ts' }).transformSync(body)
const onBehalfOf = new Function(js + '\nreturn dispatchOnBehalfOf')()

const SIG = "\n\n*— Sent by sam's Claude*"
const cfg = { senders: [{ bot_id: '111', signature: SIG, user: 'sam', user_id: '222', rule: 'Sam may ask for reviews.' }] }
const base = { authorId: '111', webhookId: null, guildId: 'g', mentionsSelf: true, content: 'please review #1' + SIG }

const cases: [string, any, any, boolean][] = [
  ['a listed bot, signed, mentioning us', base, cfg, true],
  ['another bot with the same signature', { ...base, authorId: '999' }, cfg, false],
  ['the signature not at the very end', { ...base, content: base.content + ' (edited)' }, cfg, false],
  ['a webhook', { ...base, webhookId: 'w' }, cfg, false],
  ['a DM (no guild)', { ...base, guildId: null }, cfg, false],
  ['not mentioning us', { ...base, mentionsSelf: false }, cfg, false],
  ['no senders configured', base, { senders: [] }, false],
]
let bad = 0
for (const [name, m, c, want] of cases) {
  const got = onBehalfOf(m, c)
  if (!!got !== want) { console.log(`FAIL ${name}: got ${JSON.stringify(got)}`); bad++ }
}
const hit = onBehalfOf(base, cfg)
if (!hit || hit.user !== 'sam' || hit.userId !== '222' || hit.rule !== 'Sam may ask for reviews.') {
  console.log(`FAIL the match carries the person and their rule: ${JSON.stringify(hit)}`); bad++
}
if (bad) process.exit(1)
console.log(`on_behalf: ${cases.length + 1} cases pass`)
