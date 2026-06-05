"""
learning-app 生成脚本：读取卡包 JSON → 生成交互式 HTML 应用

用法：
    python generate_app.py <json_path> [--output-dir <path>] [--build-relations] [--rag-dir <path>]

说明：
    - json_path: 卡包 JSON 文件路径（必填）
    - output-dir: 输出目录（可选，默认 output/card-app/{subject}/）
    - build-relations: 先运行关系构建流水线，再生成应用（可选）
    - rag-dir: LightRAG 存储目录（--build-relations 时使用）
"""

import asyncio
import json
import re
import shutil
import sys
from pathlib import Path


def title_to_id(title: str) -> str:
    """从标题生成唯一标识

    保留中文字符，将连续的非字母数字替换为连字符。
    """
    s = re.sub(r'[^\w\u4e00-\u9fff]+', '-', title)
    s = s.strip('-')
    return s.lower()


def resolve_knowledge_interfaces(cards: list) -> None:
    """解析知识接口文本，建立卡片间引用

    解析规则：
    - 提取 → 后的文本作为目标标题
    - 按精确标题匹配找到 target_card_id
    - 匹配不到则保留 raw_text 降级
    """
    # 构建标题 → card_id 索引
    title_to_card = {}
    for card in cards:
        title = card.get("title", "")
        card_id = card.get("card_id", "")
        if title:
            title_to_card[title] = card_id

    for card in cards:
        raw_ifaces = card.get("knowledge_interfaces", [])
        resolved = []
        for item in raw_ifaces:
            if isinstance(item, str):
                raw_text = item
            else:
                raw_text = item.get("raw_text", "") or item.get("text", "")

            # 解析 "→ 标题：说明" 格式
            target_title = ""
            relation = ""
            text = raw_text
            if text.startswith("→"):
                text = text[1:].strip()
            if "：" in text:
                parts = text.split("：", 1)
                target_title = parts[0].strip()
                relation = parts[1].strip()
            elif ":" in text:
                parts = text.split(":", 1)
                target_title = parts[0].strip()
                relation = parts[1].strip()
            else:
                target_title = text

            target_card_id = title_to_card.get(target_title, "")

            resolved.append({
                "target_card_id": target_card_id,
                "target_title": target_title,
                "relation": relation,
                "raw_text": raw_text,
            })

        card["knowledge_interfaces"] = resolved


def detect_reconstruct_types(card: dict) -> list:
    """判断卡片适合哪些重构模式，返回列表

    可能的值：
    - "reorder"   — 平行概念拖拽排序
    - "fill-blank" — 概念填空
    空列表 = 不适合任何重构

    判断规则：
    - reorder: decomposition 条目数 ≥ 2 且为平行关系
    - fill-blank: answer 字段长度 ≥ 20 字且有可挖术语
    """
    types = []
    decomposition = card.get("decomposition", [])
    answer = card.get("answer", "")
    title = card.get("title", "")

    # --- reorder 判断 ---
    if len(decomposition) >= 2:
        parallel_keywords = [
            "要素", "类型", "分类", "类别", "阶段", "步骤", "组成部分",
            "成分", "元素", "维度", "方面", "层面", "环节", "流程",
            "种类", "形式", "形态", "特征", "指标",
            "因素", "条件", "分支",
        ]
        if any(kw in title for kw in parallel_keywords):
            types.append("reorder")
        else:
            causal_pattern = re.compile(r"(因为|所以|如果|则|因此|导致|使得|从而)")
            has_causal = any(causal_pattern.search(item) for item in decomposition)
            if not has_causal:
                types.append("reorder")

    # --- fill-blank 判断 ---
    if len(answer) >= 20:
        keywords = _collect_keywords(card)
        if keywords:
            types.append("fill-blank")

    return types


