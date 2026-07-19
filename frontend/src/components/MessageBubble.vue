<template>
  <div class="message" :class="message.role">
    <div v-if="message.role === 'user'" class="bubble user-bubble">
      <div class="bubble-content">
        <p>{{ message.content }}</p>
      </div>
    </div>

    <div v-else class="assistant-wrapper">
      <div class="assistant-avatar">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
          <polyline points="9,22 9,12 15,12 15,22"/>
        </svg>
      </div>
      <!-- TTS 语音播报按钮 -->
      <button
        v-if="message.content"
        :class="['tts-btn', ttsBtnState]"
        @click="$emit('speak', message.content, messageIndex)"
        :title="ttsBtnTitle"
        :disabled="ttsBtnState === 'loading'"
      >
        <!-- idle: 播放图标 -->
        <svg v-if="ttsBtnState === 'idle'" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        <!-- loading: 旋转图标 -->
        <svg v-else-if="ttsBtnState === 'loading'" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" class="spin-icon">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 2a10 10 0 0 1 10 10"/>
        </svg>
        <!-- playing: 暂停图标 -->
        <svg v-else-if="ttsBtnState === 'playing'" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="6" y="4" width="4" height="16"/>
          <rect x="14" y="4" width="4" height="16"/>
        </svg>
        <!-- paused: 播放图标 -->
        <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        <span>{{ ttsBtnLabel }}</span>
      </button>
      <div class="bubble assistant-bubble">
        <div v-if="message.steps && message.steps.length > 0" class="react-steps">
          <div v-for="(step, i) in message.steps" :key="i" class="step-item">
            <span class="step-icon" :class="step.status === 'running' ? 'step-running' : 'step-done'">
              <svg v-if="step.status === 'running'" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" class="spin-icon">
                <path d="M12 2a10 10 0 0 1 10 10"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </span>
            <span class="step-label">{{ step.label }}</span>
          </div>
        </div>
        <div v-if="message.rewriteHint" class="rewrite-hint">
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          <span>您可能是想问：<strong>{{ message.rewriteHint }}</strong></span>
        </div>
        <div v-if="message.toolStatus" class="tool-status">
          <span class="tool-icon">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </span>
          {{ message.toolStatus }}
        </div>
        <div v-if="message.content" class="content markdown-body" v-html="renderMarkdown(message.content)"></div>
      </div>
      <div v-if="isLatest && message.suggestions && message.suggestions.length > 0" class="suggestions">
        <button
          v-for="(s, i) in message.suggestions"
          :key="i"
          class="suggest-btn"
          @click="$emit('suggest', s)"
        >
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18l6-6-6-6"/>
          </svg>
          {{ s }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  message: { type: Object, required: true },
  isLatest: { type: Boolean, default: false },
  messageIndex: { type: Number, default: -1 },
  ttsState: { type: String, default: 'idle' },
  speakingIndex: { type: Number, default: -1 },
})

const emit = defineEmits(['suggest', 'speak'])

// TTS 按钮状态（当前消息是否被选中播报）
const ttsBtnState = computed(() => {
  if (props.messageIndex === props.speakingIndex) {
    return props.ttsState // 'loading' | 'playing' | 'paused'
  }
  return 'idle'
})

const ttsBtnTitle = computed(() => {
  switch (ttsBtnState.value) {
    case 'idle': return '语音播报'
    case 'loading': return '正在合成语音...'
    case 'playing': return '暂停播报'
    case 'paused': return '继续播报'
    default: return '语音播报'
  }
})

const ttsBtnLabel = computed(() => {
  switch (ttsBtnState.value) {
    case 'idle': return '播报'
    case 'loading': return '合成中'
    case 'playing': return '暂停'
    case 'paused': return '继续'
    default: return '播报'
  }
})

marked.setOptions({
  breaks: true,
  gfm: true,
})

function renderMarkdown(text) {
  let html = marked.parse(text)
  html = html.replace(
    /「来源：(.+?)」/g,
    '<div class="source-tag">来源：$1</div>'
  )
  return html
}
</script>

<style scoped>
.message {
  display: flex;
  max-width: 100%;
  animation: msg-in 0.3s ease-out;
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
  flex-direction: column;
  align-items: flex-start;
}

/* ─── 用户气泡 ─── */
.bubble {
  max-width: 80%;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
}

