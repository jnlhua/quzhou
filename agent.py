"""
Agent 工具模块
包含四个工具（全部基于高德地图 API）：
  1. get_weather      — 高德天气：实时天气 + 4日预报
  2. search_location  — 高德地图：地址转经纬度（地理编码）
  3. plan_route       — 高德地图：路线规划（驾车/步行）
  4. search_poi       — 高德地图：周边 POI 搜索（餐厅/酒店/景点）

工具设计原则：
  - 每个工具只做一件事（原子工具）
  - 返回结构化字典，失败时返回 {"error": "原因"}
  - 调用前在 Agent 层做权限检查，工具本身不做副作用操作
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

AMAP_KEY = os.getenv("AMAP_API_KEY")

# 衢州市中心经纬度（高德坐标系）
QUZHOU_CENTER = "118.872609,28.941708"
# 衢州各景区坐标（高德坐标系，供路线规划使用）
SCENIC_COORDS = {
    "江郎山": "118.536571,28.461059",
    "烂柯山": "118.905719,28.996564",
    "根宫佛国": "118.425718,28.908561",
    "开化森林氧吧": "118.425718,28.908561",
    "衢州古城": "118.868912,28.935560",
    "南宗孔庙": "118.864219,28.931562",
}


# ─────────────────────────────────────────
# 工具 1：实时天气 + 7日预报
# ─────────────────────────────────────────

def get_weather(location_name: str = "衢州") -> dict:
    """
    获取指定城市的实时天气和未来4日预报（高德天气API）

    Args:
        location_name: 城市或地区名称，默认衢州

    Returns:
        {
            "city": "衢州市",
            "now": {"temp": "25", "text": "晴", "humidity": "60", "windDir": "东风", "windPower": "3"},
            "forecast": [{"date": "2025-06-18", "textDay": "晴", "tempMax": "28", "tempMin": "18", "windDir": "东", "windPower": "≤3"}, ...]
        }
    """
    if not AMAP_KEY:
        return {"error": "未配置 AMAP_KEY，请检查 .env 文件"}

    try:
        weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"

        # Step 1：获取实时天气（extensions=base）
        now_res = requests.get(
            weather_url,
            params={
                "city": location_name,
                "key": AMAP_KEY,
                "extensions": "base",
                "output": "JSON",
            },
            timeout=5,
        )
        now_data = now_res.json()
        if now_data.get("status") != "1":
            return {"error": f"实时天气获取失败: {now_data.get('info', '未知错误')}"}

        lives = now_data.get("lives", [])
        if not lives:
            return {"error": f"找不到城市天气: {location_name}"}

        live = lives[0]
        city_name = live.get("city", location_name)

        # Step 2：获取预报天气（extensions=all）
        fc_res = requests.get(
            weather_url,
            params={
                "city": location_name,
                "key": AMAP_KEY,
                "extensions": "all",
                "output": "JSON",
            },
            timeout=5,
        )
        fc_data = fc_res.json()
        forecast = []
        if fc_data.get("status") == "1":
            for day in fc_data.get("forecasts", [{}])[0].get("casts", []):
                forecast.append({
                    "date": day["date"],
                    "textDay": day["dayweather"],
                    "tempMax": day["daytemp"],
                    "tempMin": day["nighttemp"],
                    "windDir": day["daywind"],
                    "windPower": day["daypower"],
                })

        return {
            "city": city_name,
            "now": {
                "temp": live.get("temperature", ""),
                "text": live.get("weather", ""),
                "humidity": live.get("humidity", ""),
                "windDir": live.get("winddirection", ""),
                "windPower": live.get("windpower", ""),
            },
            "forecast": forecast,
        }

    except requests.Timeout:
        return {"error": "天气 API 请求超时，请稍后重试"}
    except Exception as e:
        return {"error": f"天气查询异常: {str(e)}"}


# ─────────────────────────────────────────
# 工具 2：地址 → 经纬度（地理编码）
# ─────────────────────────────────────────

def search_location(address: str) -> dict:
    """
    将地址文字转换为经纬度坐标（高德地理编码）

    Args:
        address: 地址，如"衢州市江山市江郎山景区"

    Returns:
        {"name": "江郎山景区", "location": "118.536571,28.461059", "address": "..."}
    """
    if not AMAP_KEY:
        return {"error": "未配置 AMAP_KEY，请检查 .env 文件"}

    # 优先从预置坐标表查
    for name, coord in SCENIC_COORDS.items():
        if name in address:
            return {"name": name, "location": coord, "address": address, "source": "preset"}

    try:
        url = "https://restapi.amap.com/v3/geocode/geo"
        # 先不限城市搜索，搜不到再限制衢州
        res = requests.get(
            url,
            params={
                "address": address,
                "key": AMAP_KEY,
                "output": "JSON",
            },
            timeout=5,
        )
        data = res.json()
        if data.get("status") == "1" and data.get("geocodes"):
            geo = data["geocodes"][0]
            return {
                "name": geo.get("formatted_address", address),
                "location": geo["location"],
                "address": geo.get("formatted_address", ""),
            }

        # 全国搜不到，限制衢州重试
        res = requests.get(
            url,
            params={
                "address": address,
                "city": "衢州",
                "key": AMAP_KEY,
                "output": "JSON",
            },
            timeout=5,
        )
        data = res.json()
        if data.get("status") != "1" or not data.get("geocodes"):
            return {"error": f"找不到地址: {address}"}

        geo = data["geocodes"][0]
        return {
            "name": geo.get("formatted_address", address),
            "location": geo["location"],
            "address": geo.get("formatted_address", ""),
        }

    except requests.Timeout:
        return {"error": "地图 API 请求超时"}
    except Exception as e:
        return {"error": f"地址解析异常: {str(e)}"}


# ─────────────────────────────────────────
# 工具 3：路线规划（驾车 / 步行）
# ─────────────────────────────────────────

def plan_route(origin: str, destination: str, mode: str = "driving") -> dict:
    """
    规划从起点到终点的路线

    Args:
        origin:      起点，地址文字或"经度,纬度"坐标
        destination: 终点，地址文字或"经度,纬度"坐标
        mode:        出行方式，"driving"（驾车）或 "walking"（步行）

    Returns:
        {
            "origin": "衢州市区",
            "destination": "江郎山景区",
            "mode": "driving",
            "distance_km": 90.5,
            "duration_min": 95,
            "steps": ["沿G60高速行驶...", ...]
        }
    """
    if not AMAP_KEY:
        return {"error": "未配置 AMAP_KEY，请检查 .env 文件"}

    def to_coord(loc_str: str) -> str:
        """如果是地址文字，先转经纬度"""
        if "," in loc_str and loc_str.replace(",", "").replace(".", "").replace("-", "").isdigit():
            return loc_str  # 已经是坐标
        result = search_location(loc_str)
        if "error" in result:
            return None
        return result["location"]

    origin_coord = to_coord(origin)
    dest_coord = to_coord(destination)

    if not origin_coord:
        return {"error": f"无法解析起点地址: {origin}"}
    if not dest_coord:
        return {"error": f"无法解析终点地址: {destination}"}

    try:
        if mode == "walking":
            url = "https://restapi.amap.com/v3/direction/walking"
        else:
            url = "https://restapi.amap.com/v3/direction/driving"

        params = {
            "origin": origin_coord,
            "destination": dest_coord,
            "key": AMAP_KEY,
            "output": "JSON",
        }
        if mode == "driving":
            params["strategy"] = 0  # 速度优先

        res = requests.get(url, params=params, timeout=8)
        data = res.json()

        if data.get("status") != "1":
            return {"error": f"路线规划失败: {data.get('info', '未知错误')}"}

        route = data["route"]
        path = route["paths"][0]
        steps_data = path.get("steps", [])

        # 提取文字导航指令（前5步）
        instructions = [s["instruction"] for s in steps_data][:5]
        distance = round(int(path["distance"]) / 1000, 1)
        duration = round(int(path["duration"]) / 60)

        # 提取完整路径坐标串（供前端地图画线）
        polyline_points = []
        for s in steps_data:
            polyline_str = s.get("polyline", "")
            if polyline_str:
                for point in polyline_str.split(";"):
                    if point and "," in point:
                        lng, lat = point.split(",")
                        polyline_points.append([float(lng), float(lat)])

        return {
            "origin": origin,
            "destination": destination,
            "mode": "驾车" if mode == "driving" else "步行",
            "distance_km": distance,
            "duration_min": duration,
            "steps": instructions,
            "origin_coord": origin_coord,
            "destination_coord": dest_coord,
            "polyline": polyline_points,
        }

    except requests.Timeout:
        return {"error": "路线规划 API 超时"}
    except Exception as e:
        return {"error": f"路线规划异常: {str(e)}"}


# ─────────────────────────────────────────
# 工具 4：周边 POI 搜索
# ─────────────────────────────────────────

def search_poi(keywords: str, location: str = QUZHOU_CENTER, radius: int = 5000) -> dict:
    """
    在指定位置周边搜索 POI（兴趣点）

    Args:
        keywords: 搜索关键词，如"餐厅"、"酒店"、"景点"
        location: 搜索中心点坐标，默认衢州市中心
        radius:   搜索半径（米），默认 5000 米

    Returns:
        {"pois": [{"name": "xxx", "address": "xxx", "location": "lng,lat", "tel": "xxx"}, ...]}
    """
    if not AMAP_KEY:
        return {"error": "未配置 AMAP_KEY，请检查 .env 文件"}

    try:
        url = "https://restapi.amap.com/v3/place/around"
        res = requests.get(
            url,
            params={
                "keywords": keywords,
                "location": location,
                "radius": radius,
                "key": AMAP_KEY,
                "output": "JSON",
                "offset": 10,  # 返回条数
                "page": 1,
                "extensions": "base",
            },
            timeout=5,
        )
        data = res.json()
        if data.get("status") != "1":
            return {"error": f"POI 搜索失败: {data.get('info')}"}

        pois = []
        for p in data.get("pois", [])[:8]:
            pois.append({
                "name": p.get("name", ""),
                "address": p.get("address", ""),
                "location": p.get("location", ""),
                "tel": p.get("tel", ""),
                "type": p.get("type", ""),
            })

        return {"keywords": keywords, "pois": pois, "total": len(pois)}

    except requests.Timeout:
        return {"error": "POI 搜索 API 超时"}
    except Exception as e:
        return {"error": f"POI 搜索异常: {str(e)}"}


# ─────────────────────────────────────────
# 工具注册表（供 Agent 使用）
# ─────────────────────────────────────────

TOOLS = {
    "get_weather": get_weather,
    "search_location": search_location,
    "plan_route": plan_route,
    "search_poi": search_poi,
}

# DeepSeek function calling 格式的工具描述
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取衢州及周边城市的实时天气和未来4日天气预报。仅用于回答衢州相关的天气问题，如'明天衢州天气怎么样''去江郎山要带雨伞吗'",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_name": {
                        "type": "string",
                        "description": "衢州地区城市或区域名称，如'衢州'、'江山'、'开化'、'常山'、'龙游'",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_route",
            "description": "规划衢州范围内的路线，支持驾车和步行。仅用于衢州相关的路线规划问题，如'从衢州市区开车去江郎山怎么走'",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "起点地址，如'衢州市区'、'衢州高铁站'",
                    },
                    "destination": {
                        "type": "string",
                        "description": "终点地址，如'江郎山景区'、'烂柯山'",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["driving", "walking"],
                        "description": "出行方式：driving（驾车）或 walking（步行），默认 driving",
                    },
                },
                "required": ["origin", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_poi",
            "description": "搜索衢州周边的餐厅、酒店、景点等地点。用于回答'附近有什么好吃的''衢州有哪些酒店'",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词，如'衢州菜餐厅'、'酒店'、'景点'",
                    },
                    "location": {
                        "type": "string",
                        "description": "搜索中心坐标（经度,纬度），默认衢州市中心",
                    },
                    "radius": {
                        "type": "integer",
                        "description": "搜索半径（米），默认5000",
                    },
                },
                "required": ["keywords"],
            },
        },
    },
]