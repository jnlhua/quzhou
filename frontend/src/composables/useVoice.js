/**
 * useVoice.js — 讯飞语音识别 (ASR) + 语音合成 (TTS) 组合式函数
 *
 * ASR：麦克风录音 → Web Audio API 16kHz PCM → WebSocket 实时识别
 * TTS：文本 → WebSocket 获取 MP3 音频 → HTMLAudioElement 播放/暂停/重播
 */

import { ref, onUnmounted } from 'vue'

// ═══════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════

/** 将 Int16Array PCM 数据编码为 base64 字符串 */
function pcmToBase64(pcm) {
  const bytes = new Uint8Array(pcm.buffer)
  let binary = ''
  const chunkSize = 8192
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode.apply(
      null,
      bytes.subarray(i, i + chunkSize)
    )
  }
  return btoa(binary)
}

/** 简易 Markdown → 纯文本（用于 TTS 朗读） */
function stripMarkdown(text) {
  return text
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/~~(.+?)~~/g, '$1')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\[(.+?)\]\(.+?\)/g, '$1')
    .replace(/!\[.*?\]\(.+?\)/g, '')
    .replace(/^>\s*/gm, '')
    .replace(/^[-*+]\s+/gm, '')
    .replace(/^\d+\.\s+/gm, '')
    .replace(/\|/g, '')
    .replace(/^[-=]{3,}$/gm, '')
    .replace(/「来源：.+?」/g, '')
    .replace(/\n+/g, '，')
    .replace(/\s+/g, ' ')
    .trim()
}

// ═══════════════════════════════════════
// ASR — 语音识别
// ═══════════════════════════════════════

const isRecording = ref(false)
const asrError = ref('')

let _ws = null
let _mediaStream = null
let _audioCtx = null
let _source = null
let _processor = null
let _sendTimer = null
let _firstFrame = true
let _audioBuffer = []
let _prefixText = '' // 录音前输入框已有内容
let _sentenceMap = {} // { sn: "该句子的最终文本" }
let _lastSn = -1 // 上一个最终结果的句子编号

async function startRecording(inputTextRef) {
  try {
    asrError.value = ''
    _firstFrame = true
    _audioBuffer = []
    _prefixText = inputTextRef.value
    _sentenceMap = {}
    _lastSn = -1

    // 1. 请求麦克风权限
    _mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, sampleRate: 16000 }
    })

    // 2. 创建 AudioContext（目标 16kHz）
    _audioCtx = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000
    })
    const actualRate = _audioCtx.sampleRate

    // 3. 音频处理管线
    _source = _audioCtx.createMediaStreamSource(_mediaStream)
    _processor = _source.context.createScriptProcessor(4096, 1, 1)

    _processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0)
      // 降采样到 16kHz（如果 AudioContext 原生采样率更高）
      const ratio = actualRate / 16000
      const newLength = Math.round(inputData.length / ratio)
      const result = new Int16Array(newLength)
      for (let i = 0; i < newLength; i++) {
        const idx = Math.min(Math.floor(i * ratio), inputData.length - 1)
        const s = Math.max(-1, Math.min(1, inputData[idx]))
        result[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
      }
      _audioBuffer.push(result)
    }

    _source.connect(_processor)
    _processor.connect(_audioCtx.destination)

    // 4. 获取讯飞 ASR WebSocket URL + appId
    const resp = await fetch('/api/voice/asr-url')
    const { url, appId } = await resp.json()

    // 5. 建立 WebSocket 连接
    _ws = new WebSocket(url)

    _ws.onopen = () => {
      // 开始定时发送音频帧（~200ms/帧）
      _sendTimer = setInterval(() => {
        if (_audioBuffer.length > 0 && _ws && _ws.readyState === WebSocket.OPEN) {
          const chunk = _audioBuffer.shift()
          const b64 = pcmToBase64(chunk)

          if (_firstFrame) {
            _ws.send(JSON.stringify({
              data: {
                status: 0,
                format: 'audio/L16;rate=16000',
                encoding: 'raw',
                audio: b64
              },
              common: { app_id: appId },
              business: {
                language: 'zh_cn',
                domain: 'iat',
                accent: 'mandarin'
              }
            }))
            _firstFrame = false
          } else {
            _ws.send(JSON.stringify({
              data: { status: 1, format: 'audio/L16;rate=16000', encoding: 'raw', audio: b64 }
            }))
          }
        }
      }, 200)
    }

    _ws.onmessage = (event) => {
      const res = JSON.parse(event.data)
      if (res.code !== 0) {
        console.error('ASR error:', res.code, res.message)
        return
      }

      const result = res.data?.result
      if (!result) return

      // 拼接本轮识别到的文本
      let text = ''
      for (const ws of result.ws || []) {
        for (const cw of ws.cw || []) {
          text += cw.w || ''
        }
      }

      // 调试日志：追踪每条服务端消息
      console.log(`[ASR] sn=${result.sn} status=${result.status} text="${text}"`)

      if (text) {
        if (result.status === 2) {
          // ★ 讯飞 status=2 可能只返回增量标点，追加而非覆盖 ★
          _sentenceMap[result.sn] = (_sentenceMap[result.sn] || '') + text
          _lastSn = result.sn
          // 拼接所有已完成句子
          const finalText = Object.keys(_sentenceMap)
            .sort((a, b) => Number(a) - Number(b))
            .map(sn => _sentenceMap[sn])
            .join('')
          console.log(`[ASR] 最终 → sentenceMap:`, _sentenceMap, `→ 显示: "${_prefixText + finalText}"`)
          inputTextRef.value = _prefixText + finalText
        } else {
          // ★ 中间结果也存入 _sentenceMap，供 status=2 追加标点时使用 ★
          _sentenceMap[result.sn] = text
          const finalText = Object.keys(_sentenceMap)
            .sort((a, b) => Number(a) - Number(b))
            .map(sn => _sentenceMap[sn])
            .join('')
          console.log(`[ASR] 中间 → sentenceMap:`, _sentenceMap, `→ 显示: "${_prefixText + finalText}"`)
          inputTextRef.value = _prefixText + finalText
        }
      }
    }

    _ws.onerror = (e) => {
      console.error('ASR WebSocket error:', e)
      asrError.value = '语音识别连接失败'
      stopRecording()
    }

    _ws.onclose = () => {
      // WebSocket 关闭时清理资源
      _cleanupASR()
    }

    isRecording.value = true
  } catch (err) {
    console.error('ASR init error:', err)
    asrError.value = err.name === 'NotAllowedError'
      ? '请允许麦克风权限'
      : '麦克风初始化失败'
    _cleanupASR()
  }
}