.user-bubble {
  background: linear-gradient(135deg, #B5E61D, #00A2E8);
  color: #fff;
  border-bottom-right-radius: 4px;
  padding: 10px 16px;
  box-shadow: 0 2px 8px rgba(0,162,232,0.2);
}

.bubble-content p {
  margin: 0;
}

/* ─── 助手消息 ─── */
.assistant-wrapper {
  max-width: 90%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.assistant-avatar {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: linear-gradient(135deg, #B5E61D, #00A2E8);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 2px;
  box-shadow: 0 2px 6px rgba(0,162,232,0.2);
}

/* TTS 播报按钮 */
.tts-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border: 1px solid rgba(0,162,232,0.15);
  border-radius: 10px;
  background: rgba(181,230,29,0.06);
  color: #00A2E8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  margin-left: 34px;
  margin-bottom: 2px;
  font-family: inherit;
}

.tts-btn:hover:not(:disabled) {
  background: rgba(0,162,232,0.1);
  border-color: rgba(0,162,232,0.3);
  transform: translateY(-1px);
}

.tts-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tts-btn.loading {
  color: #f39c12;
  border-color: rgba(243,156,18,0.2);
  background: rgba(243,156,18,0.06);
}

.tts-btn.playing {
  color: #00A2E8;
  border-color: rgba(0,162,232,0.25);
  background: rgba(0,162,232,0.08);
}

.tts-btn.paused {
  color: #e67e22;
  border-color: rgba(230,126,34,0.2);
  background: rgba(230,126,34,0.06);
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.assistant-bubble {
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255,255,255,0.6);
  color: rgba(0,0,0,0.8);
  border-bottom-left-radius: 4px;
  padding: 10px 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.tool-status {
  font-size: 12px;
  color: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

/* ─── ReAct 思考步骤 ─── */
.react-steps {
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px dashed rgba(0,0,0,0.08);
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
  color: rgba(0,0,0,0.5);
  animation: step-in 0.3s ease-out;
}

@keyframes step-in {
  from { opacity: 0; transform: translateX(-6px); }
  to { opacity: 1; transform: translateX(0); }
}

.step-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  flex-shrink: 0;
}

.step-running {
  color: #00A2E8;
  background: rgba(0,162,232,0.1);
}

.step-done {
  color: #52c41a;
  background: rgba(82,196,26,0.1);
}

.step-label {
  line-height: 1.4;
}

/* ─── 问题改写提示 ─── */
.rewrite-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(0,0,0,0.4);
  margin-bottom: 8px;
  padding: 6px 10px;
  background: rgba(0,162,232,0.05);
  border-radius: 8px;
  border-left: 3px solid rgba(0,162,232,0.3);
}

.rewrite-hint strong {
  color: #00A2E8;
  font-weight: 500;
}

.tool-icon {
  display: inline-flex;
  animation: spin 1.5s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ─── Markdown 样式 ─── */
.markdown-body :deep(p) {
  margin: 0 0 6px 0;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(strong) {
  font-weight: 600;
  color: #2d3436;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 4px 0;
  padding-left: 18px;
}
.markdown-body :deep(li) {
  margin: 3px 0;
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 8px 0 4px 0;
  font-weight: 600;
  color: #2d3436;
}
.markdown-body :deep(h1) { font-size: 17px; }
.markdown-body :deep(h2) { font-size: 16px; }
.markdown-body :deep(h3) { font-size: 15px; }
.markdown-body :deep(code) {
  background: rgba(0,0,0,0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: #e17055;
}
.markdown-body :deep(pre) {
  background: rgba(0,0,0,0.04);
  padding: 10px 14px;
  border-radius: 10px;
  overflow-x: auto;
  margin: 6px 0;
  border: 1px solid rgba(0,0,0,0.06);
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid #B5E61D;
  padding-left: 12px;
  margin: 6px 0;
  color: rgba(0,0,0,0.5);
}
.markdown-body :deep(a) {
  color: #00A2E8;
  text-decoration: none;
  font-weight: 500;
}
.markdown-body :deep(a:hover) {
  text-decoration: underline;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 6px 0;
  width: 100%;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid rgba(0,0,0,0.08);
  padding: 6px 10px;
  text-align: left;
  font-size: 13px;
}
.markdown-body :deep(th) {
  background: rgba(181,230,29,0.1);
  font-weight: 600;
}
.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid rgba(0,0,0,0.08);
  margin: 10px 0;
}
.markdown-body :deep(.source-tag) {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(0,0,0,0.35);
  font-style: italic;
}

/* ─── 推荐追问 ─── */
.suggestions {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-left: 34px;
}

.suggest-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border: 1px solid rgba(0,162,232,0.15);
  border-radius: 10px;
  background: rgba(181,230,29,0.06);
  color: #00A2E8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  text-align: left;
  align-self: flex-start;
  font-family: inherit;
}

.suggest-btn:hover {
  background: linear-gradient(135deg, #B5E61D, #00A2E8);
  color: #fff;
  border-color: transparent;
  transform: translateX(3px);
  box-shadow: 0 2px 8px rgba(0,162,232,0.2);
}
</style>