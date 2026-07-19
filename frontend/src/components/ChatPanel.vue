<template>
  <div class="chat-panel">
    <!-- 顶部标题 -->
    <div class="chat-header">
      <div class="header-brand">
        <div class="brand-icon">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
            <polyline points="9,22 9,12 15,12 15,22"/>
          </svg>
        </div>
        <div class="brand-text">
          <h1>衢小游</h1>
          <span class="subtitle">衢州旅游 AI 向导</span>
        </div>
      </div>
      <button
        class="map-toggle"
        :class="{ active: showMap }"
        @click="$emit('toggle-map')"
        :title="showMap ? '隐藏地图' : '显示地图'"
      >
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5zM15 19l-6-2.11V5l6 2.11V19z"/>
        </svg>
        <span>{{ showMap ? '隐藏地图' : '地图' }}</span>
      </button>
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="welcome">
        <div class="welcome-icon">
          <svg viewBox="0 0 64 64" width="64" height="64" fill="none">
            <circle cx="32" cy="32" r="30" fill="rgba(34,177,76,0.12)" stroke="rgba(34,177,76,0.3)" stroke-width="1.5"/>
            <path d="M32 18c-7.7 0-14 5.4-14 12 0 3.8 2 7.2 5.2 9.6L20 46l7.2-4.2c1.5.5 3.1.8 4.8.8 7.7 0 14-5.4 14-12s-6.3-12-14-12z" fill="rgba(34,177,76,0.2)" stroke="rgba(34,177,76,0.4)" stroke-width="1.5"/>
            <circle cx="26" cy="30" r="2" fill="rgba(34,177,76,0.5)"/>
            <circle cx="38" cy="30" r="2" fill="rgba(34,177,76,0.5)"/>
            <path d="M28 36c0 0 1.5 2 4 2s4-2 4-2" stroke="rgba(34,177,76,0.5)" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
        <h2 class="welcome-title">你好，我是衢小游</h2>
        <p class="welcome-desc">你的衢州旅游智能向导，问我关于景点、美食、路线的问题吧</p>
        <div class="quick-actions">
          <button @click="$emit('send', '衢州明天天气怎么样')">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
            明天天气
          </button>
          <button @click="$emit('send', '从衢州市区怎么去江郎山')">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
            怎么去江郎山
          </button>
          <button @click="$emit('send', '衢州有什么好吃的')">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8h1a4 4 0 010 8h-1"/><path d="M2 8h16v9a4 4 0 01-4 4H6a4 4 0 01-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/></svg>
            特色美食
          </button>
          <button @click="$emit('send', '附近有什么餐厅')">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
            附近餐厅
          </button>
        </div>
      </div>

      <MessageBubble
        v-for="(msg, i) in messages"
        :key="i"
        :message="msg"
        :message-index="i"
        :is-latest="i === messages.length - 1 && !loading"
        :tts-state="ttsState"
        :speaking-index="speakingIndex"
        @suggest="$emit('send', $event)"
        @speak="(text, index) => $emit('speak', text, index)"
      />

      <div v-if="loading && messages.length > 0 && !messages[messages.length - 1].content" class="typing">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input">
      <div v-if="asrError" class="asr-error">{{ asrError }}</div>
      <div class="input-wrapper">
        <!-- 麦克风按钮 -->
        <button
          @click="toggleMic"
          :disabled="loading"
          :class="['mic-btn', { recording: isRecording }]"
          :title="isRecording ? '停止录音' : '语音输入'"
        >
          <svg v-if="!isRecording" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="6" y="6" width="12" height="12" rx="1"/>
          </svg>
        </button>
        <input
          v-model="inputText"
          @keyup.enter="send"
          :disabled="loading"
          :placeholder="isRecording ? '正在聆听...' : '输入你的问题，开始衢州之旅...'"
          class="input-field"
        />
        <button @click="send" :disabled="loading || !inputText.trim()" class="send-btn">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import MessageBubble from './MessageBubble.vue'
import { useVoice } from '../composables/useVoice.js'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  showMap: { type: Boolean, default: false },
  ttsState: { type: String, default: 'idle' },
  speakingIndex: { type: Number, default: -1 },
})

const emit = defineEmits(['send', 'toggle-map', 'suggest', 'speak'])

const inputText = ref('')
const messagesContainer = ref(null)

// 语音模块
const { isRecording, asrError, startRecording, stopRecording } = useVoice()

function toggleMic() {
  if (isRecording.value) {
    stopRecording()
  } else {
    startRecording(inputText)
  }
}

