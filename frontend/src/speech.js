/**
 * Pi Vaani Soundbox Speech & Audio Synthesis Controller
 * 
 * Handles real-time audio playback for the virtual soundbox.
 * Priority 1: Plays server-generated Sarvam AI neural audio (if audio_url exists).
 * Priority 2: Falls back to Web Speech API (window.speechSynthesis).
 */

const BACKEND_BASE = 'http://localhost:8000'

let currentAudio = null

export function playSoundboxVoice({ text, audio_url, lang = 'hi-IN', onStart, onEnd }) {
  if (typeof window === 'undefined') return

  // Stop any currently playing audio
  if (currentAudio) {
    try {
      currentAudio.pause()
      currentAudio.currentTime = 0
    } catch (e) {
      // ignore
    }
    currentAudio = null
  }

  // Cancel any browser speech synthesis in progress
  if ('speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel()
    } catch (e) {
      // ignore
    }
  }

  // Priority 1: High-fidelity Sarvam AI Neural Voice Audio
  if (audio_url) {
    const fullAudioUrl = audio_url.startsWith('http')
      ? audio_url
      : `${BACKEND_BASE}${audio_url.startsWith('/') ? '' : '/'}${audio_url}`

    const audio = new Audio(fullAudioUrl)
    currentAudio = audio

    if (onStart) onStart()

    audio.onended = () => {
      currentAudio = null
      if (onEnd) onEnd()
    }

    audio.onerror = (err) => {
      console.warn('[Soundbox Audio] Error loading server audio, falling back to Web Speech API:', err)
      currentAudio = null
      speakWebSpeech(text, lang, onStart, onEnd)
    }

    audio.play().catch((err) => {
      console.warn('[Soundbox Audio] Autoplay blocked or playback failed, using Web Speech:', err)
      currentAudio = null
      speakWebSpeech(text, lang, onStart, onEnd)
    })
    return
  }

  // Priority 2: Native Browser Web Speech API
  speakWebSpeech(text, lang, onStart, onEnd)
}

function speakWebSpeech(text, lang, onStart, onEnd) {
  if (typeof window === 'undefined' || !('speechSynthesis' in window) || !text) {
    if (onEnd) onEnd()
    return
  }

  try {
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = lang || 'hi-IN'
    utterance.rate = 1.0
    utterance.pitch = 1.0

    if (onStart) {
      utterance.onstart = () => onStart()
    }

    utterance.onend = () => {
      if (onEnd) onEnd()
    }

    utterance.onerror = () => {
      if (onEnd) onEnd()
    }

    window.speechSynthesis.speak(utterance)
  } catch (err) {
    console.error('[Soundbox Speech] Web Speech API failed:', err)
    if (onEnd) onEnd()
  }
}