def _collect_keywords(card: dict) -> set:
    """收集卡片中的技术术语（用作挖空候选）

    优先级：decomposition > memory_techniques.keywords > answer 中 ≥3 字的词
    """
    keywords = set()

    # 1. decomposition 条目（通常包含概念名、要素名）
    for item in card.get("decomposition", []):
        for sep in ["：", ":", "。", ".", "，", ","]:
            if sep in item:
                item = item.split(sep)[0]
        item = item.strip()
        if len(item) >= 2:
            keywords.add(item)

    # 2. memory_techniques.keywords
    mt = card.get("memory_techniques", {})
    for kw in mt.get("keywords", []):
        if len(kw) >= 2:
            keywords.add(kw)

    # 3. 如果还不够，从 answer 中提取 ≥3 字的连续名词短语
    if len(keywords) < 3:
        answer = card.get("answer", "")
        segments = re.split(r"[，,。.、：:；;()（）]", answer)
        for seg in segments:
            seg = seg.strip()
            if 2 <= len(seg) <= 20 and not any(c in seg for c in "的了着呢吗"):
                keywords.add(seg)

    return keywords


def generate_blanks(card: dict) -> list:
    """从卡片 answer 字段生成挖空题

    返回格式：
    [
        {"sentence": "...____......____...", "answers": ["术语1", "术语2"], "hint": "..."},
        ...
    ]
    最多生成 3 题，每题挖 1-2 个空
    """
    answer = card.get("answer", "")
    if len(answer) < 20:
        return []

    keywords = sorted(_collect_keywords(card), key=len, reverse=True)
    valid_kw = [kw for kw in keywords if kw in answer]

    if len(valid_kw) < 1:
        return []

    blanks = []
    used_indices = set()

    for kw in valid_kw:
        if len(blanks) >= 3:
            break

        start = 0
        positions = []
        while True:
            idx = answer.find(kw, start)
            if idx == -1:
                break
            positions.append((idx, idx + len(kw)))
            start = idx + 1

        if not positions:
            continue

        chosen = None
        for pos in positions:
            if not any(u[0] < pos[1] and pos[0] < u[1] for u in used_indices):
                chosen = pos
                break

        if chosen is None:
            continue

        used_indices.add(chosen)

        ctx_start = max(0, chosen[0] - 30)
        ctx_end = min(len(answer), chosen[1] + 30)
        context = answer[ctx_start:chosen[0]] + "____" + answer[chosen[1]:ctx_end]
        context = context.strip("，,。.！!？?；;")

        second_kw = None
        second_pos = None
        for kw2 in valid_kw:
            if kw2 == kw:
                continue
            idx2 = answer.find(kw2, max(0, chosen[0] - 10), min(len(answer), ctx_end))
            if idx2 >= 0:
                if not any(u[0] < idx2 + len(kw2) and idx2 < u[1] for u in used_indices):
                    second_kw = kw2
                    second_pos = idx2
                    break

        if second_kw and second_pos:
            used_indices.add((second_pos, second_pos + len(second_kw)))
            ctx_end2 = min(len(answer), second_pos + len(second_kw) + 10)
            sentence_fragment = answer[max(ctx_start, second_pos - 20):second_pos] + "____" + answer[second_pos + len(second_kw):ctx_end2]
            blanks.append({
                "sentence": sentence_fragment.strip("，,。.！!？?；;"),
                "answers": [kw, second_kw],
                "hint": "填写对应的关键术语"
            })
        else:
            blanks.append({
                "sentence": context,
                "answers": [kw],
                "hint": "填写对应的关键术语"
            })

    return blanks


