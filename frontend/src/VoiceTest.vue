<template>
  <div class="test-page">
    <h1>语音模块测试</h1>
    <p class="subtitle">讯飞 ASR（语音识别）+ TTS（语音合成）逐步验证</p>

    <!-- Step 1: 麦克风测试 -->
    <section class="card">
      <h2>1. 麦克风权限 & 音频采集</h2>
      <button @click="testMic" :disabled="micTesting" class="btn primary">
        {{ micTesting ? '测试中...' : '测试麦克风' }}
      </button>
      <div class="status" :class="micStatus">{{ micStatusText }}</div>
      <div v-if="audioInfo" class="info">
        <span>采样率: {{ audioInfo.sampleRate }} Hz</span>
        <span>实际采样率: {{ audioInfo.actualRate }} Hz</span>
        <span>采集帧数: {{ audioInfo.frames }}</span>
        <span>PCM 数据量: {{ audioInfo.pcmSize }} bytes</span>
      </div>
    </section>

    <!-- Step 2: ASR 语音识别 -->
    <section class="card">
      <h2>2. 讯飞 ASR 语音识别</h2>
      <p class="desc">按下录音，对着麦克风说话，再次按下停止</p>
      <button
        @click="toggleASR"
        :disabled="!micReady"
        class="btn"
        :class="{ danger: asrRecording, primary: !asrRecording }"
      >
        {{ asrRecording ? '停止录音' : '开始录音' }}
      </button>
      <div v-if="!micReady" class="hint">请先通过 Step 1 测试麦克风</div>
      <div class="status" :class="asrStatus">{{ asrStatusText }}</div>
      <div v-if="asrText" class="result-box">
        <label>识别结果：</label>
        <div class="result-text">{{ asrText }}</div>
      </div>
      <div v-if="asrRealtime" class="result-box realtime">
        <label>实时识别：</label>
        <div class="result-text">{{ asrRealtime }}</div>
      </div>
    </section>

    <!-- Step 3: TTS 语音合成 -->
    <section class="card">
      <h2>3. 讯飞 TTS 语音合成</h2>
      <textarea
        v-model="ttsText"
        placeholder="输入要合成的文字..."
        class="tts-input"
        rows="3"
      ></textarea>
      <div class="btn-row">
        <button @click="testTTS" :disabled="!ttsText.trim() || ttsLoading" class="btn primary">
          {{ ttsLoading ? '合成中...' : '合成并播放' }}
        </button>
        <button v-if="ttsHasAudio" @click="replayTTS" class="btn secondary">
          重新播放
        </button>
      </div>
      <div class="status" :class="ttsStatus">{{ ttsStatusText }}</div>
      <div v-if="ttsAudioInfo" class="info">
        <span>音频大小: {{ ttsAudioInfo.size }} bytes</span>
        <span>格式: MP3</span>
      </div>
    </section>

    <!-- 日志面板 -->
    <section class="card log-card">
      <div class="log-header">
        <h2>运行日志</h2>
        <button @click="logs = []" class="btn small">清空</button>
      </div>
      <div class="log-panel" ref="logPanel">
        <div v-for="(log, i) in logs" :key="i" :class="['log-line', log.level]">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-tag">[{{ log.tag }}]</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
        <div v-if="logs.length === 0" class="log-empty">暂无日志</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, nextTick, onUnmounted } from 'vue'

// ═══════════════════════════════════════
// 日志系统
// ═══════════════════════════════════════
const logs = ref([])
const logPanel = ref(null)

function log(tag, msg, level = 'info') {
  const now = new Date()
  const time = now.toLocaleTimeString('zh-CN', { hour12: false }) + '.' + String(now.getMilliseconds()).padStart(3, '0')
  logs.value.push({ time, tag, msg, level })
  nextTick(() => {
    if (logPanel.value) {
      logPanel.value.scrollTop = logPanel.value.scrollHeight
    }
  })
}

// ═══════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════
function pcmToBase64(pcm) {
  const bytes = new Uint8Array(pcm.buffer)
  let binary = ''
  const chunkSize = 8192
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize))
  }
  return btoa(binary)
}

