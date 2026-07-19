<template>
  <div class="map-panel">
    <div id="amap-container" class="map-container"></div>

    <div v-if="routeInfo" class="route-card">
      <div class="route-header">
        <span class="route-icon">{{ routeInfo.mode === '步行' ? '🚶' : '🚗' }}</span>
        <div class="route-title-group">
          <span class="route-title">{{ routeInfo.origin_name }} → {{ routeInfo.destination_name }}</span>
          <span class="route-meta">{{ routeInfo.mode }} · {{ routeInfo.distance_km }} 公里 · 约 {{ routeInfo.duration_min }} 分钟</span>
        </div>
      </div>
      <button class="clear-btn" @click="clearRoute">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
        </svg>
        清除路线
      </button>
    </div>

    <div v-if="!mapLoaded" class="map-loading">
      <div class="loading-spinner"></div>
      <p>地图加载中...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  showMap: { type: Boolean, default: false },
})

const mapLoaded = ref(false)
const routeInfo = ref(null)

let map = null
let polyline = null
let startMarker = null
let endMarker = null

watch(() => props.showMap, (visible) => {
  if (visible && !mapLoaded.value) {
    setTimeout(() => initMap(), 50)
  }
})

function initMap() {
  if (typeof AMap === 'undefined') {
    console.warn('高德地图 JS API 未加载，请检查 index.html 中的 Key 配置')
    return
  }

  map = new AMap.Map('amap-container', {
    zoom: 10,
    center: [118.872609, 28.941708],
    viewMode: '2D',
    mapStyle: 'amap://styles/light',
  })

  new AMap.Marker({
    position: [118.872609, 28.941708],
    title: '衢州市中心',
    map: map,
  })

  const scenicSpots = [
    { name: '江郎山', pos: [118.536571, 28.461059] },
    { name: '烂柯山', pos: [118.905719, 28.996564] },
    { name: '根宫佛国', pos: [118.425718, 28.908561] },
    { name: '衢州古城', pos: [118.868912, 28.935560] },
    { name: '南宗孔庙', pos: [118.864219, 28.931562] },
  ]

  scenicSpots.forEach(spot => {
    new AMap.Marker({
      position: spot.pos,
      title: spot.name,
      map: map,
      label: {
        content: `<div style="font-size:12px;color:#00A2E8;background:rgba(255,255,255,0.9);padding:2px 10px;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.08);border:1px solid rgba(0,162,232,0.2);font-weight:500">${spot.name}</div>`,
        direction: 'top',
      },
    })
  })

  mapLoaded.value = true
}

function drawRoute(data) {
  if (!map) return

  clearOverlays()
  routeInfo.value = data

  const originPos = data.origin_coord.split(',').map(Number)
  const destPos = data.destination_coord.split(',').map(Number)

  if (data.polyline && data.polyline.length > 0) {
    polyline = new AMap.Polyline({
      path: data.polyline,
      strokeColor: '#00A2E8',
      strokeWeight: 6,
      strokeOpacity: 0.85,
      lineJoin: 'round',
      lineCap: 'round',
      zIndex: 50,
    })
    map.add(polyline)
  }

  startMarker = new AMap.Marker({
    position: originPos,
    title: data.origin_name,
    label: {
      content: `<div style="background:linear-gradient(135deg,#52c41a,#389e0d);color:#fff;padding:4px 10px;border-radius:8px;font-size:12px;font-weight:600;box-shadow:0 2px 8px rgba(82,196,26,0.3)">起 ${data.origin_name}</div>`,
      direction: 'top',
    },
    map: map,
  })

  endMarker = new AMap.Marker({
    position: destPos,
    title: data.destination_name,
    label: {
      content: `<div style="background:linear-gradient(135deg,#ff4d4f,#cf1322);color:#fff;padding:4px 10px;border-radius:8px;font-size:12px;font-weight:600;box-shadow:0 2px 8px rgba(255,77,79,0.3)">终 ${data.destination_name}</div>`,
      direction: 'top',
    },
    map: map,
  })

  const bounds = new AMap.Bounds(
    [Math.min(originPos[0], destPos[0]) - 0.05, Math.min(originPos[1], destPos[1]) - 0.05],
    [Math.max(originPos[0], destPos[0]) + 0.05, Math.max(originPos[1], destPos[1]) + 0.05]
  )
  map.setBounds(bounds)
}

function clearOverlays() {
  if (polyline) { map.remove(polyline); polyline = null }
  if (startMarker) { map.remove(startMarker); startMarker = null }
  if (endMarker) { map.remove(endMarker); endMarker = null }
}

function clearRoute() {
  clearOverlays()
  routeInfo.value = null
  if (map) {
    map.setZoomAndCenter(10, [118.872609, 28.941708])
  }
}

defineExpose({ drawRoute, clearRoute })

onBeforeUnmount(() => {
  if (map) {
    map.destroy()
  }
})
</script>

<style scoped>
.map-panel {
  width: 100%;
  height: 100%;
  position: relative;
}

.map-container {
  width: 100%;
  height: 100%;
}

/* ─── 路线信息卡片 ─── */
.route-card {
  position: absolute;
  top: 16px;
  left: 16px;
  right: 16px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.5);
  border-radius: 14px;
  padding: 14px 18px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 14px;
}

.route-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.route-icon {
  font-size: 22px;
}

.route-title-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.route-title {
  font-size: 14px;
  font-weight: 600;
  color: #2d3436;
}

.route-meta {
  font-size: 12px;
  color: rgba(0,0,0,0.4);
}

.clear-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.5);
  color: rgba(0,0,0,0.5);
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.25s ease;
  font-family: inherit;
}

.clear-btn:hover {
  background: rgba(255,77,79,0.08);
  border-color: rgba(255,77,79,0.2);
  color: #ff4d4f;
}

/* ─── 加载动画 ─── */
.map-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: rgba(0,0,0,0.4);
  font-size: 13px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(181,230,29,0.15);
  border-top-color: #00A2E8;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ─── 移动端 ─── */
@media (max-width: 768px) {
  .map-panel {
    height: 45vh;
  }

  .route-card {
    top: 8px;
    left: 8px;
    right: 8px;
    padding: 10px 14px;
    flex-wrap: wrap;
    gap: 8px;
  }
}
</style>