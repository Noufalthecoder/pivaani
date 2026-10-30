/**
 * Pi Vaani Soundbox Speech & Audio Synthesis Controller
 *
 * Handles real-time audio playback for the virtual soundbox.
 * Priority 1: Plays server-generated Sarvam AI neural audio (if audio_url exists).
 * Priority 2: Falls back to Web Speech API (window.speechSynthesis).
 *
 * Clips are queued: a Case opening sends a customer clip then a merchant clip,
 * and the second must not cut off the first.
 */

const BACKEND_BASE = 'http://localhost:8000'

const queue = []
let isPlaying = false
let currentAudio = null
let currentItem = null

// Chrome populates voices asynchronously; prime the list as early as possible
let voicesReady = null
function loadVoices() {
  if (voicesReady) return voicesReady
  voicesReady = new Promise((resolve) => {
    const synth = window.speechSynthesis
    if (synth.getVoices().length > 0) return resolve()
    const done = () => {
      synth.removeEventListener('voiceschanged', done)
      resolve()
    }
    synth.addEventListener('voiceschanged', done)
    setTimeout(done, 1000) // some browsers never fire voiceschanged
  })
  return voicesReady
}
if (typeof window !== 'undefined' && 'speechSynthesis' in window) loadVoices()

// Only one browser tab may be the audible soundbox; with several demo tabs open
// they would otherwise all play the same clip slightly out of sync (an echo).
// Web Locks hands the role to the next tab when the current one closes. State
// lives on window so a hot-reloaded copy of this module reuses the tab's lock.
function isAudibleTab() {
  if (!window.__pivaaniSoundbox) {
    const state = { audible: !(navigator.locks && navigator.locks.request) }
    window.__pivaaniSoundbox = state
    if (!state.audible) {
      navigator.locks.request('pivaani-soundbox-audio', () => {
        state.audible = true
        return new Promise(() => {}) // hold the lock for the tab's lifetime
      })
    }
  }
  return window.__pivaaniSoundbox.audible
}
if (typeof window !== 'undefined') isAudibleTab()

export function playSoundboxVoice({ text, audio_url, lang = 'hi-IN', onStart, onEnd }) {
  if (typeof window === 'undefined') return
  if (!isAudibleTab()) {
    // Silent tab: keep captions and the LED in step without making sound
    if (onStart) onStart()
    setTimeout(() => onEnd && onEnd(), 1500 + text.length * 60)
    return
  }
  // Drop a duplicate of a line that is already playing or waiting, so a
  // repeated event can never make the soundbox say the same thing twice
  const isDuplicate = (item) => item && item.text === text && item.lang === lang
  if (isDuplicate(currentItem) || queue.some(isDuplicate)) return
  queue.push({ text, audio_url, lang, onStart, onEnd })
  if (!isPlaying) playNext()
}

export function stopSoundboxVoice() {
  queue.length = 0
  currentItem = null
  if (currentAudio) {
    try {
      currentAudio.pause()
    } catch (e) {
      // ignore
    }
    currentAudio = null
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel()
    } catch (e) {
      // ignore
    }
  }
  isPlaying = false
}

function playNext() {
  const item = queue.shift()
  currentItem = item || null
  if (!item) {
    isPlaying = false
    return
  }
  isPlaying = true

  let finished = false
  const finish = () => {
    // Ignore late callbacks from a clip that stopSoundboxVoice() already cut off
    if (finished || currentItem !== item) return
    finished = true
    currentAudio = null
    if (item.onEnd) item.onEnd()
    playNext()
  }

  if (item.audio_url) {
    playServerAudio(item, finish)
  } else {
    speakWebSpeech(item, finish)
  }
}

// Priority 1: High-fidelity Sarvam AI Neural Voice Audio
function playServerAudio(item, finish) {
  const fullAudioUrl = item.audio_url.startsWith('http')
    ? item.audio_url
    : `${BACKEND_BASE}${item.audio_url.startsWith('/') ? '' : '/'}${item.audio_url}`

  const audio = new Audio(fullAudioUrl)
  currentAudio = audio

  // onerror and a rejected play() can both fire; fall back only once
  let fellBack = false
  const fallBack = (err) => {
    // A clip we stopped on purpose (Stop / Reset) rejects with AbortError; don't re-speak it
    if (fellBack || currentItem !== item) return
    fellBack = true
    if (err?.name === 'AbortError') {
      finish() // interrupted, not broken: move on rather than speak it again
      return
    }
    console.warn('[Soundbox Audio] Server audio failed, falling back to Web Speech API:', err)
    speakWebSpeech(item, finish)
  }

  audio.onplay = () => {
    if (item.onStart) item.onStart()
  }
  audio.onended = finish
  audio.onerror = fallBack
  audio.play().catch(fallBack)
}

// Priority 2: Native Browser Web Speech API
async function speakWebSpeech(item, finish) {
  const { text, lang, onStart } = item
  if (!('speechSynthesis' in window) || !text) {
    finish()
    return
  }

  try {
    await loadVoices()

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = lang || 'hi-IN'
    utterance.rate = 1.0
    utterance.pitch = 1.0
    // Pick an installed voice for the language; otherwise the browser may read Tamil/Hindi with an English voice
    const voices = window.speechSynthesis.getVoices()
    const prefix = utterance.lang.split('-')[0]
    const voice =
      voices.find((v) => v.lang === utterance.lang) ||
      voices.find((v) => v.lang.replace('_', '-').startsWith(prefix))
    if (voice) utterance.voice = voice

    // Chrome sometimes never fires onend; don't let the queue stall forever
    const watchdog = setTimeout(finish, 4000 + text.length * 150)
    const done = () => {
      clearTimeout(watchdog)
      finish()
    }

    utterance.onstart = () => {
      if (onStart) onStart()
    }
    utterance.onend = done
    utterance.onerror = done

    window.speechSynthesis.speak(utterance)
  } catch (err) {
    console.error('[Soundbox Speech] Web Speech API failed:', err)
    finish()
  }
}