// ═══════════════════════════════════════
// Step 1: 麦克风测试
// ═══════════════════════════════════════
const micTesting = ref(false)
const micStatus = ref('')
const micStatusText = ref('')
const micReady = ref(false)
const audioInfo = ref(null)

async function testMic() {
  micTesting.value = true
  micStatus.value = ''
  micStatusText.value = '正在请求麦克风权限...'
  audioInfo.value = null
  log('MIC', '请求 getUserMedia 权限...')

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }
    })
    log('MIC', '麦克风权限获取成功')

    const AudioCtx = window.AudioContext || window.webkitAudioContext
    if (!AudioCtx) {
      throw new Error('浏览器不支持 AudioContext')
    }
    const ctx = new AudioCtx({ sampleRate: 16000 })
    const actualRate = ctx.sampleRate
    log('MIC', `AudioContext 创建成功，目标采样率 16000，实际: ${actualRate}`)

    const source = ctx.createMediaStreamSource(stream)
    const processor = source.context.createScriptProcessor(4096, 1, 1)
    log('MIC', 'ScriptProcessor 创建成功 (bufferSize=4096)')

    let frameCount = 0
    let totalPcmBytes = 0
    micStatusText.value = '正在采集 2 秒音频...'

    await new Promise((resolve) => {
      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0)
        const ratio = actualRate / 16000
        const newLen = Math.round(input.length / ratio)
        const pcm = new Int16Array(newLen)
        for (let i = 0; i < newLen; i++) {
          const idx = Math.min(Math.floor(i * ratio), input.length - 1)
          const s = Math.max(-1, Math.min(1, input[idx]))
          pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
        }
        totalPcmBytes += pcm.byteLength
        frameCount++
      }

      source.connect(processor)
      processor.connect(ctx.destination)
      log('MIC', '音频管线已连接，开始采集...')

      setTimeout(() => {
        processor.disconnect()
        source.disconnect()
        stream.getTracks().forEach(t => t.stop())
        ctx.close()
        resolve()
      }, 2000)
    })

    audioInfo.value = {
      sampleRate: 16000,
      actualRate: actualRate,
      frames: frameCount,
      pcmSize: totalPcmBytes,
    }

    log('MIC', `采集完成: ${frameCount} 帧, ${totalPcmBytes} bytes PCM 数据`)

    if (frameCount > 0 && totalPcmBytes > 0) {
      micStatus.value = 'success'
      micStatusText.value = `麦克风正常！采集了 ${frameCount} 帧音频数据`
      micReady.value = true
      log('MIC', '麦克风测试通过', 'success')
    } else {
      micStatus.value = 'error'
      micStatusText.value = '未采集到音频数据'
      log('MIC', '未采集到数据', 'error')
    }
  } catch (err) {
    micStatus.value = 'error'
    if (err.name === 'NotAllowedError') {
      micStatusText.value = '麦克风权限被拒绝，请在浏览器设置中允许麦克风'
      log('MIC', '权限被拒绝: ' + err.message, 'error')
    } else if (err.name === 'NotFoundError') {
      micStatusText.value = '未找到麦克风设备'
      log('MIC', '未找到麦克风: ' + err.message, 'error')
    } else {
      micStatusText.value = '麦克风初始化失败: ' + err.message
      log('MIC', '初始化失败: ' + err.name + ' - ' + err.message, 'error')
    }
    console.error('Mic test error:', err)
  } finally {
    micTesting.value = false
  }
}

// ═══════════════════════════════════════
// Step 2: ASR 语音识别
// ═══════════════════════════════════════
const asrRecording = ref(false)
const asrStatus = ref('')
const asrStatusText = ref('')
const asrText = ref('')
const asrRealtime = ref('')

let _asrWs = null
let _asrStream = null
let _asrCtx = null
let _asrProcessor = null
let _asrSource = null
let _asrTimer = null
let _asrFirstFrame = true
let _asrBuffer = []
let _asrAppId = ''
let _sentenceMap = {}

async function toggleASR() {
  if (asrRecording.value) {
    stopASR()
  } else {
    await startASR()
  }
}

