/** Component logic probes with the real Vue SFC compiler and Markdown parser.
 * Run: node frontend/tests/audit_frontend.mjs
 * These probes execute script logic in a VM; they are not browser E2E tests.
 */
import fs from 'node:fs'
import path from 'node:path'
import vm from 'node:vm'
import { fileURLToPath } from 'node:url'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { ref, reactive } from 'vue'
import { marked } from 'marked'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const results = []
const source = fs.readFileSync(path.join(root, 'frontend/src/views/chat/index.vue'), 'utf8')
const script = parse(source).descriptor.scriptSetup.content
const stripImports = text => text.replace(/^import[\s\S]*?from\s+['"][^'"]+['"];?\s*$/gm, '')
const defer = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const answer = (sessionId, content) => ({ session_id: sessionId, assistant_message: { id: 100 + sessionId, role: 'assistant', content, sources: [] } })
const message = content => ({ id: content, role: 'assistant', content })

function chatContext(overrides = {}) {
  const context = vm.createContext({
    ref, reactive, marked, onMounted: () => {}, nextTick: callback => callback(),
    ElMessage: { success() {}, warning() {}, error() {} }, ElMessageBox: { confirm: async () => {} },
    getSessionsApi: async () => [], createSessionApi: async () => ({ id: 3, title: 'new' }),
    renameSessionApi: async () => {}, deleteSessionApi: async () => {}, clearSessionMessagesApi: async () => {},
    getSessionMessagesApi: async id => [message(`session-${id}`)], askQuestionApi: async () => answer(1, 'answer'),
    exportChatHistoryApi: async () => {}, ...overrides,
  })
  vm.runInContext(stripImports(script) + '\nglobalThis.audit = { sessions, currentSessionId, messages, inputQuestion, sending, handleSend, selectSession, handleCreateSession, renderMarkdown };', context)
  return context.audit
}

async function run(id, name, probe, defect = false) {
  try {
    const [ok, evidence] = await probe()
    results.push({ id, name, status: ok ? 'PASS' : (defect ? 'ISSUE' : 'FAIL'), evidence })
  } catch (error) {
    results.push({ id, name, status: 'ERROR', evidence: error.stack })
  }
  console.log(`${results.at(-1).status.padEnd(5)} ${id} ${name}`)
}

await run('U01', 'Compile all Vue single-file components', async () => {
  const files = []
  function scan(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const full = path.join(directory, entry.name)
      if (entry.isDirectory()) scan(full)
      else if (entry.name.endsWith('.vue')) files.push(full)
    }
  }
  scan(path.join(root, 'frontend/src'))
  const errors = []
  for (const file of files) {
    const { descriptor, errors: parseErrors } = parse(fs.readFileSync(file, 'utf8'))
    errors.push(...parseErrors)
    const compiled = compileScript(descriptor, { id: file })
    errors.push(...compileTemplate({ source: descriptor.template.content, filename: file, id: file, compilerOptions: { bindingMetadata: compiled.bindings } }).errors)
  }
  return [errors.length === 0, { components: files.length, errors }]
})

await run('U02', 'Markdown rendering preserves executable HTML attributes', async () => {
  const chat = chatContext()
  const html = chat.renderMarkdown('<img src=x onerror="globalThis.__audit_xss=1">')
  return [!html.includes('onerror'), { rendered_html: html, template_uses_v_html: source.includes('v-html="renderMarkdown(msg.content)"') }]
}, true)

await run('U03', 'Switching sessions while a question is in flight mixes replies', async () => {
  const pending = defer()
  const chat = chatContext({ askQuestionApi: () => pending.promise })
  chat.sessions.value = [{ id: 1, title: 'A' }, { id: 2, title: 'B' }]
  chat.currentSessionId.value = 1
  chat.inputQuestion.value = 'question for A'
  const sending = chat.handleSend()
  await chat.selectSession(2)
  pending.resolve(answer(1, 'answer for A'))
  await sending
  const contents = chat.messages.value.map(msg => msg.content)
  return [!contents.includes('answer for A'), { current_session: chat.currentSessionId.value, displayed_messages: contents }]
}, true)

