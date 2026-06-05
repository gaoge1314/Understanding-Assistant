"""
构建知识关联——中间概念层 pipeline

5 步流水线：
  Step 1: 数据准备 —— 从 graphml 提取实体+三元组，读取卡片数据
  Step 2: LLM 聚类 —— DeepSeek 将实体聚合成 20-30 中间概念
  Step 3: 卡片绑定 —— 严格匹配(A) → LLM 补充(B)
  Step 4: 关系推导 —— 规则引擎 → LLM 精修 + 写 proof
  Step 5: 输出 —— 更新卡片 JSON（semantic_profile + relations[].proof）

用法：
  python scripts/build_relations.py
"""

import os
import sys
import json
import re
import asyncio
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from difflib import SequenceMatcher

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# ──────────────────────────────────────────────
# DeepSeek API 配置
# ──────────────────────────────────────────────
DEEPSEEK_API_KEY = "sk-894795de35f2414e85a46f5903494a7c"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"
# ──────────────────────────────────────────────


def load_graph_data(graphml_path: str) -> tuple[list[str], list[tuple[str, str, str]]]:
    """从 GraphML 提取所有实体名 + 三元组关系"""
    tree = ET.parse(graphml_path)
    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}

    entities = []
    for n in tree.findall(".//g:node", ns):
        d0 = n.find("g:data[@key='d0']", ns)
        if d0 is not None and d0.text:
            entities.append(d0.text)

    triples = []
    for e in tree.findall(".//g:edge", ns):
        src = e.get("source", "")
        tgt = e.get("target", "")
        desc_data = e.find("g:data[@key='d0']", ns)
        rel_label = e.find("g:data[@key='d1']", ns)
        desc = ""
        if desc_data is not None and desc_data.text:
            desc = desc_data.text
        elif rel_label is not None and rel_label.text:
            desc = rel_label.text
        if src and tgt:
            triples.append((src, desc, tgt))

    return entities, triples


def build_triple_input(entities: list[str], triples: list[tuple[str, str, str]]) -> str:
    """构建LLM输入的实体清单+三元组"""
    lines = [f"【实体清单】（共 {len(entities)} 个）"]
    lines.append("、".join(entities))
    lines.append("")
    lines.append(f"【三元组关系】（共 {len(triples)} 条）")
    for s, r, t in triples[:200]:  # 最多送200条以避免token超限
        rel_text = r[:40] if r else "(关联)"
        lines.append(f"  ({s}, {rel_text}, {t})")
    if len(triples) > 200:
        lines.append(f"  ... (其余 {len(triples)-200} 条略)")

    return "\n".join(lines)


def build_clustering_prompt(
    triple_input: str,
    card_titles: list[str],
) -> list[dict]:
    """构建聚类 Prompt（含 24 张卡片标题作为锚点）"""
    system_msg = """你是一位知识体系构建专家。你的任务是将灾害学知识图谱中的微观"实体"聚类为 20-30 个高层次的"中间概念"。

每个中间概念必须满足：
1. 概念名：简洁（4-8 字），如"能量传递机制"、"风险量化评估"
2. entities：列出属于该概念的实体名（必须是从输入实体清单中选取的）
3. description：一句话说明这个概念在灾害学中代表什么

你还需输出概念间的关系（可选）：
- concept_relations：概念之间的有向关系，如 A 是 B 的输入、A 导致 B 等

注意：最终这些概念会与灾害学的 24 张知识卡片对接，聚类时请考虑这些卡片的方向。"""

    titles_str = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(card_titles))
    user_msg = f"""{triple_input}

以上是灾害学知识图谱中的所有实体和关系。

以下是将要对接的 24 张知识卡片（作为聚类锚点，帮助确定概念的方向）：
{titles_str}

请将这 259 个实体聚类为 20-30 个中间概念，输出 JSON 格式（严格遵循）：

{{
  "intermediate_concepts": [
    {{
      "concept_name": "概念名（4-8字）",
      "entities": ["实体1", "实体2", ...],
      "description": "一句话描述"
    }}
  ],
  "concept_relations": [
    {{"source": "概念A", "target": "概念B", "relation": "关系描述"}}
  ]
}}"""

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


