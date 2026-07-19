"""
衢小游 RAG 检索评估脚本
======================
对比不同检索策略的召回效果：
  A. 纯语义检索（BGE-M3 + ChromaDB）
  B. 纯 BM25 关键词检索
  C. 双路融合（语义 + BM25 → RRF）
  D. 双路融合 + Reranker 精排（完整管线）
  E. 完整管线 + 问题改写（检索失败时触发）

指标：Hit@1, Hit@3, MRR（Mean Reciprocal Rank）

运行方式：
  python evaluate.py
"""

import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat_engine import rag, _rewrite_query, _get_llm_client

# ─────────────────────────────────────────
# 测试集：(问题, 期望命中的 chunk_id 列表)
# 包含简单问题、口语化问题、需要改写才能命中的问题
# ─────────────────────────────────────────
TEST_CASES = [
    # ── 简单直接（应该轻松命中）──
    ("衢州有什么好吃的", ["food_001", "food_002"]),
    ("江郎山门票多少钱", ["jianglangshan_002"]),
    ("烂柯山怎么去", ["lankeshan_004"]),
    ("衢州住哪里比较好", ["accommodation_001", "accommodation_002"]),
    ("衢州公交多少钱", ["transport_001"]),
    ("水亭门有什么好玩的", ["gengong_shuitingmen_004", "gengong_shuitingmen_005"]),
    ("衢州有什么特产可以买", ["shopping_001", "shopping_004"]),
    ("江郎山在哪里", ["jianglangshan_001"]),
    ("烂柯山有什么景点", ["lankeshan_003"]),
    ("衢州过年有什么活动", ["festivals_001", "festivals_002"]),

    # ── 口语化 / 表述模糊（考验检索鲁棒性）──
    ("去江郎山玩要带多少钱", ["jianglangshan_002"]),
    ("开化那个鱼好吃吗在哪吃", ["food_001"]),
    ("从杭州开车去衢州走哪条高速", ["transport_003"]),
    ("水亭门晚上有啥看的", ["gengong_shuitingmen_005", "gengong_shuitingmen_003"]),
    ("衢州那个围棋的山叫什么", ["lankeshan_001"]),
    ("龙游发糕哪里买", ["shopping_001", "food_001"]),
    ("江郎山旁边还有什么古镇", ["jianglangshan_005"]),
    ("衢州晚上哪里热闹", ["gengong_shuitingmen_005", "festivals_004"]),

    # ── 需要改写才能命中（首次检索大概率失败）──
    ("衢州有没有适合带小孩玩的地方", ["jianglangshan_001", "gengong_shuitingmen_001"]),
    ("下雨天衢州能去哪", ["gengong_shuitingmen_001", "jianglangshan_004"]),
    ("衢州拍照打卡的地方", ["jianglangshan_001", "gengong_shuitingmen_004"]),
    ("一个人去衢州玩两天怎么安排", ["jianglangshan_001", "lankeshan_001", "accommodation_001"]),
    ("衢州有没有什么非遗体验", ["festivals_003", "gengong_shuitingmen_004"]),
]


# ─────────────────────────────────────────
# 检索策略封装
# ─────────────────────────────────────────
def retrieve_semantic_only(query, top_k=3):
    """策略A：纯语义检索"""
    return rag._semantic_search(query, top_k=top_k)


def retrieve_bm25_only(query, top_k=3):
    """策略B：纯BM25"""
    return rag._bm25_search(query, top_k=top_k)


def retrieve_fusion(query, top_k=3):
    """策略C：双路RRF融合（无Reranker）"""
    sem = rag._semantic_search(query, top_k=5)
    bm = rag._bm25_search(query, top_k=5)
    return rag._rrf_fusion(sem, bm, top_n=top_k)


def retrieve_full(query, top_k=3):
    """策略D：完整管线（双路 + Reranker）"""
    return rag.retrieve(query)


def retrieve_with_rewrite(query, top_k=3):
    """策略E：完整管线 + 问题改写兜底"""
    docs = rag.retrieve(query)
    if docs and docs[0].get("rerank_score", 0) >= -2:
        return docs
    # 检索失败 → 改写 → 重试
    client = _get_llm_client()
    rewritten = _rewrite_query(client, query)
    if rewritten != query:
        retry = rag.retrieve(rewritten)
        if retry and retry[0].get("rerank_score", 0) >= -2:
            return retry
    return docs  # 返回原始结果（可能为空或低分）