await run('U04', 'Out-of-order message fetches display the wrong session history', async () => {
  const a = defer(), b = defer()
  const chat = chatContext({ getSessionMessagesApi: id => id === 1 ? a.promise : b.promise })
  const selectingA = chat.selectSession(1)
  const selectingB = chat.selectSession(2)
  b.resolve([message('private history B')])
  await selectingB
  a.resolve([message('private history A')])
  await selectingA
  const contents = chat.messages.value.map(msg => msg.content)
  return [contents[0] === 'private history B', { current_session: chat.currentSessionId.value, displayed_messages: contents }]
}, true)

await run('U05', 'Creating a session while generating attaches the old reply to the new session', async () => {
  const pending = defer()
  const chat = chatContext({ askQuestionApi: () => pending.promise })
  chat.currentSessionId.value = 1
  chat.inputQuestion.value = 'old question'
  const sending = chat.handleSend()
  await chat.handleCreateSession()
  pending.resolve(answer(1, 'old answer'))
  await sending
  return [chat.messages.value.length === 0, { current_session: chat.currentSessionId.value, displayed_messages: chat.messages.value.map(msg => msg.content) }]
}, true)

await run('U06', 'Failed send loses input and leaves an unmarked temporary message', async () => {
  const chat = chatContext({ askQuestionApi: async () => { throw new Error('offline') } })
  chat.currentSessionId.value = 1
  chat.inputQuestion.value = 'recover this question'
  await chat.handleSend()
  return [chat.inputQuestion.value === 'recover this question', { input_after_failure: chat.inputQuestion.value, temporary_messages: chat.messages.value.length, sending: chat.sending.value }]
}, true)

await run('U07', 'Browser route guard handles logged-out, employee and admin roles', async () => {
  const code = fs.readFileSync(path.join(root, 'frontend/src/router/index.js'), 'utf8')
  let guard
  const user = { isLoggedIn: false, isAdmin: false }
  const context = vm.createContext({
    createRouter: () => ({ beforeEach: callback => { guard = callback } }), createWebHistory: () => ({}),
    useUserStore: () => user, ElMessage: { warning() {}, error() {} }, document: {},
  })
  vm.runInContext(stripImports(code).replace('export default router', ''), context)
  const destinations = []
  const to = { path: '/settings', meta: { requiresAuth: true, requiresAdmin: true } }
  guard(to, {}, destination => destinations.push(destination ?? 'allowed'))
  user.isLoggedIn = true
  guard(to, {}, destination => destinations.push(destination ?? 'allowed'))
  user.isAdmin = true
  guard(to, {}, destination => destinations.push(destination ?? 'allowed'))
  return [JSON.stringify(destinations) === JSON.stringify(['/login', '/chat', 'allowed']), { destinations }]
})

await run('U08', 'Third-party embedding API key cannot be edited in settings UI', async () => {
  const text = fs.readFileSync(path.join(root, 'frontend/src/views/settings/index.vue'), 'utf8')
  const template = parse(text).descriptor.template.content
  const hasProvider = template.includes('v-model="form.embedding_provider"')
  const hasKey = template.includes('v-model="form.embedding_api_key"')
  return [hasProvider && hasKey, { provider_control: hasProvider, api_key_control: hasKey, backend_fields_exist: true }]
}, true)

const summary = Object.fromEntries(['PASS', 'ISSUE', 'FAIL', 'ERROR'].map(status => [status, results.filter(r => r.status === status).length]))
fs.writeFileSync(path.join(root, 'docs/audit-frontend-results.json'), JSON.stringify({ summary, verification: 'VM component logic and real Vue compiler; no browser E2E', results }, null, 2))
console.log(summary)
process.exitCode = summary.FAIL || summary.ERROR ? 1 : 0
