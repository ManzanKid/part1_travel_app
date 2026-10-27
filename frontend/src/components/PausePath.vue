<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  BREATHING_CYCLES,
  BREATHING_DURATION_MS,
  STOP_STEPS,
  STOP_STEP_DURATION_MS,
  breathingCue,
  containsObviousCrisisLanguage,
  stopCue,
} from '../pausepathRules.mjs'

const screen = ref('home')
const returnScreen = ref('home')
const simplerView = ref(false)

const scenario = ref('')
const saveConversationConsent = ref(false)
const suggestionPending = ref(false)
const suggestion = ref(null)
const suggestionError = ref('')
const conversationError = ref('')
const conversationSaved = ref(false)

const historyLoading = ref(false)
const historyError = ref('')
const sessions = ref([])
const conversations = ref([])
const lastSkillId = ref(null)
const deletingId = ref('')

const activeSkillId = ref('')
const activeElapsedMs = ref(0)
const stopStepIndex = ref(0)
const stopStepElapsedMs = ref(0)
const paused = ref(false)
const pauseNote = ref('')
const sessionStartedAt = ref('')
const sessionFinishedAt = ref('')
const sessionDurationMs = ref(0)
const sessionStatus = ref('stopped')
const sessionSaved = ref(false)
const sessionSaving = ref(false)
const sessionError = ref('')
const sessionNotice = ref('')

let timerHandle = null
let lastTickAt = null

const currentCue = computed(() => {
  if (activeSkillId.value === 'breathing') return breathingCue(activeElapsedMs.value)
  if (activeSkillId.value === 'stop') {
    return {
      ...stopCue(stopStepIndex.value, stopStepElapsedMs.value),
      stepCount: STOP_STEPS.length,
    }
  }
  return null
})

const exerciseProgress = computed(() => {
  if (activeSkillId.value === 'breathing') {
    return `${currentCue.value?.cycle ?? BREATHING_CYCLES} of ${BREATHING_CYCLES} cycles`
  }
  if (activeSkillId.value === 'stop') {
    return `Step ${currentCue.value?.step ?? 1} of ${STOP_STEPS.length}`
  }
  return ''
})

function readLocalSimplerView() {
  try {
    simplerView.value = window.localStorage.getItem('pausepath-simpler-view') === 'true'
  } catch {
    simplerView.value = false
  }
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, options)
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'PausePath could not complete that request.')
  return data
}