async def call_deepseek(messages: list[dict]) -> str:
    """调用 DeepSeek API"""
    import aiohttp

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
        "max_tokens": 8192,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        ) as resp:
            raw_text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"DeepSeek API 错误 {resp.status}: {raw_text[:500]}")
            try:
                data = json.loads(raw_text)
                content = data["choices"][0]["message"]["content"]
                if not content:
                    print(f"  [WARN] API 返回空 content，完整响应: {json.dumps(data, ensure_ascii=False)[:300]}")
                    return "{}"
                return content
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  [WARN] 解析响应失败: {e}")
                print(f"  [WARN] 原始响应(前500字): {raw_text[:500]}")
                return "{}"


def _repair_json(raw: str) -> str:
    """修复常见的 JSON 格式问题"""
    # 1. 修复 ""word" → "word"（多余的开引号）
    raw = re.sub(r'""([^"]{1,20})"', r'"\1"', raw)

    # 2. 修复数组末尾多余的逗号
    raw = re.sub(r',\s*]', ']', raw)
    raw = re.sub(r',\s*}', '}', raw)

    # 3. 确保以 } 结尾
    stripped = raw.rstrip()
    if not stripped.endswith("}"):
        last_brace = stripped.rfind("}")
        if last_brace == -1:
            stripped += "}"
        else:
            stripped = stripped[:last_brace+1]

    # 4. 补全未闭合的引号
    in_string = False
    escape = False
    for i, ch in enumerate(stripped):
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
    if in_string:
        stripped += '"'

    return stripped


def parse_concepts(raw: str) -> dict:
    """解析 LLM 返回的 JSON，含多层容错"""
    if not raw or raw.strip() in ("{}", ""):
        return {"intermediate_concepts": [], "concept_relations": []}

    # Step 1: 尝试从代码块中提取
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
    if m:
        raw = m.group(1)

    # Step 2: 尝试直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Step 3: 修复常见问题后重试
    print(f"  [WARN] JSON 解析失败(长度={len(raw)}字)，尝试修复...")
    print(f"  [DEBUG] 内容前500字: {raw[:500]}")
    print(f"  [DEBUG] 内容后300字: {raw[-300:]}")

    fixed = _repair_json(raw)
    try:
        result = json.loads(fixed)
        print(f"  [INFO] JSON 修复成功！")
        return result
    except json.JSONDecodeError:
        pass

    # Step 4: 逐行修复 — 如果某行有引号问题，跳过问题行
    lines = raw.split("\n")
    cleaned = []
    for line in lines:
        # 跳过完全无效的行
        if re.match(r'^\s*["\']?\s*["\']?\s*[,]?\s*$', line) and len(line.strip()) <= 2:
            continue
        cleaned.append(line)
    fixed2 = _repair_json("\n".join(cleaned))

    try:
        result = json.loads(fixed2)
        print(f"  [INFO] JSON 逐行修复成功！")
        return result
    except json.JSONDecodeError:
        print(f"  [WARN] 修复均失败，返回空结构")
        return {"intermediate_concepts": [], "concept_relations": []}


def bind_cards_strict(
    card_titles: list[str],
    concepts: list[dict],
) -> dict[str, list[str]]:
    """方法 A：严格实体交集匹配——卡片标题或语义画像与概念实体做交集"""
    bindings = {t: [] for t in card_titles}
    used_titles = set()

    # 对每个概念，提取其实体集
    concept_entity_sets = {}
    for c in concepts:
        name = c["concept_name"]
        entities = set(c.get("entities", []))
        concept_entity_sets[name] = entities

    # 对每个卡片，遍历概念取交集
    for title in card_titles:
        bound_concepts = []
        for c in concepts:
            cname = c["concept_name"]
            centities = concept_entity_sets[cname]
            # 检查标题是否在概念实体中（精确匹配）
            if title in centities:
                bound_concepts.append(cname)
                continue
            # 检查标题是否以概念实体开头或相反
            for e in centities:
                if e == title or (len(e) > 3 and len(title) > 3 and
                                  (title.startswith(e) or e.startswith(title))):
                    bound_concepts.append(cname)
                    break
                # 模糊匹配 ≥ 0.8
                if SequenceMatcher(None, e, title).ratio() >= 0.80:
                    bound_concepts.append(cname)
                    break
        if bound_concepts:
            bindings[title] = bound_concepts
            used_titles.add(title)

    return bindings, used_titles