async def generate_app(
    json_path: str,
    output_dir: str | None = None,
    build_relations: bool = False,
    rag_dir: str | None = None,
) -> str:
    """从卡包 JSON 生成 HTML 应用

    Args:
        json_path: 卡包 JSON 文件路径
        output_dir: 输出目录（可选，默认 output/card-app/{subject}/）
        build_relations: 是否先运行关系构建流水线
        rag_dir: LightRAG 存储目录（build_relations=True 时使用）
    """
    json_path = Path(json_path)

    # 0. 可选：先运行关系构建流水线
    if build_relations:
        print("=" * 60)
        print("[前置步骤] 运行中间概念层关系构建流水线...")
        print("=" * 60)

        # 尝试导入 build_relations，优先从项目根目录
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from scripts.build_relations import build_relations as run_build_relations

        if rag_dir is None:
            rag_dir = str(Path(json_path).parent.parent.parent / "rag_storage")

        await run_build_relations(
            input_path=str(json_path),
            output_path=str(json_path),
            rag_dir=rag_dir,
            output_dir=str(json_path.parent),
        )
        print("=" * 60)
        print("[前置步骤] 关系构建完成，继续生成应用")
        print("=" * 60)

    if not json_path.exists():
        raise FileNotFoundError(f"卡包 JSON 文件不存在：{json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        pack_data = json.load(f)

    subject = pack_data.get("subject", "未命名科目")
    cards = pack_data.get("cards", [])

    if not cards:
        raise ValueError("卡包 JSON 中没有卡片数据")

    # 2. 为每张卡片生成 card_id
    for card in cards:
        if not card.get("card_id"):
            card["card_id"] = title_to_id(card.get("title", ""))

    # 3. 解析知识接口引用
    resolve_knowledge_interfaces(cards)

    # 4. 富化每张卡片（重构类型 + 填空数据）
    enriched_cards = []
    for card in cards:
        enriched_card = dict(card)
        enriched_card["reconstruct_type"] = detect_reconstruct_types(card)
        enriched_card["blanks"] = generate_blanks(card)
        enriched_cards.append(enriched_card)

    # 5. 构造 data.json 数据
    output_data = {
        "subject": subject,
        "source_file": pack_data.get("source_file", ""),
        "generated_at": pack_data.get("generated_at", ""),
        "version": pack_data.get("version", 1),
        "all_knowledge_titles": pack_data.get("all_knowledge_titles", []),
        "cards": enriched_cards,
    }

    # 6. 确定输出目录
    if output_dir is None:
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent.parent.parent
        output_dir = project_root / "output" / "card-app" / subject
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 7. 拷贝模板文件
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    if not templates_dir.exists():
        raise FileNotFoundError(f"模板目录不存在：{templates_dir}")

    for filename in ["index.html", "style.css", "state.js", "collapse.js", "sidebar.js", "card-view.js", "flashcard.js", "plan.js", "reorder.js", "fill-blank.js", "app.js"]:
        src = templates_dir / filename
        dst = output_dir / filename
        if src.exists():
            if filename == "index.html":
                content = src.read_text(encoding="utf-8")
                data_json = json.dumps(output_data, ensure_ascii=False, indent=2)
                content = content.replace("__DATA__", data_json)
                dst.write_text(content, encoding="utf-8")
            else:
                shutil.copy2(src, dst)
            print(f"  ✓ 拷贝 {filename}")
        else:
            print(f"  ⚠ 模板文件 {filename} 不存在，跳过")

    # 8. 统计各类卡片数量
    reorder_count = sum(1 for c in enriched_cards if "reorder" in c.get("reconstruct_type", []))
    blank_count = sum(1 for c in enriched_cards if "fill-blank" in c.get("reconstruct_type", []))
    blank_total = sum(len(c.get("blanks", [])) for c in enriched_cards)
    print(f"     - 概念重组: {reorder_count} 张 | 概念填空: {blank_count} 张（{blank_total} 题）")

    print(f"\n✅ 学习应用已生成：{output_dir}")
    print(f"   打开 {output_dir / 'index.html'} 即可开始学习")
    return str(output_dir)


def main():
    if len(sys.argv) < 2:
        print("用法：python generate_app.py <json_path> [选项]")
        print("选项：")
        print("  --output-dir <path>    输出目录（可选）")
        print("  --build-relations      先运行关系构建流水线（可选）")
        print("  --rag-dir <path>       LightRAG 存储目录（--build-relations 时使用）")
        print("示例：")
        print("  python generate_app.py ../../output/json/灾害学_v5.json")
        print("  python generate_app.py ../../output/json/灾害学_v5.json --build-relations")
        sys.exit(1)

    json_path = sys.argv[1]
    output_dir = None
    build_relations_flag = False
    rag_dir = None

    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        if idx + 1 < len(sys.argv):
            output_dir = sys.argv[idx + 1]

    if "--build-relations" in sys.argv:
        build_relations_flag = True

    if "--rag-dir" in sys.argv:
        idx = sys.argv.index("--rag-dir")
        if idx + 1 < len(sys.argv):
            rag_dir = sys.argv[idx + 1]

    try:
        asyncio.run(generate_app(json_path, output_dir, build_relations_flag, rag_dir))
    except Exception as e:
        print(f"❌ 生成失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()