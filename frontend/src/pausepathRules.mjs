export const SKILL_IDS = Object.freeze(['breathing', 'stop'])

export const BREATHING_PHASES = Object.freeze([
  Object.freeze({ id: 'inhale', instruction: 'Inhale gently', durationMs: 4_000 }),
  Object.freeze({ id: 'exhale', instruction: 'Exhale gently', durationMs: 6_000 }),
])

export const BREATHING_CYCLES = 6
export const BREATHING_CYCLE_MS = BREATHING_PHASES.reduce((sum, phase) => sum + phase.durationMs, 0)
export const BREATHING_DURATION_MS = BREATHING_CYCLES * BREATHING_CYCLE_MS

export const STOP_STEPS = Object.freeze([
  Object.freeze({ id: 'stop', instruction: 'Stop.' }),
  Object.freeze({ id: 'step-back', instruction: 'Take a step back.' }),
  Object.freeze({ id: 'observe', instruction: 'Observe what is happening internally and externally.' }),
  Object.freeze({ id: 'proceed', instruction: 'Proceed mindfully.' }),
])

export const STOP_STEP_DURATION_MS = 15_000
export const STOP_DURATION_MS = STOP_STEPS.length * STOP_STEP_DURATION_MS

export function isSkillId(value) {
  return SKILL_IDS.includes(value)
}

export function breathingCue(elapsedMs) {
  const elapsed = Math.max(0, Math.min(BREATHING_DURATION_MS, Number(elapsedMs) || 0))
  if (elapsed >= BREATHING_DURATION_MS) return { complete: true }

  const cyclePosition = elapsed % BREATHING_CYCLE_MS
  const phase = cyclePosition < BREATHING_PHASES[0].durationMs
    ? BREATHING_PHASES[0]
    : BREATHING_PHASES[1]
  const phaseEnd = phase.id === 'inhale'
    ? BREATHING_PHASES[0].durationMs
    : BREATHING_CYCLE_MS

  return {
    complete: false,
    cycle: Math.floor(elapsed / BREATHING_CYCLE_MS) + 1,
    phase: phase.id,
    instruction: phase.instruction,
    secondsRemaining: Math.ceil((phaseEnd - cyclePosition) / 1_000),
  }
}

export function stopCue(stepIndex, stepElapsedMs) {
  const index = Math.max(0, Math.min(STOP_STEPS.length - 1, Number(stepIndex) || 0))
  const elapsed = Math.max(0, Math.min(STOP_STEP_DURATION_MS, Number(stepElapsedMs) || 0))
  return {
    complete: false,
    step: index + 1,
    instruction: STOP_STEPS[index].instruction,
    secondsRemaining: Math.ceil((STOP_STEP_DURATION_MS - elapsed) / 1_000),
  }
}

const CRISIS_PATTERNS = [
  /\b(?:suicid(?:e|al)|kill myself|end my life|take my own life|wants? to die)\b/i,
  /\b(?:don't|do not) want to (?:live|be alive)\b/i,
  /\bself[- ]harm\b|\bhurt myself\b|\boverdose\b/i,
  /\b(?:harm|hurt|kill) someone\b/i,
  /\b(?:immediate danger|going to hurt myself)\b/i,
]

export function containsObviousCrisisLanguage(text) {
  return typeof text === 'string' && CRISIS_PATTERNS.some(pattern => pattern.test(text))
}