async function startASR() {
  asrText.value = ''
  asrRealtime.value = ''
  asrStatus.value = ''
  asrStatusText.value = '准备中...'
  _asrFirstFrame = true
  _asrBuffer = []
  _sentenceMap = {}

  log('ASR', '开始录音流程...')

  try {
    // 1. 获取麦克风
    _asrStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }
    })
    log('ASR', '麦克风已打开')

    // 2. AudioContext
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    _asrCtx = new AudioCtx({ sampleRate: 16000 })
    const actualRate = _asrCtx.sampleRate
    log('ASR', `AudioContext 已创建 (实际采样率: ${actualRate})`)

    // 3. 音频处理
    _asrSource = _asrCtx.createMediaStreamSource(_asrStream)
    _asrProcessor = _asrSource.context.createScriptProcessor(4096, 1, 1)

    _asrProcessor.onaudioprocess = (e) => {
      const input = e.inputBuffer.getChannelData(0)
      const ratio = actualRate / 16000
      const newLen = Math.round(input.length / ratio)
      const pcm = new Int16Array(newLen)
      for (let i = 0; i < newLen; i++) {
        const idx = Math.min(Math.floor(i * ratio), input.length - 1)
        const s = Math.max(-1, Math.min(1, input[idx]))
        pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
      }
      _asrBuffer.push(pcm)
    }

    _asrSource.connect(_asrProcessor)
    _asrProcessor.connect(_asrCtx.destination)
    log('ASR', '音频管线已连接')

    // 4. 获取 WebSocket URL
    asrStatusText.value = '连接讯飞 ASR 服务...'
    log('ASR', '请求后端 /api/voice/asr-url...')

    const resp = await fetch('/api/voice/asr-url')
    if (!resp.ok) throw new Error(`后端返回 ${resp.status}: ${await resp.text()}`)
    const { url, appId } = await resp.json()
    _asrAppId = appId
    log('ASR', `获取到 WS URL (appId=${appId})`)
    log('ASR', `URL: ${url.substring(0, 80)}...`)

    // 5. WebSocket 连接
    asrStatusText.value = '连接 WebSocket...'
    _asrWs = new WebSocket(url)

    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('WebSocket 连接超时 (10s)')), 10000)

      _asrWs.onopen = () => {
        clearTimeout(timeout)
        log('ASR', 'WebSocket 连接成功！')
        resolve()
      }
      _asrWs.onerror = () => {
        clearTimeout(timeout)
        reject(new Error('WebSocket 连接失败'))
      }
    })

    // 6. 开始发送音频帧
    _asrTimer = setInterval(() => {
      if (_asrBuffer.length > 0 && _asrWs && _asrWs.readyState === WebSocket.OPEN) {
        const chunk = _asrBuffer.shift()
        const b64 = pcmToBase64(chunk)

        if (_asrFirstFrame) {
          const frame = {
            data: { status: 0, format: 'audio/L16;rate=16000', encoding: 'raw', audio: b64 },
            common: { app_id: _asrAppId },
            business: { language: 'zh_cn', domain: 'iat', accent: 'mandarin' }
          }
          _asrWs.send(JSON.stringify(frame))
          _asrFirstFrame = false
          log('ASR', `发送首帧 (audio ${b64.length} chars)`)
        } else {
          _asrWs.send(JSON.stringify({
            data: { status: 1, format: 'audio/L16;rate=16000', encoding: 'raw', audio: b64 }
          }))
        }
      }
    }, 200)

    // 7. 处理识别结果
    _asrWs.onmessage = (event) => {
      try {
        const res = JSON.parse(event.data)
        if (res.header && res.header.code !== 0) {
          log('ASR', `服务端错误 code=${res.header.code}: ${res.header.message}`, 'error')
          asrStatus.value = 'error'
          asrStatusText.value = `识别错误: ${res.header.message} (code=${res.header.code})`
          return
        }
        if (res.code !== undefined && res.code !== 0) {
          log('ASR', `服务端错误 code=${res.code}: ${res.message}`, 'error')
          return
        }

        const result = res.data?.result
        if (!result) return

        let text = ''
        for (const ws of result.ws || []) {
          for (const cw of ws.cw || []) {
            text += cw.w || ''
          }
        }

        if (text) {
          if (result.status === 2) {
            // ★ 讯飞 status=2 可能只返回增量标点，追加而非覆盖 ★
            _sentenceMap[result.sn] = (_sentenceMap[result.sn] || '') + text
            asrRealtime.value = ''
            const allText = Object.keys(_sentenceMap)
              .sort((a, b) => Number(a) - Number(b))
              .map(sn => _sentenceMap[sn])
              .join('')
            asrText.value = allText
            log('ASR', `句子最终(sn=${result.sn}): "${text}" -> 全部: "${allText}"`, 'success')
          } else {
            // ★ 中间结果也存入 _sentenceMap，供 status=2 追加标点时使用 ★
            _sentenceMap[result.sn] = text
            const allText = Object.keys(_sentenceMap)
              .sort((a, b) => Number(a) - Number(b))
              .map(sn => _sentenceMap[sn])
              .join('')
            asrRealtime.value = text
            asrText.value = allText
          }
        }

        if (result.status === 2) {
          log('ASR', `收到 status=2 (一句话结束), sn=${result.sn}`)
        }
      } catch (e) {
        log('ASR', `解析消息失败: ${e.message}`, 'error')
      }
    }

    _asrWs.onclose = (event) => {
      log('ASR', `WebSocket 关闭 (code=${event.code}, reason=${event.reason})`)
    }

    asrRecording.value = true
    asrStatus.value = 'success'
    asrStatusText.value = '录音中... 对着麦克风说话吧！'
    log('ASR', '录音已开始', 'success')

  } catch (err) {
    asrStatus.value = 'error'
    asrStatusText.value = 'ASR 启动失败: ' + err.message
    log('ASR', '启动失败: ' + err.message, 'error')
    console.error('ASR start error:', err)
    cleanupASR()
  }
}