function jsonOptions(method, body) {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

async function loadPreferences() {
  try {
    const data = await requestJson('/api/pausepath/preferences')
    simplerView.value = Boolean(data.simpler_view)
    try {
      window.localStorage.setItem('pausepath-simpler-view', String(simplerView.value))
    } catch {
      // The local display control still works if browser storage is unavailable.
    }
  } catch {
    // PausePath remains usable without the backend preference endpoint.
  }
}

async function toggleSimplerView() {
  simplerView.value = !simplerView.value
  try {
    window.localStorage.setItem('pausepath-simpler-view', String(simplerView.value))
  } catch {
    // The in-memory setting remains active for this visit.
  }
  try {
    await requestJson('/api/pausepath/preferences', jsonOptions('PUT', {
      simpler_view: simplerView.value,
    }))
  } catch {
    // Simpler view is a local interface control and does not depend on persistence.
  }
}

async function loadHistory() {
  historyLoading.value = true
  historyError.value = ''
  try {
    const data = await requestJson('/api/pausepath/history')
    sessions.value = data.sessions || []
    conversations.value = data.conversations || []
    lastSkillId.value = data.last_skill_id || null
  } catch {
    historyError.value = 'Saved history is unavailable right now. You can still use either exercise.'
  } finally {
    historyLoading.value = false
  }
}

async function openHistory() {
  screen.value = 'history'
  await loadHistory()
}

function openCrisisInformation() {
  if (screen.value === 'crisis') return
  if (screen.value === 'exercise' && !paused.value) {
    pauseExercise('crisis')
  }
  returnScreen.value = screen.value
  screen.value = 'crisis'
}

function closeCrisisInformation() {
  screen.value = returnScreen.value || 'home'
  returnScreen.value = 'home'
}

function stopTimer() {
  if (timerHandle !== null) window.clearInterval(timerHandle)
  timerHandle = null
  lastTickAt = null
}

function finishExercise(status) {
  stopTimer()
  paused.value = false
  pauseNote.value = ''
  sessionFinishedAt.value = new Date().toISOString()
  sessionDurationMs.value = Math.max(0, Math.round(activeElapsedMs.value))
  sessionStatus.value = status
  sessionSaved.value = false
  sessionSaving.value = false
  sessionError.value = ''
  sessionNotice.value = ''
  screen.value = 'complete'
}

function advanceClock(now = performance.now()) {
  if (lastTickAt === null || paused.value || screen.value !== 'exercise') return
  const delta = Math.max(0, now - lastTickAt)
  lastTickAt = now
  activeElapsedMs.value += delta

  if (activeSkillId.value === 'breathing') {
    if (activeElapsedMs.value >= BREATHING_DURATION_MS) {
      activeElapsedMs.value = BREATHING_DURATION_MS
      finishExercise('completed')
    }
    return
  }

  stopStepElapsedMs.value += delta
  while (stopStepElapsedMs.value >= STOP_STEP_DURATION_MS && screen.value === 'exercise') {
    stopStepElapsedMs.value -= STOP_STEP_DURATION_MS
    if (stopStepIndex.value >= STOP_STEPS.length - 1) {
      finishExercise('completed')
      return
    }
    stopStepIndex.value += 1
  }
}

function startTimer() {
  stopTimer()
  lastTickAt = performance.now()
  timerHandle = window.setInterval(() => advanceClock(performance.now()), 100)
}

async function beginExercise(skillId) {
  if (skillId !== 'breathing' && skillId !== 'stop') return
  activeSkillId.value = skillId
  activeElapsedMs.value = 0
  stopStepIndex.value = 0
  stopStepElapsedMs.value = 0
  paused.value = false
  pauseNote.value = ''
  sessionStartedAt.value = ''
  sessionFinishedAt.value = ''
  sessionDurationMs.value = 0
  sessionStatus.value = 'stopped'
  sessionSaved.value = false
  sessionError.value = ''
  sessionNotice.value = ''
  screen.value = 'exercise'
  await nextTick()
  if (screen.value !== 'exercise') return
  sessionStartedAt.value = new Date().toISOString()
  startTimer()
}

function pauseExercise(reason = 'user') {
  if (screen.value !== 'exercise' || paused.value) return
  advanceClock()
  if (screen.value !== 'exercise') return
  stopTimer()
  paused.value = true
  pauseNote.value = reason === 'background'
    ? 'The exercise paused because this tab became inactive.'
    : reason === 'crisis'
      ? 'The exercise is paused while you view crisis information.'
      : 'Paused. Resume when you are ready.'
}

function resumeExercise() {
  if (screen.value !== 'exercise' || !paused.value) return
  paused.value = false
  pauseNote.value = ''
  startTimer()
}

function leaveExercise() {
  if (screen.value === 'crisis' && returnScreen.value === 'exercise') {
    returnScreen.value = 'home'
    finishExercise('stopped')
    return
  }
  if (screen.value !== 'exercise') {
    screen.value = 'home'
    return
  }
  advanceClock()
  if (screen.value === 'exercise') finishExercise('stopped')
}

function nextStopStep() {
  if (paused.value || screen.value !== 'exercise' || activeSkillId.value !== 'stop') return
  advanceClock()
  if (screen.value !== 'exercise') return
  if (stopStepIndex.value >= STOP_STEPS.length - 1) {
    finishExercise('completed')
    return
  }
  stopStepIndex.value += 1
  stopStepElapsedMs.value = 0
}

async function saveSession() {
  if (sessionSaved.value || sessionSaving.value || !sessionStartedAt.value || !sessionFinishedAt.value) return
  sessionSaving.value = true
  sessionError.value = ''
  sessionNotice.value = ''
  try {
    await requestJson('/api/pausepath/sessions', jsonOptions('POST', {
      skill_id: activeSkillId.value,
      started_at: sessionStartedAt.value,
      finished_at: sessionFinishedAt.value,
      duration_ms: sessionDurationMs.value,
      status: sessionStatus.value,
    }))
    sessionSaved.value = true
    sessionNotice.value = 'This session was saved to your local history.'
    lastSkillId.value = activeSkillId.value
    await loadHistory()
  } catch {
    sessionError.value = 'This session could not be saved. You can continue without saving.'
  } finally {
    sessionSaving.value = false
  }
}

async function askForSuggestion() {
  const fictionalScenario = scenario.value.trim()
  const shouldSaveConversation = saveConversationConsent.value
  suggestion.value = null
  suggestionError.value = ''
  conversationError.value = ''
  conversationSaved.value = false
  if (!fictionalScenario) {
    suggestionError.value = 'Enter a short fictional scenario, or choose an exercise directly.'
    return
  }
  if (containsObviousCrisisLanguage(fictionalScenario)) {
    suggestionError.value = 'The optional suggestion was skipped for this fictional input.'
    openCrisisInformation()
    return
  }

  suggestionPending.value = true
  try {
    const data = await requestJson('/api/pausepath/recommend', jsonOptions('POST', {
      scenario: fictionalScenario,
    }))
    if (data.crisis_info) {
      suggestionError.value = 'The optional suggestion was skipped for this fictional input.'
      openCrisisInformation()
      return
    }
    if (data.skill_id !== 'breathing' && data.skill_id !== 'stop') {
      throw new Error('invalid suggestion')
    }
    suggestion.value = data.skill_id
    if (shouldSaveConversation) {
      try {
        await requestJson('/api/pausepath/conversations', jsonOptions('POST', {
          scenario: fictionalScenario,
          skill_id: data.skill_id,
        }))
        conversationSaved.value = true
        await loadHistory()
      } catch {
        conversationError.value = 'The suggestion is available, but the fictional exchange could not be saved.'
      }
    }
  } catch {
    suggestionError.value = 'Suggestions are unavailable. You can choose either activity normally.'
  } finally {
    suggestionPending.value = false
  }
}

function useSuggestion() {
  if (suggestion.value) beginExercise(suggestion.value)
}

async function deleteSavedItem(kind, id) {
  if (!id || deletingId.value) return
  deletingId.value = id
  historyError.value = ''
  try {
    const path = kind === 'session'
      ? `/api/pausepath/sessions/${encodeURIComponent(id)}`
      : `/api/pausepath/conversations/${encodeURIComponent(id)}`
    await requestJson(path, { method: 'DELETE' })
    await loadHistory()
  } catch {
    historyError.value = 'That saved item could not be deleted.'
  } finally {
    deletingId.value = ''
  }
}

async function deleteAllHistory() {
  if (!window.confirm('Delete all saved PausePath sessions and fictional conversations?')) return
  historyError.value = ''
  try {
    await requestJson('/api/pausepath/history', { method: 'DELETE' })
    await loadHistory()
  } catch {
    historyError.value = 'Saved history could not be deleted.'
  }
}

function formatDate(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatDuration(durationMs) {
  const seconds = Math.max(0, Math.round(Number(durationMs || 0) / 1_000))
  return `${seconds} ${seconds === 1 ? 'second' : 'seconds'}`
}

function handleVisibilityChange() {
  if (document.hidden && screen.value === 'exercise' && !paused.value) {
    pauseExercise('background')
  }
}

onMounted(() => {
  readLocalSimplerView()
  loadPreferences()
  loadHistory()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  stopTimer()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <main class="pausepath-page" :class="{ 'simpler-view': simplerView }">
    <header class="pausepath-header">
      <div>
        <p class="pausepath-eyebrow">Coursework prototype · fictional scenarios only</p>
        <h1>PausePath</h1>
        <p class="pausepath-disclaimer">
          PausePath is not therapy, diagnosis, crisis monitoring, or a real mental health support service.
        </p>
      </div>
      <div class="pausepath-persistent-controls" role="group" aria-label="PausePath controls">
        <button class="pausepath-button crisis-button" type="button" @click="openCrisisInformation">
          Crisis information
        </button>
        <button
          class="pausepath-button leave-button"
          type="button"
          @click="leaveExercise"
        >
          Stop / Leave
        </button>
        <button
          class="pausepath-button simpler-button"
          type="button"
          :aria-pressed="simplerView"
          @click="toggleSimplerView"
        >
          Simpler view: {{ simplerView ? 'On' : 'Off' }}
        </button>
      </div>
    </header>

    <p class="pausepath-safety-note">
      This coursework prototype is for fictional scenarios only. It does not monitor users or provide emergency assistance.
    </p>

    <section v-if="screen === 'home'" class="pausepath-card" aria-labelledby="pausepath-home-title">
      <h2 id="pausepath-home-title">Choose one short activity</h2>
      <p>No explanation is needed. You can pause or leave at any time.</p>

      <div class="skill-options">
        <article class="skill-choice">
          <h3>4–6 breathing</h3>
          <p>Six cycles: inhale for four seconds, then exhale for six seconds. About 60 seconds.</p>
          <button class="pausepath-button primary" type="button" @click="beginExercise('breathing')">
            Start 4–6 breathing
          </button>
        </article>
        <article class="skill-choice">
          <h3>STOP</h3>
          <p>Four short steps, shown one at a time. About 60 seconds at the suggested pace.</p>
          <button class="pausepath-button primary" type="button" @click="beginExercise('stop')">
            Start STOP
          </button>
        </article>
      </div>

      <div class="pausepath-secondary-actions">
        <button class="pausepath-button" type="button" @click="openHistory">View saved history</button>
        <button
          v-if="lastSkillId"
          class="pausepath-button"
          type="button"
          @click="beginExercise(lastSkillId)"
        >
          Repeat last saved skill
        </button>
      </div>

      <section class="choose-help" aria-labelledby="help-choose-title">
        <h3 id="help-choose-title">Help me choose <span class="optional-label">Optional</span></h3>
        <p>A free-model suggestion can select only one of the two options. You remain in control.</p>
        <form class="scenario-form" @submit.prevent="askForSuggestion">
          <label for="pausepath-scenario">Short fictional scenario</label>
          <textarea
            id="pausepath-scenario"
            v-model="scenario"
            maxlength="160"
            rows="3"
            placeholder="For example: A fictional student feels rushed before a presentation."
            :disabled="suggestionPending"
          ></textarea>
          <small>{{ scenario.length }}/160 characters. Do not enter real personal information.</small>
          <small>A limited phrase check may bypass a suggestion. It can miss or overflag wording and does not assess risk.</small>
          <label class="consent-option">
            <input v-model="saveConversationConsent" type="checkbox" />
            Save this fictional exchange to history if a suggestion is returned.
          </label>
          <button class="pausepath-button" type="submit" :disabled="suggestionPending">
            {{ suggestionPending ? 'Preparing optional suggestion…' : 'Help me choose' }}
          </button>
        </form>
        <p v-if="suggestionPending" class="pausepath-status" role="status">
          The optional suggestion is loading. Crisis information remains available above.
        </p>
        <p v-if="suggestionError" class="pausepath-error" role="alert">{{ suggestionError }}</p>
        <p v-if="conversationError" class="pausepath-error" role="alert">{{ conversationError }}</p>
        <p v-if="conversationSaved" class="pausepath-status" role="status">
          The fictional exchange was saved with your consent.
        </p>
        <div v-if="suggestion" class="suggestion-result" role="status">
          <p>
            Optional suggestion: <strong>{{ suggestion === 'breathing' ? '4–6 breathing' : 'STOP' }}</strong>.
            This is not a clinical assessment; either activity remains available.
          </p>
          <button class="pausepath-button primary" type="button" @click="useSuggestion">
            Start suggested activity
          </button>
        </div>
      </section>
    </section>

    <section v-else-if="screen === 'exercise'" class="pausepath-card exercise-card" aria-labelledby="exercise-title">
      <p class="pausepath-progress">{{ exerciseProgress }}</p>
      <h2 id="exercise-title">{{ activeSkillId === 'breathing' ? '4–6 breathing' : 'STOP' }}</h2>
      <div class="exercise-instruction">
        <p aria-live="polite" aria-atomic="true">{{ paused ? 'Paused' : currentCue?.instruction }}</p>
        <strong v-if="!paused" class="countdown">{{ currentCue?.secondsRemaining }}</strong>
      </div>
      <p v-if="activeSkillId === 'breathing'" class="pausepath-progress-note">
        Cycle {{ currentCue?.cycle }} of {{ BREATHING_CYCLES }} · about 60 seconds total
      </p>
      <p v-else class="pausepath-progress-note">
        Step {{ currentCue?.step }} of {{ STOP_STEPS.length }} · about 60 seconds at the suggested pace
      </p>
      <p v-if="paused" class="pausepath-status" role="status">{{ pauseNote }}</p>
      <div class="exercise-controls">
        <button
          v-if="!paused"
          class="pausepath-button"
          type="button"
          @click="pauseExercise()"
        >Pause</button>
        <button v-else class="pausepath-button primary" type="button" @click="resumeExercise">
          Resume
        </button>
        <button
          v-if="activeSkillId === 'stop' && !paused"
          class="pausepath-button"
          type="button"
          @click="nextStopStep"
        >
          {{ stopStepIndex === STOP_STEPS.length - 1 ? 'Finish now' : 'Next' }}
        </button>
      </div>
      <p class="exercise-duration-note">
        Active duration {{ formatDuration(activeElapsedMs) }}. Pauses and inactive-tab time are excluded.
      </p>
    </section>

    <section v-else-if="screen === 'complete'" class="pausepath-card" aria-labelledby="completion-title">
      <h2 id="completion-title">{{ sessionStatus === 'completed' ? 'This activity is complete' : 'You left the activity' }}</h2>
      <p>
        {{ sessionStatus === 'completed' ? 'You can leave, repeat, or choose another activity.' : 'You can leave it here or choose another activity.' }}
      </p>
      <p>Active exercise duration: {{ formatDuration(sessionDurationMs) }}. Pauses are excluded.</p>
      <button
        v-if="!sessionSaved"
        class="pausepath-button primary"
        type="button"
        :disabled="sessionSaving"
        @click="saveSession"
      >
        {{ sessionSaving ? 'Saving…' : 'Save this session to history' }}
      </button>
      <p v-if="sessionSaved" class="pausepath-status" role="status">{{ sessionNotice }}</p>
      <p v-if="sessionError" class="pausepath-error" role="alert">{{ sessionError }}</p>
      <div class="pausepath-secondary-actions">
        <button class="pausepath-button" type="button" @click="beginExercise(activeSkillId)">Repeat this activity</button>
        <button class="pausepath-button" type="button" @click="screen = 'home'">Choose another activity</button>
        <button class="pausepath-button" type="button" @click="openHistory">View history</button>
      </div>
    </section>

    <section v-else-if="screen === 'history'" class="pausepath-card" aria-labelledby="history-title">
      <div class="history-heading">
        <div>
          <h2 id="history-title">Saved history</h2>
          <p>Only items you explicitly chose to save appear here.</p>
        </div>
        <button
          v-if="sessions.length || conversations.length"
          class="pausepath-button delete-history-button"
          type="button"
          @click="deleteAllHistory"
        >Delete all saved history</button>
      </div>
      <p v-if="historyLoading" class="pausepath-status" role="status">Loading saved history…</p>
      <p v-if="historyError" class="pausepath-error" role="alert">{{ historyError }}</p>
      <p v-if="!historyLoading && !sessions.length && !conversations.length" class="pausepath-status">
        No saved PausePath history.
      </p>

      <div v-if="sessions.length" class="history-group">
        <h3>Practice sessions</h3>
        <article v-for="session in sessions" :key="session.session_id" class="history-item">
          <div>
            <strong>{{ session.skill_id === 'breathing' ? '4–6 breathing' : 'STOP' }}</strong>
            <p>{{ formatDate(session.finished_at) }} · {{ formatDuration(session.duration_ms) }} · {{ session.status }}</p>
          </div>
          <button
            class="pausepath-button delete-history-button"
            type="button"
            :disabled="deletingId === session.session_id"
            @click="deleteSavedItem('session', session.session_id)"
          >Delete</button>
        </article>
      </div>

      <div v-if="conversations.length" class="history-group">
        <h3>Fictional AI conversations</h3>
        <article v-for="conversation in conversations" :key="conversation.thread_id" class="history-item conversation-item">
          <div>
            <strong>Optional suggestion: {{ conversation.skill_id === 'breathing' ? '4–6 breathing' : 'STOP' }}</strong>
            <p v-for="(message, index) in conversation.messages" :key="`${conversation.thread_id}-${index}`">
              <span>{{ message.role === 'user' ? 'Fictional scenario: ' : 'PausePath: ' }}</span>{{ message.content }}
            </p>
          </div>
          <button
            class="pausepath-button delete-history-button"
            type="button"
            :disabled="deletingId === conversation.thread_id"
            @click="deleteSavedItem('conversation', conversation.thread_id)"
          >Delete</button>
        </article>
      </div>

      <button class="pausepath-button" type="button" @click="screen = 'home'">Back to activities</button>
    </section>

    <section v-else-if="screen === 'crisis'" class="pausepath-card crisis-card" aria-labelledby="crisis-title">
      <p class="pausepath-eyebrow">Static information · available without the model</p>
      <h2 id="crisis-title">Crisis information</h2>
      <p>If you are in the United States and need crisis support, call or text 988.</p>
      <p><a href="tel:988">Call 988</a> · <a href="sms:988">Text 988</a> · <a href="https://988lifeline.org/get-help/" target="_blank" rel="noopener noreferrer">988 Lifeline information</a></p>
      <p>For an immediate emergency, <a href="tel:911">call 911</a>.</p>
      <p class="pausepath-safety-note">
        PausePath does not monitor users, assess risk, or provide crisis or emergency assistance.
        This limited phrase check can miss or overflag language and cannot determine anyone’s risk.
      </p>
      <p v-if="returnScreen === 'exercise'" class="pausepath-status" role="status">
        Your exercise is paused. Resume it only if you choose.
      </p>
      <button class="pausepath-button primary" type="button" @click="closeCrisisInformation">
        {{ returnScreen === 'exercise' ? 'Return to paused activity' : 'Back' }}
      </button>
    </section>

    <footer class="pausepath-footer">
      <span>Fictional coursework prototype only · No clinical assessment or emergency monitoring</span>
    </footer>
  </main>
</template>

<style scoped>
.pausepath-page {
  width: min(1000px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 48px;
  color: #26333a;
}

.pausepath-header,
.pausepath-persistent-controls,
.skill-options,
.pausepath-secondary-actions,
.exercise-controls,
.history-heading,
.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pausepath-header,
.history-heading,
.history-item {
  justify-content: space-between;
}

.pausepath-header {
  align-items: flex-start;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.pausepath-header h1 {
  margin: 0;
  color: #233f45;
  letter-spacing: -0.035em;
}

.pausepath-eyebrow {
  margin: 0 0 6px;
  color: #526d70;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.pausepath-disclaimer,
.pausepath-safety-note {
  max-width: 740px;
  color: #52646a;
  line-height: 1.5;
}

.pausepath-persistent-controls {
  justify-content: flex-end;
  flex-wrap: wrap;
}

.pausepath-button {
  min-height: 44px;
  border: 1px solid #aabbb6;
  border-radius: 9px;
  padding: 10px 14px;
  background: #fff;
  color: #294248;
  font-weight: 650;
  text-align: center;
}

.pausepath-button:hover:not(:disabled) {
  background: #edf4f1;
}

.pausepath-button:focus-visible,
.scenario-form textarea:focus-visible,
.scenario-form input:focus-visible,
.crisis-card a:focus-visible {
  outline: 3px solid #729ba0;
  outline-offset: 2px;
}

.pausepath-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.crisis-button {
  border-color: #8a4848;
  background: #fff7f4;
  color: #702c2c;
}

.leave-button {
  border-color: #64777c;
}

.simpler-button[aria-pressed="true"],
.primary {
  border-color: #315f62;
  background: #315f62;
  color: #fff;
}

.primary:hover:not(:disabled) {
  background: #234e51;
}

.pausepath-safety-note {
  margin: 14px 0;
  border-left: 4px solid #a0b6aa;
  padding: 9px 13px;
  background: #f0f5f1;
}

.pausepath-card {
  margin-top: 20px;
  border: 1px solid #d9e2dc;
  border-radius: 16px;
  padding: 26px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(33, 57, 53, 0.06);
}

.pausepath-card h2 {
  margin: 0 0 8px;
  color: #243f44;
}

.pausepath-card h3 {
  margin-top: 0;
  color: #2a4b4d;
}

.skill-options {
  align-items: stretch;
  margin-top: 20px;
}

.skill-choice {
  flex: 1 1 0;
  border: 1px solid #dbe5df;
  border-radius: 12px;
  padding: 20px;
  background: #f9fbf8;
}

.skill-choice p,
.choose-help p,
.history-item p {
  color: #596a6c;
  line-height: 1.5;
}

.pausepath-secondary-actions {
  flex-wrap: wrap;
  margin: 18px 0;
}

.choose-help {
  margin-top: 26px;
  border-top: 1px solid #e3e9e4;
  padding-top: 22px;
}

.optional-label {
  border-radius: 999px;
  padding: 3px 8px;
  background: #eaf0ec;
  color: #52646a;
  font-size: 0.73rem;
  vertical-align: middle;
}

.scenario-form {
  display: grid;
  gap: 9px;
  max-width: 700px;
}

.scenario-form label {
  font-weight: 650;
}

.scenario-form textarea {
  width: 100%;
  resize: vertical;
  border: 1px solid #b9c8c2;
  border-radius: 9px;
  padding: 12px;
  color: #26333a;
  font: inherit;
  line-height: 1.45;
}

.scenario-form small {
  color: #617174;
}

.consent-option {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin: 8px 0;
  line-height: 1.45;
}

.consent-option input {
  width: 18px;
  height: 18px;
  margin: 2px 0 0;
  flex: 0 0 auto;
}

.suggestion-result,
.pausepath-status,
.pausepath-error {
  margin-top: 16px;
  border-radius: 9px;
  padding: 12px 14px;
  line-height: 1.5;
}

.suggestion-result,
.pausepath-status {
  border: 1px solid #c5d8cb;
  background: #f0f7f1;
}

.pausepath-error {
  border: 1px solid #dfb5b0;
  background: #fff4f1;
  color: #7a302a;
}

.exercise-card {
  text-align: center;
}

.pausepath-progress {
  margin: 0 0 7px;
  color: #53686a;
  font-weight: 700;
}

.exercise-instruction {
  min-height: 150px;
  display: grid;
  place-content: center;
  margin: 20px auto;
  border: 1px solid #d7e4dc;
  border-radius: 16px;
  background: #f6faf6;
}

.exercise-instruction p {
  margin: 0;
  padding: 12px 20px 4px;
  color: #29474b;
  font-size: clamp(1.5rem, 4vw, 2.15rem);
  font-weight: 650;
}

.countdown {
  padding-bottom: 12px;
  color: #42676a;
  font-size: 1.5rem;
}

.pausepath-progress-note,
.exercise-duration-note {
  color: #5b6d70;
}

.exercise-controls {
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 20px;
}

.exercise-duration-note {
  margin-top: 22px;
  font-size: 0.92rem;
}

.history-heading {
  align-items: flex-start;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.history-heading p {
  margin-bottom: 0;
}

.history-group {
  margin: 22px 0;
}

.history-item {
  align-items: flex-start;
  gap: 16px;
  border-top: 1px solid #e3e9e4;
  padding: 15px 0;
}

.history-item p {
  margin: 5px 0;
  overflow-wrap: anywhere;
}

.delete-history-button {
  flex: 0 0 auto;
  border-color: #d3aaaa;
  color: #773d3d;
}

.crisis-card a {
  color: #274f69;
  font-weight: 700;
}

.pausepath-footer {
  margin-top: 24px;
  color: #657477;
  font-size: 0.85rem;
  text-align: center;
}

.simpler-view .pausepath-card {
  box-shadow: none;
  border-width: 2px;
  padding: 30px;
}

.simpler-view .pausepath-card > p,
.simpler-view .skill-choice p {
  font-size: 1.08rem;
}

.simpler-view .pausepath-button {
  min-height: 50px;
  font-size: 1.02rem;
}

.simpler-view .exercise-instruction {
  min-height: 180px;
  border-width: 2px;
  background: #fff;
}

.simpler-view .exercise-instruction p {
  font-size: clamp(1.8rem, 5vw, 2.6rem);
}

@media (max-width: 700px) {
  .pausepath-header,
  .pausepath-persistent-controls {
    align-items: stretch;
    flex-direction: column;
  }

  .pausepath-persistent-controls {
    width: 100%;
  }

  .skill-options {
    flex-direction: column;
  }

  .pausepath-card {
    padding: 20px;
  }

  .history-item {
    flex-direction: column;
  }
}
</style>
