"""
直接从卡包 JSON 提取卡片间的关系

不需要 LightRAG，直接用 DeepSeek API 分析每对卡片的关系。
适用于卡片数量不多（< 50）的情况。

用法：
  python scripts/extract_relations.py
  python scripts/extract_relations.py --input output/json/灾害学_v5.json --output output/json/灾害学_v5.json
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from openai import AsyncOpenAI

# ═══════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════

DEEPSEEK_API_KEY = "sk-894795de35f2414e85a46f5903494a7c"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


# ═══════════════════════════════════════════
# 关系类型定义
# ═══════════════════════════════════════════

RELATION_TYPES = """
- expand（展开/具体化）：B是A的具体化、特例、组成部分、实例
- generalize（概括）：B是A的概括、抽象、总结
- contrast（对比）：A与B对比辨析，强调区别
- theorize（理论）：B是A的理论基础、原理依据
- apply（实践/应用）：B是A的实践应用、管理方法、操作流程
- precede（前置/前提）：B是A的前提条件、前置知识
- succeed（后继/结果）：B是A的结果、后续阶段
"""


async def analyze_relation(card_a: dict, card_b: dict) -> dict | None:
    """分析两张卡片之间的关系"""
    prompt = f"""分析以下两个知识卡片之间的关系。

卡片A（标题：{card_a['title']}）：
{card_a.get('answer', '')[:300]}

卡片B（标题：{card_b['title']}）：
{card_b.get('answer', '')[:300]}

请判断卡片A和卡片B之间是否存在直接的、明确的关联关系。
如果存在，请返回：
1. 关系类型（从以下选择一种）：{RELATION_TYPES}
2. 关系描述：一句话说明A和B的关系（20字以内）

如果不存在直接关联，请返回：无关系

只返回JSON格式：{{"has_relation": true/false, "type": "关系类型", "description": "关系描述"}}
"""

    try:
        resp = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=200,
        )
        text = resp.choices[0].message.content
        result = json.loads(text)
        if result.get("has_relation"):
            return {
                "targetId": card_b["title"],
                "type": result.get("type", "expand"),
                "label": result.get("description", ""),
            }
        return None
    except Exception as e:
        print(f"  [WARN] 分析失败: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser(description="提取卡片关系")
    parser.add_argument("--input", default=str(ROOT_DIR / "output/json/灾害学_v5.json"))
    parser.add_argument("--output", default=str(ROOT_DIR / "output/json/灾害学_v5.json"))
    parser.add_argument("--limit", type=int, default=0, help="限制参与分析的卡片数（0=全部）")
    args = parser.parse_args()

    # 1. 读取卡包
    print(f"[INFO] 读取卡包: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        pack = json.load(f)

    cards = pack.get("cards", [])
    if args.limit > 0:
        cards = cards[:args.limit]

    card_titles = [c.get("title", "") for c in cards if c.get("title")]
    print(f"[INFO] 共 {len(cards)} 张卡片，将分析 {len(cards) * (len(cards) - 1) // 2} 对关系")

    # 2. 逐对分析
    all_relations = {}
    analyzed = 0

    for i, card_a in enumerate(cards):
        title_a = card_a.get("title", "")
        relations = []
        for j, card_b in enumerate(cards):
            if i >= j:
                continue
            title_b = card_b.get("title", "")
            analyzed += 1
            print(f"  [{analyzed}] {title_a} ↔ {title_b}")

            # A→B
            result_ab = await analyze_relation(card_a, card_b)
            if result_ab:
                relations.append(result_ab)

            # B→A
            result_ba = await analyze_relation(card_b, card_a)
            if result_ba and result_ba.get("targetId") != title_a:
                relations.append({
                    "targetId": title_a,
                    "type": result_ba.get("type", "expand"),
                    "label": result_ba.get("description", ""),
                })

        if relations:
            all_relations[title_a] = relations

    # 3. 写入卡片
    print("[INFO] 写入 relations...")
    for card in cards:
        title = card.get("title", "")
        card.pop("knowledge_interfaces", None)
        card["relations"] = all_relations.get(title, [])

    # 4. 输出
    pack["version"] = pack.get("version", 1) + 1
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in all_relations.values())
    print(f"[DONE] 输出: {args.output}")
    print(f"[DONE] 共生成 {total} 条关系（分析了 {analyzed} 对）")


if __name__ == "__main__":
    asyncio.run(main())