function stopASR() {
  log('ASR', '停止录音...')
  asrRecording.value = false
  asrStatusText.value = '正在停止...'

  // 发送最后一帧
  if (_asrWs && _asrWs.readyState === WebSocket.OPEN) {
    _asrWs.send(JSON.stringify({
      data: { status: 2, format: 'audio/L16;rate=16000', encoding: 'raw', audio: '' }
    }))
    log('ASR', '已发送结束帧 (status=2)')
  }

  // 停止音频采集
  if (_asrTimer) { clearInterval(_asrTimer); _asrTimer = null }
  if (_asrProcessor) { try { _asrProcessor.disconnect() } catch (e) {} }
  if (_asrSource) { try { _asrSource.disconnect() } catch (e) {} }
  if (_asrStream) { _asrStream.getTracks().forEach(t => t.stop()); _asrStream = null }
  if (_asrCtx && _asrCtx.state !== 'closed') { try { _asrCtx.close() } catch (e) {} }

  // 等 2 秒让服务端返回最终结果
  setTimeout(() => {
    if (_asrWs) { try { _asrWs.close() } catch (e) {}; _asrWs = null }
    asrStatusText.value = asrText.value ? `识别完成: "${asrText.value}"` : '录音已停止（未识别到文字）'
    log('ASR', asrText.value ? '录音结束，有识别结果' : '录音结束，无识别结果', asrText.value ? 'success' : 'warn')
  }, 2000)
}

function cleanupASR() {
  if (_asrTimer) { clearInterval(_asrTimer); _asrTimer = null }
  if (_asrProcessor) { try { _asrProcessor.disconnect() } catch (e) {}; _asrProcessor = null }
  if (_asrSource) { try { _asrSource.disconnect() } catch (e) {}; _asrSource = null }
  if (_asrStream) { _asrStream.getTracks().forEach(t => t.stop()); _asrStream = null }
  if (_asrCtx && _asrCtx.state !== 'closed') { try { _asrCtx.close() } catch (e) {} }
  _asrCtx = null
  if (_asrWs) { try { _asrWs.close() } catch (e) {}; _asrWs = null }
  _asrFirstFrame = true
  _asrBuffer = []
  _sentenceMap = {}
  asrRecording.value = false
}

// ═══════════════════════════════════════
// Step 3: TTS 语音合成
// ═══════════════════════════════════════
const ttsText = ref('你好，我是衢小游，你的衢州旅游智能向导。有什么可以帮你的吗？')
const ttsLoading = ref(false)
const ttsStatus = ref('')
const ttsStatusText = ref('')
const ttsHasAudio = ref(false)
const ttsAudioInfo = ref(null)
let _ttsBlob = null
let _ttsAudio = null

