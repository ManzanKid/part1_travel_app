import assert from 'node:assert/strict'
import test from 'node:test'
import {
  BREATHING_CYCLES,
  BREATHING_DURATION_MS,
  SKILL_IDS,
  STOP_DURATION_MS,
  STOP_STEPS,
  STOP_STEP_DURATION_MS,
  breathingCue,
  containsObviousCrisisLanguage,
  isSkillId,
  stopCue,
} from '../src/pausepathRules.mjs'

test('breathing uses six four-second inhales and six six-second exhales', () => {
  assert.equal(BREATHING_CYCLES, 6)
  assert.equal(BREATHING_DURATION_MS, 60_000)
  assert.ok(BREATHING_DURATION_MS < 90_000)
  assert.deepEqual(
    [breathingCue(0).phase, breathingCue(3_999).secondsRemaining,
      breathingCue(4_000).phase, breathingCue(9_999).secondsRemaining,
      breathingCue(10_000).cycle],
    ['inhale', 1, 'exhale', 1, 2],
  )
  assert.equal(breathingCue(60_000).complete, true)
})

test('STOP steps appear in the required order and target one minute', () => {
  assert.deepEqual(STOP_STEPS.map(step => step.id), ['stop', 'step-back', 'observe', 'proceed'])
  assert.deepEqual(STOP_STEPS.map(step => step.instruction), [
    'Stop.',
    'Take a step back.',
    'Observe what is happening internally and externally.',
    'Proceed mindfully.',
  ])
  assert.equal(STOP_STEP_DURATION_MS, 15_000)
  assert.equal(STOP_DURATION_MS, 60_000)
  assert.ok(STOP_DURATION_MS < 90_000)
  assert.equal(stopCue(2, 0).instruction, STOP_STEPS[2].instruction)
})

test('only breathing and STOP are valid skill IDs', () => {
  assert.deepEqual(SKILL_IDS, ['breathing', 'stop'])
  assert.equal(isSkillId('breathing'), true)
  assert.equal(isSkillId('stop'), true)
  assert.equal(isSkillId('therapy'), false)
})

test('limited crisis phrase check catches obvious wording without claiming risk assessment', () => {
  assert.equal(containsObviousCrisisLanguage('A fictional character wants to end my life'), true)
  assert.equal(containsObviousCrisisLanguage('My fictional character has a difficult day'), false)
})
