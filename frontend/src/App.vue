<template>
  <div class="page-wrapper" @mousemove="handleGlobalMouseMove">
    <!-- 背景层 -->
    <div class="bg-layer">
      <div class="bg-image"></div>
      <div class="bg-overlay"></div>
    </div>

    <!-- 装饰性浮动元素 -->
    <div class="floating-elements" aria-hidden="true">
      <div class="float-circle c1"></div>
      <div class="float-circle c2"></div>
      <div class="float-circle c3"></div>
      <div class="float-line l1"></div>
      <div class="float-line l2"></div>
    </div>

    <!-- 聊天卡片 -->
    <div
      class="chat-card glow-card"
      ref="chatCardRef"
      @mousemove="handleCardMouseMove($event, 'chat')"
      @mouseleave="handleCardMouseLeave('chat')"
    >
      <!-- 边框光效跟随 -->
      <div
        class="border-glow"
        :style="chatGlowStyle"
        v-show="chatGlowVisible"
      ></div>

      <ChatPanel
        :messages="messages"
        :loading="loading"
        :show-map="showMap"
        :tts-state="ttsState"
        :speaking-index="speakingIndex"
        @send="handleSend"
        @toggle-map="showMap = !showMap"
        @speak="handleSpeak"
      />
    </div>

    <!-- 地图面板 -->
    <div
      v-show="showMap"
      class="map-card glow-card"
      ref="mapCardRef"
      @mousemove="handleCardMouseMove($event, 'map')"
      @mouseleave="handleCardMouseLeave('map')"
    >
      <div
        class="border-glow"
        :style="mapGlowStyle"
        v-show="mapGlowVisible"
      ></div>
      <MapPanel :show-map="showMap" ref="mapPanel" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick } from 'vue'
import ChatPanel from './components/ChatPanel.vue'
import MapPanel from './components/MapPanel.vue'
import { useVoice } from './composables/useVoice.js'

const messages = ref([])
const loading = ref(false)
const mapPanel = ref(null)
const showMap = ref(false)

// 语音播报（TTS）
const { ttsState, speakingIndex, handleSpeak } = useVoice()

const MAP_TOOLS = ['plan_route']

// ─── 边框流光效果 ───
const chatCardRef = ref(null)
const mapCardRef = ref(null)
const chatGlow = ref({ x: 50, y: 50 })
const mapGlow = ref({ x: 50, y: 50 })
const chatGlowVisible = ref(false)
const mapGlowVisible = ref(false)

function handleCardMouseMove(e, type) {
  const rect = e.currentTarget.getBoundingClientRect()
  const x = ((e.clientX - rect.left) / rect.width) * 100
  const y = ((e.clientY - rect.top) / rect.height) * 100
  if (type === 'chat') {
    chatGlow.value = { x, y }
    chatGlowVisible.value = true
  } else {
    mapGlow.value = { x, y }
    mapGlowVisible.value = true
  }
}

function handleCardMouseLeave(type) {
  if (type === 'chat') {
    chatGlowVisible.value = false
  } else {
    mapGlowVisible.value = false
  }
}

const chatGlowStyle = computed(() => ({
  background: `radial-gradient(circle at ${chatGlow.value.x}% ${chatGlow.value.y}%, rgba(181,230,29,0.5) 0%, rgba(0,162,232,0.3) 40%, transparent 70%)`,
}))

const mapGlowStyle = computed(() => ({
  background: `radial-gradient(circle at ${mapGlow.value.x}% ${mapGlow.value.y}%, rgba(181,230,29,0.5) 0%, rgba(0,162,232,0.3) 40%, transparent 70%)`,
}))

// ─── 全局视差效果 ───
const mouseX = ref(0)
const mouseY = ref(0)

function handleGlobalMouseMove(e) {
  mouseX.value = (e.clientX / window.innerWidth) * 100
  mouseY.value = (e.clientY / window.innerHeight) * 100
  // 更新浮动元素位置
  document.documentElement.style.setProperty('--mx', mouseX.value + '%')
  document.documentElement.style.setProperty('--my', mouseY.value + '%')
}

// ─── 聊天逻辑 ───
function generateSuggestions(userText) {
  const q = userText.toLowerCase()
  if (/天气|气温|下雨|温度/.test(q)) {
    return ['这周末适合出游吗', '衢州最佳旅游季节', '去江郎山要带什么']
  }
  if (/路线|怎么去|导航|走|开车|步行/.test(q)) {
    return ['附近有什么餐厅', '这个景点门票多少', '还有什么好玩的景点']
  }
  if (/美食|吃|餐厅|小吃|菜/.test(q)) {
    return ['衢州三头一掌是什么', '附近有酒店吗', '衢州有什么特产']
  }
  if (/景点|景区|玩|旅游|打卡/.test(q)) {
    return ['怎么去这个景点', '附近有什么好吃的', '门票多少钱']
  }
  if (/酒店|住|住宿/.test(q)) {
    return ['附近有什么景点', '怎么去江郎山', '衢州有什么美食']
  }
  return ['衢州有什么美食', '怎么去江郎山', '明天天气怎么样']
}