async function testTTS() {
  ttsLoading.value = true
  ttsStatus.value = ''
  ttsStatusText.value = '正在连接讯飞 TTS 服务...'
  ttsHasAudio.value = false
  ttsAudioInfo.value = null
  _ttsBlob = null

  const text = ttsText.value.trim()
  log('TTS', `开始合成: "${text.substring(0, 50)}${text.length > 50 ? '...' : ''}"`)

  try {
    // 1. 获取 WebSocket URL + 请求体
    log('TTS', '请求后端 /api/voice/tts-url...')
    const resp = await fetch('/api/voice/tts-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    })
    if (!resp.ok) throw new Error(`后端返回 ${resp.status}: ${await resp.text()}`)
    const { url, body } = await resp.json()
    log('TTS', '获取到 WS URL')
    log('TTS', `URL: ${url.substring(0, 80)}...`)

    // 2. WebSocket 连接 + 发送请求
    ttsStatusText.value = '正在合成音频...'
    const ws = new WebSocket(url)

    const audioChunks = []
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('TTS WebSocket 超时 (15s)')), 15000)

      ws.onopen = () => {
        log('TTS', 'WebSocket 连接成功，发送合成请求')
        ws.send(JSON.stringify(body))
      }

      ws.onmessage = (event) => {
        try {
          const res = JSON.parse(event.data)
          const code = res.header?.code ?? res.code
          if (code !== 0) {
            reject(new Error(`TTS 错误 code=${code}: ${res.header?.message || res.message}`))
            return
          }
          const audioData = res.data?.audio ?? res.payload?.audio?.audio
          if (audioData) {
            audioChunks.push(audioData)
          }
          const status = res.data?.status ?? res.payload?.audio?.status
          if (status === 2) {
            clearTimeout(timeout)
            log('TTS', '收到合成完成信号 (status=2)')
            resolve()
          }
        } catch (e) {
          reject(e)
        }
      }

      ws.onerror = () => {
        clearTimeout(timeout)
        reject(new Error('TTS WebSocket 连接失败'))
      }

      ws.onclose = (event) => {
        clearTimeout(timeout)
        log('TTS', `WebSocket 关闭 (code=${event.code})`)
        resolve()
      }
    })

    // 3. 拼接音频
    const allBase64 = audioChunks.join('')
    log('TTS', `收到 ${audioChunks.length} 个音频块, 共 ${allBase64.length} base64字符`)

    if (allBase64.length === 0) {
      ttsStatus.value = 'error'
      ttsStatusText.value = '未收到音频数据'
      log('TTS', '未收到音频数据', 'error')
      return
    }

    const binaryStr = atob(allBase64)
    const totalLen = binaryStr.length
    const uint8 = new Uint8Array(totalLen)
    for (let i = 0; i < totalLen; i++) { uint8[i] = binaryStr.charCodeAt(i) }
    _ttsBlob = new Blob([uint8], { type: 'audio/mpeg' })
    ttsAudioInfo.value = { size: totalLen }
    ttsHasAudio.value = true

    log('TTS', `音频合成成功！大小: ${totalLen} bytes`, 'success')

    // 4. 播放
    await playTTS()

  } catch (err) {
    ttsStatus.value = 'error'
    ttsStatusText.value = 'TTS 失败: ' + err.message
    log('TTS', '合成失败: ' + err.message, 'error')
    console.error('TTS error:', err)
  } finally {
    ttsLoading.value = false
  }
}

async function playTTS() {
  if (!_ttsBlob) return
  ttsStatusText.value = '正在播放...'
  log('TTS', '开始播放音频')

  return new Promise((resolve) => {
    if (_ttsAudio) { _ttsAudio.pause(); _ttsAudio = null }
    const url = URL.createObjectURL(_ttsBlob)
    _ttsAudio = new Audio(url)
    _ttsAudio.onplay = () => {
      ttsStatus.value = 'success'
      ttsStatusText.value = '正在播放...'
    }
    _ttsAudio.onended = () => {
      ttsStatusText.value = '播放完成！可以点击"重新播放"再听一遍'
      URL.revokeObjectURL(url)
      _ttsAudio = null
      log('TTS', '播放完成', 'success')
      resolve()
    }
    _ttsAudio.onerror = (e) => {
      ttsStatus.value = 'error'
      ttsStatusText.value = '音频播放失败'
      log('TTS', '播放失败', 'error')
      resolve()
    }
    _ttsAudio.play().catch((err) => {
      ttsStatus.value = 'error'
      ttsStatusText.value = '播放失败: ' + err.message
      log('TTS', '播放异常: ' + err.message, 'error')
      resolve()
    })
  })
}