function stopRecording() {
  if (_ws && _ws.readyState === WebSocket.OPEN) {
    // 发送最后一帧（status=2）通知服务端结束
    _ws.send(JSON.stringify({
      data: { status: 2, format: 'audio/L16;rate=16000', encoding: 'raw', audio: '' }
    }))
  }

  isRecording.value = false

  // 停止音频采集（但保留 WebSocket 等待最终结果）
  if (_sendTimer) { clearInterval(_sendTimer); _sendTimer = null }
  if (_processor) { try { _processor.disconnect() } catch (e) {} }
  if (_source) { try { _source.disconnect() } catch (e) {} }
  if (_mediaStream) { _mediaStream.getTracks().forEach(t => t.stop()); _mediaStream = null }
  if (_audioCtx && _audioCtx.state !== 'closed') {
    try { _audioCtx.close() } catch (e) {}
  }

  // 2 秒后强制关闭 WebSocket（兜底）
  setTimeout(() => {
    if (_ws) {
      try { _ws.close() } catch (e) {}
      _ws = null
    }
  }, 2000)
}

function _cleanupASR() {
  if (_sendTimer) { clearInterval(_sendTimer); _sendTimer = null }
  if (_processor) { try { _processor.disconnect() } catch (e) {}; _processor = null }
  if (_source) { try { _source.disconnect() } catch (e) {}; _source = null }
  if (_mediaStream) { _mediaStream.getTracks().forEach(t => t.stop()); _mediaStream = null }
  if (_audioCtx && _audioCtx.state !== 'closed') {
    try { _audioCtx.close() } catch (e) {}
  }
  _audioCtx = null
  if (_ws && _ws.readyState !== WebSocket.CLOSED) {
    try { _ws.close() } catch (e) {}
  }
  _ws = null
  _firstFrame = true
  _audioBuffer = []
  _sentenceMap = {}
  _lastSn = -1
}

// ═══════════════════════════════════════
// TTS — 语音合成
// ═══════════════════════════════════════

const ttsState = ref('idle') // 'idle' | 'loading' | 'playing' | 'paused'
const speakingIndex = ref(-1) // 当前正在播报的消息索引

let _audioElement = null
let _audioBlob = null
let _cachedText = ''
let _cachedBlobUrl = null