function send() {
  const text = inputText.value.trim()
  if (!text || props.loading) return
  inputText.value = ''
  emit('send', text)
}

watch(
  () => props.messages.length,
  () => {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  }
)

watch(
  () => props.messages.map(m => m.content).join(''),
  () => {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  }
)
</script>

<style scoped>
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ─── 顶部标题 ─── */
.chat-header {
  padding: 16px 20px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(135deg, #B5E61D, #00A2E8);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0,162,232,0.3);
}

.brand-text h1 {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #2d3436, #636e72);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 2px;
}

.subtitle {
  font-size: 11px;
  color: rgba(0,0,0,0.35);
  letter-spacing: 1px;
  font-weight: 400;
}

.map-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 7px 14px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 10px;
  background: rgba(255,255,255,0.5);
  color: rgba(0,0,0,0.55);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  flex-shrink: 0;
  font-family: inherit;
}

.map-toggle:hover {
  border-color: rgba(0,162,232,0.3);
  background: rgba(181,230,29,0.1);
  color: #00A2E8;
}

.map-toggle.active {
  background: linear-gradient(135deg, #B5E61D, #00A2E8);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 2px 8px rgba(0,162,232,0.3);
}

/* ─── 消息列表 ─── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ─── 欢迎页 ─── */
.welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 10px;
  padding: 20px;
}

.welcome-icon {
  margin-bottom: 4px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.welcome-title {
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, #2d3436, #636e72);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.welcome-desc {
  font-size: 13px;
  color: rgba(0,0,0,0.4);
  max-width: 320px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 6px;
}

.quick-actions button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 20px;
  background: rgba(255,255,255,0.6);
  color: rgba(0,0,0,0.6);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.25s ease;
  font-family: inherit;
}

.quick-actions button:hover {
  background: linear-gradient(135deg, #B5E61D, #00A2E8);
  color: #fff;
  border-color: transparent;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,162,232,0.3);
}

/* ─── 打字动画 ─── */
.typing {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
  align-self: flex-start;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: linear-gradient(135deg, #B5E61D, #00A2E8);
  animation: typing 1.4s infinite ease-in-out;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.25; }
  30% { transform: translateY(-6px); opacity: 1; }
}

/* ─── 输入区域 ─── */
.chat-input {
  padding: 12px 16px 16px;
  border-top: 1px solid rgba(0,0,0,0.04);
}

.input-wrapper {
  display: flex;
  gap: 8px;
  align-items: center;
  background: rgba(255,255,255,0.6);
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 14px;
  padding: 4px 4px 4px 16px;
  transition: all 0.3s ease;
}

.input-wrapper:focus-within {
  border-color: rgba(0,162,232,0.3);
  box-shadow: 0 0 0 3px rgba(181,230,29,0.1), 0 2px 8px rgba(0,0,0,0.04);
  background: rgba(255,255,255,0.85);
}

/* 麦克风按钮 */
.mic-btn {
  width: 38px;
  height: 38px;
  border: none;
  border-radius: 10px;
  background: rgba(0,0,0,0.04);
  color: rgba(0,0,0,0.4);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s ease;
  flex-shrink: 0;
  margin-left: -8px;
}

.mic-btn:hover {
  background: rgba(181,230,29,0.15);
  color: #00A2E8;
}

.mic-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.mic-btn.recording {
  background: #ff4757;
  color: #fff;
  animation: pulse-rec 1.5s ease-in-out infinite;
}

@keyframes pulse-rec {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255,71,87,0.4); }
  50% { box-shadow: 0 0 0 8px rgba(255,71,87,0); }
}

/* ASR 错误提示 */
.asr-error {
  font-size: 12px;
  color: #ff4757;
  padding: 4px 0 0 4px;
  margin-bottom: 2px;
}

.input-field {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  outline: none;
  color: rgba(0,0,0,0.8);
  font-family: inherit;
}

.input-field::placeholder {
  color: rgba(0,0,0,0.25);
}

.input-field:disabled {
  opacity: 0.5;
}

.send-btn {
  width: 38px;
  height: 38px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #B5E61D, #00A2E8);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s ease;
  flex-shrink: 0;
}

.send-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.send-btn:not(:disabled):hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(0,162,232,0.35);
}

.send-btn:not(:disabled):active {
  transform: scale(0.95);
}

/* ─── 移动端 ─── */
@media (max-width: 768px) {
  .chat-panel {
    width: 100%;
    height: 55vh;
  }
  .quick-actions button {
    font-size: 12px;
    padding: 6px 12px;
  }
}
</style>