function replayTTS() {
  if (_ttsBlob) {
    playTTS()
  }
}

// 清理
onUnmounted(() => {
  cleanupASR()
  if (_ttsAudio) { _ttsAudio.pause(); _ttsAudio = null }
})
</script>

<style scoped>
.test-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 20px;
  font-family: 'Segoe UI', system-ui, sans-serif;
}

h1 {
  text-align: center;
  font-size: 28px;
  background: linear-gradient(135deg, #B5E61D, #00A2E8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  text-align: center;
  color: rgba(0,0,0,0.4);
  margin-bottom: 30px;
}

.card {
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.6);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.card h2 {
  font-size: 18px;
  margin: 0 0 12px 0;
  color: #2d3436;
}

.desc {
  color: rgba(0,0,0,0.45);
  font-size: 13px;
  margin-bottom: 12px;
}

.btn {
  padding: 10px 24px;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.25s ease;
}

.btn.primary {
  background: linear-gradient(135deg, #B5E61D, #00A2E8);
  color: #fff;
}

.btn.primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,162,232,0.3);
}

.btn.danger {
  background: linear-gradient(135deg, #e74c3c, #c0392b);
  color: #fff;
}

.btn.secondary {
  background: rgba(0,0,0,0.06);
  color: rgba(0,0,0,0.6);
}

.btn.small {
  padding: 4px 12px;
  font-size: 12px;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-row {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.hint {
  color: rgba(0,0,0,0.35);
  font-size: 12px;
  margin-top: 8px;
}

.status {
  margin-top: 10px;
  font-size: 13px;
  color: rgba(0,0,0,0.5);
}

.status.success {
  color: #22b54c;
}

.status.error {
  color: #e74c3c;
}

.status.warn {
  color: #f39c12;
}

.info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 10px;
  font-size: 12px;
  color: rgba(0,0,0,0.4);
}

.result-box {
  margin-top: 12px;
  padding: 12px 16px;
  background: rgba(0,0,0,0.03);
  border-radius: 10px;
  border: 1px solid rgba(0,0,0,0.06);
}

.result-box label {
  font-size: 12px;
  color: rgba(0,0,0,0.35);
  display: block;
  margin-bottom: 4px;
}

.result-box.realtime {
  border-color: rgba(181,230,29,0.3);
  background: rgba(181,230,29,0.05);
}

.result-text {
  font-size: 16px;
  color: #2d3436;
  font-weight: 500;
}

.tts-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid rgba(0,0,0,0.1);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 8px;
  outline: none;
}

.tts-input:focus {
  border-color: rgba(0,162,232,0.3);
  box-shadow: 0 0 0 3px rgba(181,230,29,0.1);
}

.log-card {
  max-height: 400px;
  display: flex;
  flex-direction: column;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.log-header h2 {
  margin: 0;
}

.log-panel {
  flex: 1;
  overflow-y: auto;
  max-height: 300px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  background: rgba(0,0,0,0.03);
  border-radius: 8px;
  padding: 10px;
}

.log-line {
  padding: 2px 0;
  display: flex;
  gap: 8px;
}

.log-line.error .log-msg { color: #e74c3c; }
.log-line.success .log-msg { color: #22b54c; }
.log-line.warn .log-msg { color: #f39c12; }

.log-time {
  color: rgba(0,0,0,0.3);
  flex-shrink: 0;
}

.log-tag {
  color: #00A2E8;
  font-weight: 600;
  flex-shrink: 0;
}

.log-msg {
  color: rgba(0,0,0,0.6);
  word-break: break-all;
}

.log-empty {
  text-align: center;
  color: rgba(0,0,0,0.25);
  padding: 20px;
}
</style>