/** 获取/创建音频播放器 */
function _getAudio() {
  if (!_audioBlob) return null
  if (!_cachedBlobUrl) {
    _cachedBlobUrl = URL.createObjectURL(_audioBlob)
  }
  if (!_audioElement) {
    _audioElement = new Audio(_cachedBlobUrl)
    _audioElement.onended = () => {
      ttsState.value = 'idle'
      speakingIndex.value = -1
      _stopAndCleanupAudio()
    }
  }
  return _audioElement
}

/** 停止播放并清理所有音频资源 */
function _stopAndCleanupAudio() {
  if (_audioElement) {
    _audioElement.pause()
    _audioElement = null
  }
  if (_cachedBlobUrl) {
    URL.revokeObjectURL(_cachedBlobUrl)
    _cachedBlobUrl = null
  }
  _audioBlob = null
}

/**
 * 语音播报 / 暂停 / 重播
 * @param {string} text     - 要播报的文本（Markdown 格式，内部会自动去除标记）
 * @param {number} msgIndex - 消息在列表中的索引（用于标识当前播报的是哪条消息）
 */
async function handleSpeak(text, msgIndex) {
  const plainText = stripMarkdown(text)
  if (!plainText) return

  const isSameMsg = msgIndex === speakingIndex.value

  // 正在播放同一条消息 → 暂停
  if (ttsState.value === 'playing' && isSameMsg) {
    const audio = _getAudio()
    if (audio) audio.pause()
    ttsState.value = 'paused'
    return
  }

  // 已暂停同一条消息 → 恢复播放
  if (ttsState.value === 'paused' && isSameMsg) {
    const audio = _getAudio()
    if (audio) {
      audio.play().catch(() => {})
      ttsState.value = 'playing'
    }
    return
  }

  // 不同消息，或 idle 状态 → 停止旧播放，开始新播报
  _stopAndCleanupAudio()

  // idle → 开始播报
  ttsState.value = 'loading'
  speakingIndex.value = msgIndex
  _cachedText = plainText

  try {
    // 1. 获取讯飞 TTS WebSocket URL + 请求体
    const resp = await fetch('/api/voice/tts-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: plainText })
    })
    const { url, body } = await resp.json()

    // 2. 连接 WebSocket 接收音频
    const audioChunks = []
    await new Promise((resolve, reject) => {
      const ws = new WebSocket(url)
      ws.onopen = () => ws.send(JSON.stringify(body))
      ws.onmessage = (event) => {
        try {
          const res = JSON.parse(event.data)
          const code = res.header?.code ?? res.code
          if (code !== 0) { reject(new Error(`TTS error: ${code}`)); return }
          const audioData = res.data?.audio ?? res.payload?.audio?.audio
          if (audioData) {
            audioChunks.push(atob(audioData))
          }
          const status = res.data?.status ?? res.payload?.audio?.status
          if (status === 2) resolve()
        } catch (e) { reject(e) }
      }
      ws.onerror = (e) => reject(e)
      ws.onclose = () => resolve()
    })

    // 3. 拼接音频 → Blob
    const totalLen = audioChunks.reduce((s, c) => s + c.length, 0)
    if (totalLen === 0) { ttsState.value = 'idle'; speakingIndex.value = -1; return }

    const uint8 = new Uint8Array(totalLen)
    let offset = 0
    for (const chunk of audioChunks) {
      for (let i = 0; i < chunk.length; i++) {
        uint8[offset++] = chunk.charCodeAt(i)
      }
    }
    _audioBlob = new Blob([uint8], { type: 'audio/mp3' })

    // 4. 播放
    const audio = _getAudio()
    if (audio) {
      await audio.play()
      ttsState.value = 'playing'
    }
  } catch (err) {
    console.error('TTS error:', err)
    ttsState.value = 'idle'
    speakingIndex.value = -1
  }
}

/** 组件卸载时清理所有资源 */
function _cleanup() {
  _cleanupASR()
  if (_audioElement) { _audioElement.pause(); _audioElement = null }
  if (_cachedBlobUrl) { URL.revokeObjectURL(_cachedBlobUrl); _cachedBlobUrl = null }
  _audioBlob = null
}

// ═══════════════════════════════════════
// 导出
// ═══════════════════════════════════════

export function useVoice() {
  onUnmounted(_cleanup)

  return {
    // ASR
    isRecording,
    asrError,
    startRecording,
    stopRecording,
    // TTS
    ttsState,
    speakingIndex,
    handleSpeak,
    stripMarkdown,
  }
}