def build_binding_prompt(
    unmatched_titles: list[str],
    concepts: list[dict],
) -> list[dict]:
    """方法 B：LLM 绑定——将未绑定卡片分类到概念"""
    concept_list = "\n".join(
        f"  {i+1}. {c['concept_name']} — {c.get('description','')}"
        for i, c in enumerate(concepts)
    )
    titles_list = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(unmatched_titles))

    system_msg = """你将灾害学知识卡片与中间概念进行语义绑定。根据卡片的标题和内容，判断它最相关的是哪 1-3 个中间概念，并给出理由。请以JSON格式输出。"""

    user_msg = f"""中间概念列表：
{concept_list}

未绑定的卡片：
{titles_list}

请为每张卡片绑定最相关的 1-3 个中间概念。
输出格式：
{{
  "bindings": [
    {{"card_title": "卡片标题", "concepts": ["概念A", "概念B"], "reason": "绑定理..."}},
    ...
  ]
}}"""

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def derive_relations_rule(
    bindings: dict[str, list[str]],
    concept_relations: list[dict],
) -> list[tuple[str, str, str, list[str]]]:
    """规则引擎预推导卡片关系
    返回: [(卡片A, 卡片B, 关系类型, 共享概念列表)]"""
    results = []
    titles = list(bindings.keys())

    # 建立概念→卡片的反向索引
    concept_to_cards = {}
    for title, concepts in bindings.items():
        for c in concepts:
            concept_to_cards.setdefault(c, []).append(title)

    # 建立概念间关系图谱（快速查找路径）
    concept_graph = {}
    for cr in concept_relations:
        s, t = cr["source"], cr["target"]
        concept_graph.setdefault(s, []).append(t)

    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            a, b = titles[i], titles[j]
            a_concepts = set(bindings.get(a, []))
            b_concepts = set(bindings.get(b, []))

            # 情况1：共享概念
            shared = a_concepts & b_concepts
            if shared:
                results.append((a, b, "expand", list(shared)))
                continue

            # 情况2：概念图中有路径
            path_found = None
            for ac in a_concepts:
                if ac in concept_graph:
                    for target in concept_graph[ac]:
                        if target in b_concepts:
                            path_found = (ac, target)
                            break
            if path_found:
                results.append((a, b, "apply", [path_found[0], path_found[1]]))
                continue

            # 情况3：通过反向索引——共享卡片但无共同概念，跳过

    return results


def build_refine_prompt(
    rule_results: list[tuple[str, str, str, list[str]]],
    bindings: dict[str, list[str]],
    cards: list[dict],
) -> list[dict]:
    """LLM 精修：修正关系类型 + 写 proof + 生成每张卡片的 function_tag 和 abstract"""
    pairs_str = "\n".join(
        f"  {i+1}. {a} ↔ {b}\n"
        f"     预分类类型: {rel_type}\n"
        f"     关联概念: {', '.join(concepts)}"
        for i, (a, b, rel_type, concepts) in enumerate(rule_results)
    )

    # 构建卡片摘要数据
    card_summaries = {}
    for c in cards:
        title = c.get("title", "")
        if title:
            answer_excerpt = (c.get("answer", "") or "")[:120]
            card_summaries[title] = {
                "title": title,
                "core_principle": c.get("core_principle", ""),
                "answer_excerpt": answer_excerpt,
            }

    system_msg = """你是知识关系分析专家。你的任务包括两项：

任务一（精修关系）：对卡片之间的关系进行精修
1. 确认或修正关系类型（expand/contrast/generalize/theorize/apply/precede/succeed）
2. 一句话描述label
3. 写出证明链 proof：包括 shared_entities（相关实体）、intermediate_concepts（共享概念）、reasoning（推理过程）

关系类型定义：
- expand：展开/补充，同一领域的不同侧面
- generalize：概括/抽象，从具体到一般
- contrast：对比/辨析，指出差异
- theorize：理论化/解释，用理论解释现象
- apply：应用/实践，理论到实践
- precede：前置/前提，因果关系中的原因方
- succeed：后继/结果，因果关系中的结果方

任务二（卡片语义画像）：为每张卡片生成 function_tag 和 abstract
- function_tag：功能标签，可选值：mechanism_description（机制描述）、comparison_analysis（对比分析）、process_flow（流程步骤）、structural_model（结构模型）、practical_guideline（实践指南）
- abstract：一句话抽象概括（不超过50字），用高度凝练的语言说明该卡片的核心内容

请以JSON格式输出。"""

    user_msg = f"""以下是规则引擎预推导的卡片关系对列表：

{pairs_str}

每张卡片的中间概念绑定情况：
{json.dumps(bindings, ensure_ascii=False, indent=2)}

每张卡片的详细数据（用于生成 function_tag 和 abstract）：
{json.dumps(card_summaries, ensure_ascii=False, indent=2)}

请输出：
{{
  "refined_relations": [
    {{
      "source": "卡片A",
      "target": "卡片B",
      "type": "关系类型",
      "label": "一句话描述",
      "proof": {{
        "shared_entities": ["实体1", "实体2"],
        "intermediate_concepts": ["概念A", "概念B"],
        "reasoning": "推理过程（为什么这两张卡有关联）"
      }}
    }}
  ],
  "card_profiles": [
    {{
      "title": "卡片标题",
      "function_tag": "功能标签",
      "abstract": "一句话抽象概括（≤50字）"
    }}
  ]
}}"""

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


