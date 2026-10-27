<script setup>
import { computed, ref } from 'vue'

const question = ref('')
const loading = ref(false)
const errorMessage = ref('')
const result = ref(null)
const traceText = computed(() => result.value?.trace
  ? JSON.stringify(result.value.trace, null, 2)
  : '')

async function ask() {
  const text = question.value.trim()
  if (!text || loading.value) return

  loading.value = true
  errorMessage.value = ''
  result.value = null
  try {
    const response = await fetch('/api/chatbot/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text }),
    })
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || 'The hotel assistant could not answer.')
    }
    result.value = data
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'The hotel assistant could not answer. Try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel chatbot-panel" aria-labelledby="hotel-assistant-heading">
    <div class="section-heading">
      <div>
        <h2 id="hotel-assistant-heading">Ask about your saved hotels</h2>
        <p>Answers use your locally saved hotels and their demo nightly records.</p>
      </div>
    </div>

    <form class="chatbot-form" @submit.prevent="ask">
      <label for="hotel-question">Your question</label>
      <textarea
        id="hotel-question"
        v-model="question"
        rows="3"
        maxlength="500"
        placeholder="Which hotel has the lowest total cost for October 10–13, 2026?"
        :disabled="loading"
        aria-describedby="hotel-question-help"
      ></textarea>
      <small id="hotel-question-help">Ask about saved hotels, their nightly prices, dates, or room availability.</small>
      <button type="submit" :disabled="loading || !question.trim()">
        {{ loading ? 'Checking saved hotel data...' : 'Ask assistant' }}
      </button>
    </form>

    <p v-if="loading" class="message" role="status" aria-live="polite">
      Checking saved records and preparing a grounded answer…
    </p>
    <p v-if="errorMessage" class="chatbot-error" role="alert">{{ errorMessage }}</p>

    <section v-if="result" class="chatbot-answer" aria-labelledby="chatbot-answer-heading">
      <h3 id="chatbot-answer-heading">Answer</h3>
      <p v-if="result.trace.retrieved_record_count === 0" class="chatbot-data-note" role="status">
        No matching saved hotel nightly records were found for this question.
      </p>
      <p v-if="result.trace.derived_stays?.some(stay => !stay.complete)" class="chatbot-data-note" role="status">
        Some saved hotels have missing nightly records for these dates, so their total cost or full-stay availability cannot be confirmed.
      </p>
      <p class="chatbot-answer-text" role="status">{{ result.answer }}</p>
      <p class="simulated-label">Prices and room availability are simulated classroom data.</p>
      <details class="chatbot-trace">
        <summary>Verification trace</summary>
        <pre>{{ traceText }}</pre>
      </details>
    </section>
  </section>
</template>

<style scoped>
.chatbot-panel { margin-top: 24px; }
.chatbot-form { display: grid; gap: 9px; }
.chatbot-form label { font-weight: 700; }
.chatbot-form textarea {
  width: 100%; resize: vertical; padding: 12px 14px; border: 1px solid #ccd3df;
  border-radius: 10px; color: #172033; font: inherit; line-height: 1.45;
}
.chatbot-form textarea:focus { outline: 3px solid rgba(45, 104, 167, 0.15); border-color: #2d68a7; }
.chatbot-form small, .simulated-label { color: #657187; }
.chatbot-form button {
  justify-self: start; margin-top: 7px; border: 0; border-radius: 9px;
  padding: 11px 16px; background: #173f5f; color: white; font-weight: 700;
}
.chatbot-form button:disabled { opacity: 0.55; cursor: not-allowed; }
.chatbot-answer { margin-top: 22px; padding: 18px; border: 1px solid #dce3ec; border-radius: 12px; background: #f8fafc; }
.chatbot-answer h3 { margin: 0 0 8px; }
.chatbot-answer-text { white-space: pre-wrap; line-height: 1.55; }
.simulated-label { font-size: 0.9rem; }
.chatbot-error { margin-top: 16px; color: #b91c1c; }
.chatbot-data-note { padding: 11px 12px; border-left: 4px solid #d97706; background: #fff7ed; }
.chatbot-trace { margin-top: 18px; }
.chatbot-trace summary { cursor: pointer; font-weight: 650; }
.chatbot-trace pre { max-height: 340px; overflow: auto; padding: 14px; border-radius: 8px; background: #111827; color: #e5e7eb; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 0.82rem; }
</style>