async function handleSend(userText) {
  messages.value.push({ role: 'user', content: userText })

  const assistantMsg = reactive({
    role: 'assistant', content: '', toolStatus: '', steps: [], suggestions: [], rewriteHint: '',
  })
  messages.value.push(assistantMsg)
  loading.value = true

  // 发送新消息时清除旧路线
  if (mapPanel.value) {
    mapPanel.value.clearRoute()
  }

  try {
    const history = messages.value.slice(0, -1).map(m => ({
      role: m.role, content: m.content,
    }))

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText, history }),
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let currentEvent = 'message'

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line === '') {
          currentEvent = 'message'
        } else if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          const dataStr = line.slice(6)
          try {
            const data = JSON.parse(dataStr)

            if (currentEvent === 'route') {
              showMap.value = true
              await nextTick()
              if (mapPanel.value) {
                mapPanel.value.drawRoute(data)
              }
            } else if (currentEvent === 'step') {
              assistantMsg.steps.push(data)
            } else if (currentEvent === 'rewrite') {
              assistantMsg.rewriteHint = data.rewritten
            } else if (currentEvent === 'message') {
              if (data.type === 'token') {
                assistantMsg.content += data.content
              } else if (data.type === 'tool_call') {
                const toolNames = {
                  get_weather: '查询天气',
                  plan_route: '规划路线',
                  search_poi: '搜索周边',
                  search_location: '查找地点',
                }
                assistantMsg.toolStatus = `正在${toolNames[data.name] || data.name}...`

                if (MAP_TOOLS.includes(data.name)) {
                  showMap.value = true
                }
              } else if (data.type === 'done') {
                assistantMsg.toolStatus = ''
                assistantMsg.content = data.content || assistantMsg.content
                assistantMsg.suggestions = generateSuggestions(userText)
              }
            }
          } catch (e) {
            console.warn('SSE JSON parse error:', e, 'raw:', dataStr)
          }
        }
      }
    }
  } catch (err) {
    assistantMsg.content = '网络错误，请检查后端是否启动（localhost:8000）'
    console.error('Chat error:', err)
  } finally {
    loading.value = false
  }
}
</script>

<style>
/* 全局 CSS 变量 */
:root {
  --glow-color-1: rgba(181, 230, 29, 0.4);
  --glow-color-2: rgba(100, 180, 255, 0.3);
  --card-bg: rgba(255, 255, 255, 0.8);
  --card-border: rgba(255, 255, 255, 0.35);
}
</style>

<style scoped>
/* ─── 页面容器 ─── */
.page-wrapper {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  padding: 24px;
  overflow: hidden;
}

/* ─── 背景层 ─── */
.bg-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
}

.bg-image {
  position: absolute;
  inset: 0;
  background: url('/backgroud.png') center center / cover no-repeat;
  filter: brightness(0.85) saturate(1.1);
  transform: scale(1.05);
  animation: bg-kenburns 20s ease-in-out infinite alternate;
}

@keyframes bg-kenburns {
  0% { transform: scale(1.05) translate(0, 0); }
  100% { transform: scale(1.15) translate(-1%, -1%); }
}

.bg-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(135deg, rgba(0,0,0,0.15) 0%, transparent 40%, transparent 60%, rgba(0,0,0,0.1) 100%),
    radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.15) 100%);
}

/* ─── 装饰浮动元素 ─── */
.floating-elements {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

.float-circle {
  position: absolute;
  border-radius: 50%;
  opacity: 0.12;
  transition: transform 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.c1 {
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(100,180,255,0.3), transparent);
  top: 10%; left: 5%;
  transform: translate(calc(var(--mx, 50) * 0.02 - 1%), calc(var(--my, 50) * 0.02 - 1%));
}

.c2 {
  width: 200px; height: 200px;
  background: radial-gradient(circle, rgba(181,230,29,0.25), transparent);
  bottom: 15%; right: 10%;
  transform: translate(calc(var(--mx, 50) * -0.015 + 0.75%), calc(var(--my, 50) * -0.015 + 0.75%));
}

.c3 {
  width: 150px; height: 150px;
  background: radial-gradient(circle, rgba(80,200,120,0.2), transparent);
  top: 50%; left: 60%;
  transform: translate(calc(var(--mx, 50) * 0.01 - 0.5%), calc(var(--my, 50) * 0.01 - 0.5%));
}

.float-line {
  position: absolute;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
  height: 1px;
  width: 60%;
}

.l1 { top: 20%; left: 20%; transform: rotate(-15deg); }
.l2 { bottom: 30%; right: 10%; width: 40%; transform: rotate(10deg); }

/* ─── 通用卡片玻璃态 ─── */
.glow-card {
  position: relative;
  background: var(--card-bg);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  border: 1px solid var(--card-border);
  border-radius: 20px;
  box-shadow:
    0 8px 40px rgba(0, 0, 0, 0.08),
    0 2px 8px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  overflow: hidden;
  transition: transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.4s ease;
  z-index: 1;
}

.glow-card:hover {
  transform: translateY(-2px);
  box-shadow:
    0 12px 48px rgba(0, 0, 0, 0.12),
    0 4px 16px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

/* ─── 边框光效（鼠标追踪） ─── */
.border-glow {
  position: absolute;
  top: -1px;
  left: -1px;
  right: -1px;
  bottom: -1px;
  border-radius: 21px;
  pointer-events: none;
  z-index: -1;
  transition: opacity 0.15s ease;
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: exclude;
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  padding: 2px;
}

/* ─── 聊天卡片 ─── */
.chat-card {
  width: 580px;
  min-width: 440px;
  height: 85vh;
  flex-shrink: 0;
}

/* ─── 地图卡片 ─── */
.map-card {
  flex: 1;
  max-width: 600px;
  height: 85vh;
}

/* ─── 响应式 ─── */
@media (max-width: 1200px) {
  .chat-card { width: 420px; min-width: unset; }
  .map-card { max-width: 480px; }
}

@media (max-width: 768px) {
  .page-wrapper {
    flex-direction: column;
    padding: 12px;
    gap: 12px;
  }
  .chat-card { width: 100%; height: 55vh; }
  .map-card { width: 100%; max-width: none; height: 40vh; }
  .float-circle, .float-line { display: none; }
}
</style>