STRATEGIES = {
    "A_纯语义": retrieve_semantic_only,
    "B_纯BM25": retrieve_bm25_only,
    "C_双路RRF": retrieve_fusion,
    "D_双路+Rerank": retrieve_full,
    "E_完整+改写": retrieve_with_rewrite,
}


# ─────────────────────────────────────────
# 评估指标计算
# ─────────────────────────────────────────
def hit_at_k(retrieved_ids, expected_ids, k):
    """前 k 个结果中是否命中了任一期望文档"""
    return 1 if any(rid in expected_ids for rid in retrieved_ids[:k]) else 0


def mrr(retrieved_ids, expected_ids):
    """Mean Reciprocal Rank：第一个命中的排名倒数"""
    for i, rid in enumerate(retrieved_ids):
        if rid in expected_ids:
            return 1.0 / (i + 1)
    return 0.0


def evaluate_strategy(name, func, test_cases):
    """对单个策略跑全部测试用例，返回指标"""
    hit1_total = 0
    hit3_total = 0
    mrr_total = 0.0
    n = len(test_cases)
    details = []

    for query, expected in test_cases:
        try:
            docs = func(query)
            retrieved_ids = [d["chunk_id"] for d in docs] if docs else []
        except Exception as e:
            retrieved_ids = []
            print(f"  [ERROR] {query}: {e}")

        h1 = hit_at_k(retrieved_ids, expected, 1)
        h3 = hit_at_k(retrieved_ids, expected, 3)
        r = mrr(retrieved_ids, expected)

        hit1_total += h1
        hit3_total += h3
        mrr_total += r

        details.append({
            "query": query,
            "expected": expected,
            "retrieved": retrieved_ids,
            "hit@1": h1,
            "hit@3": h3,
            "mrr": round(r, 3),
        })

    return {
        "strategy": name,
        "Hit@1": round(hit1_total / n * 100, 1),
        "Hit@3": round(hit3_total / n * 100, 1),
        "MRR": round(mrr_total / n, 3),
        "details": details,
    }


# ─────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────
def main():
    print("=" * 60)
    print("  衢小游 RAG 检索评估")
    print(f"  测试用例数：{len(TEST_CASES)}")
    print("=" * 60)

    # 初始化 RAG 引擎
    print("\n[1/3] 初始化 RAG 引擎（加载模型 + 向量库）...")
    rag.init()
    print("  [OK] 初始化完成")

    # 逐策略评估
    results = []
    strategies_to_run = list(STRATEGIES.items())

    print(f"\n[2/3] 开始评估（共 {len(strategies_to_run)} 种策略）...\n")

    for name, func in strategies_to_run:
        print(f"  >> 评估策略: {name}")
        start = time.time()
        result = evaluate_strategy(name, func, TEST_CASES)
        elapsed = time.time() - start
        result["time_s"] = round(elapsed, 1)
        results.append(result)
        print(f"    Hit@1={result['Hit@1']}%  Hit@3={result['Hit@3']}%  MRR={result['MRR']}  ({elapsed:.1f}s)")

    # 输出汇总
    print("\n" + "=" * 60)
    print("  评估结果汇总")
    print("=" * 60)
    print(f"\n{'策略':<16} {'Hit@1':>8} {'Hit@3':>8} {'MRR':>8} {'耗时':>8}")
    print("-" * 52)
    for r in results:
        print(f"{r['strategy']:<16} {r['Hit@1']:>7.1f}% {r['Hit@3']:>7.1f}% {r['MRR']:>8.3f} {r['time_s']:>7.1f}s")

    # 输出失败用例详情（完整管线）
    full_result = next((r for r in results if "D_" in r["strategy"]), None)
    if full_result:
        failures = [d for d in full_result["details"] if d["hit@3"] == 0]
        if failures:
            print(f"\n[3/3] 完整管线未命中的用例（{len(failures)} 条）：")
            for f in failures:
                print(f"  [X] \"{f['query']}\"")
                print(f"    期望: {f['expected']}")
                print(f"    实际: {f['retrieved']}")
        else:
            print("\n[3/3] 完整管线全部命中 [OK]")

    # 保存详细结果到 JSON
    output_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {output_path}")


if __name__ == "__main__":
    main()