async def build_relations(input_path, output_path, rag_dir, output_dir, force=False):
    """5 步流水线主流程（模块级 API，可直接 import 调用）

    Args:
        input_path: 输入卡包 JSON 路径
        output_path: 输出卡包 JSON 路径
        rag_dir: LightRAG 存储目录
        output_dir: 中间产物输出目录
        force: 是否强制重新聚类（不使用缓存）
    """

    # ════════════════════════════════════════
    # Step 1: 数据准备
    # ════════════════════════════════════════
    print("[Step 1/5] 数据准备...")

    # 1a. 读取卡包
    print(f"  [INFO] 读取卡包: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        pack = json.load(f)

    cards = pack.get("cards", [])
    card_titles = [c.get("title", "") for c in cards if c.get("title")]
    print(f"  [INFO] 共 {len(cards)} 张卡片")

    # 1b. 读取 LightRAG 图谱
    graphml_path = os.path.join(rag_dir, "graph_chunk_entity_relation.graphml")
    if not os.path.exists(graphml_path):
        print(f"  [ERROR] 找不到图谱文件: {graphml_path}")
        return

    entities, triples = load_graph_data(graphml_path)
    print(f"  [INFO] 图谱: {len(entities)} 实体, {len(triples)} 三元组")

    # ════════════════════════════════════════
    # Step 2: LLM 聚类 → 中间概念
    # ════════════════════════════════════════
    print("[Step 2/5] LLM 聚类生成中间概念...")

    # 检查缓存
    concepts_cache_path = os.path.join(output_dir, "intermediate_concepts.json")
    concepts_data = None

    if os.path.exists(concepts_cache_path) and not force:
        print(f"  [INFO] 使用缓存中间概念: {concepts_cache_path}")
        with open(concepts_cache_path, "r", encoding="utf-8") as f:
            concepts_data = json.load(f)
    else:
        triple_input = build_triple_input(entities, triples)
        prompt = build_clustering_prompt(triple_input, card_titles)

        print(f"  [INFO] 调用 DeepSeek (model={DEEPSEEK_MODEL}, max_tokens=8192)...")
        raw = await call_deepseek(prompt)
        concepts_data = parse_concepts(raw)
        print(f"  [INFO] 聚类完成: {len(concepts_data.get('intermediate_concepts', []))} 个中间概念, "
              f"{len(concepts_data.get('concept_relations', []))} 条概念间关系")

        # 保存缓存
        os.makedirs(output_dir, exist_ok=True)
        with open(concepts_cache_path, "w", encoding="utf-8") as f:
            json.dump(concepts_data, f, ensure_ascii=False, indent=2)
        print(f"  [INFO] 缓存已保存: {concepts_cache_path}")

    concepts = concepts_data.get("intermediate_concepts", [])
    concept_relations = concepts_data.get("concept_relations", [])

    if not concepts:
        print("  [ERROR] 未生成任何中间概念，pipeline 终止。")
        print("  [HINT] 可能原因: API 返回空、max_tokens 不足、Prompt 不当")
        return

    # ════════════════════════════════════════
    # Step 3: 卡片绑定到中间概念
    # ════════════════════════════════════════
    print("[Step 3/5] 卡片绑定到中间概念...")

    # 3a. 方法 A — 严格实体交集
    bindings, used_titles = bind_cards_strict(card_titles, concepts)
    print(f"  [INFO] 方法A（严格匹配）: {len(used_titles)}/{len(card_titles)} 张已绑定")

    # 3b. 方法 B — LLM 补充绑定
    unmatched = [t for t in card_titles if t not in used_titles]
    if unmatched:
        print(f"  [INFO] 方法B（LLM补充）: {len(unmatched)} 张待绑定...")
        b_prompt = build_binding_prompt(unmatched, concepts)
        b_raw = await call_deepseek(b_prompt)
        b_data = parse_concepts(b_raw)

        for item in b_data.get("bindings", []):
            title = item["card_title"]
            if title in bindings and title not in used_titles:
                bindings[title] = item.get("concepts", [])
                used_titles.add(title)
        print(f"  [INFO] LLM 补充后: {len(used_titles)}/{len(card_titles)}")

    # 3c. 打印绑定结果
    for title in card_titles:
        if title in used_titles:
            print(f"  ✅ {title} → {bindings[title]}")
        else:
            print(f"  ❌ {title}（未绑定）")

    # ════════════════════════════════════════
    # Step 4: 关系推导 + proof 生成
    # ════════════════════════════════════════
    print("[Step 4/5] 关系推导 + proof 生成...")

    # 4a. 规则引擎预推导
    rule_results = derive_relations_rule(bindings, concept_relations)
    print(f"  [INFO] 规则引擎预推导: {len(rule_results)} 条关系")

    # 4b. LLM 精修 + 写 proof
    if rule_results:
        refine_prompt = build_refine_prompt(rule_results, bindings, cards)
        print(f"  [INFO] LLM 精修中...")
        refine_raw = await call_deepseek(refine_prompt)
        refine_data = parse_concepts(refine_raw)
        refined = refine_data.get("refined_relations", [])
        print(f"  [INFO] LLM 精修完成: {len(refined)} 条精修关系")
    else:
        refined = []

    # ════════════════════════════════════════
    # Step 5: 输出
    # ════════════════════════════════════════
    print("[Step 5/5] 写入输出...")

    # 5a. 构建输出映射（source → relation list）
    rel_map = {t: [] for t in card_titles}
    for r in refined:
        src = r.get("source", "")
        if src in rel_map:
            rel_map[src].append({
                "targetId": r.get("target", ""),
                "type": r.get("type", "expand"),
                "label": r.get("label", ""),
                "proof": r.get("proof", {}),
            })

    # 5b. 读取 card_profiles（Step 4 增强输出）
    card_profiles = {}
    if refine_data:
        for cp in refine_data.get("card_profiles", []):
            card_profiles[cp["title"]] = cp

    # 5c. 写入卡片
    for card in cards:
        title = card.get("title", "")
        profile = card_profiles.get(title, {})
        card["semantic_profile"] = {
            "core_terms": bindings.get(title, []),
            "function_tag": profile.get("function_tag", ""),
            "abstract": profile.get("abstract", ""),
        }
        # 写入 relations（含 proof）
        card["relations"] = rel_map.get(title, [])

    # 5d. 输出
    pack["version"] = pack.get("version", 1) + 1
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    total_rels = sum(len(v) for v in rel_map.values())
    print(f"[DONE] 输出: {output_path}")
    print(f"[DONE] 共 {total_rels} 条关系")
    print(f"[DONE] 绑定率: {len(used_titles)}/{len(card_titles)}")


async def main():
    """CLI 入口（保持手动运行能力）"""
    parser = argparse.ArgumentParser(description="构建知识关联（中间概念层）")
    parser.add_argument("--input", default=str(ROOT_DIR / "output/json/灾害学_v5.json"))
    parser.add_argument("--output", default=str(ROOT_DIR / "output/json/灾害学_v5.json"))
    parser.add_argument("--rag-dir", default=str(ROOT_DIR / "rag_storage"))
    parser.add_argument("--output-dir", default=str(ROOT_DIR / "output/json"))
    parser.add_argument("--force", action="store_true", help="强制重新聚类（不使用缓存）")
    args = parser.parse_args()

    await build_relations(
        input_path=args.input,
        output_path=args.output,
        rag_dir=args.rag_dir,
        output_dir=args.output_dir,
        force=args.force,
    )


if __name__ == "__main__":
    asyncio.run(main())