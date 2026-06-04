"""
将复习题答案填入知识卡包，生成 v5 版本。
同时生成基本的记忆技巧（关键词、层级图、对比表）。
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from scripts import models as m


# ===== 答案提取 =====

def parse_answers(answer_file: str) -> dict:
    """从答案文件的题目标题行提取：标题 → 后续答案文本"""
    with open(answer_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 找出所有题目标题行
    q_starts = []
    for i, line in enumerate(lines):
        line = line.strip()
        # 匹配 "数字. 标题" 或 "数字.文字"（无空格）或 "数字.  标题"（多空格）
        if re.match(r'^\d+\.\s*\S', line) and len(line) > 3:
            # 排除页码
            if line.strip().isdigit():
                continue
            q_starts.append((i, line))

    qa_map = {}
    for idx, (start_i, title_line) in enumerate(q_starts):
        end_i = q_starts[idx + 1][0] if idx + 1 < len(q_starts) else len(lines)

        # 提取题号（支持 "数字. 标题" 和 "数字.标题" 两种格式）
        m_q = re.match(r'(\d+)\.\s*(.*)', title_line)
        if not m_q:
            continue
        q_num = int(m_q.group(1))
        q_title = m_q.group(2).strip().rstrip('。，：:；;')

        # 提取答案文本（从题目标题之后到下一个标题之前）
        answer_lines = []
        for j in range(start_i + 1, end_i):
            line = lines[j].strip()
            if line and not re.match(r'^\d+$', line):  # 跳过空白行和页码
                answer_lines.append(line)

        answer_text = '\n'.join(answer_lines).strip()
        qa_map[q_title] = answer_text

    return qa_map


# ===== 标题模糊匹配 =====

def match_title(q_title: str, card_titles: list) -> str:
    """将答案标题与卡片标题匹配"""
    q_clean = q_title.rstrip('。，')

    # 精确匹配
    if q_clean in card_titles:
        return q_clean

    # 去除"简述"前缀
    clean = re.sub(r'^简述', '', q_clean).strip()
    if clean in card_titles:
        return clean

    # 长标题截取（去掉后半句）
    for ct in card_titles:
        if q_clean.startswith(ct) or ct.startswith(q_clean):
            return ct

    # 归一化后精确匹配（处理"构成灾害链的各种山地灾害的差异性"与"构成灾害链的山地灾害的差异性"）
    def normalize(s: str) -> str:
        """去除标题中对匹配干扰的常见冗余词"""
        s = re.sub(r'各种|简述|对于|中的', '', s)
        return s.strip()

    q_norm = normalize(q_clean)
    for ct in card_titles:
        if q_norm == normalize(ct):
            return ct

    # 包含匹配：优先匹配长标题（避免 "灾害链" 被 "灾害群、灾害链、灾害遭遇的异同" 中的子串抢走）
    candidates = []
    for ct in card_titles:
        if q_clean in ct or ct in q_clean:
            candidates.append(ct)
    if candidates:
        # 返回最长的匹配（最具体）
        return max(candidates, key=len)

    # 关键词匹配
    stop_words = {'的', '与', '和', '及', '、', '，', '。', '；', '：', '了', '在'}
    q_tokens = set(q_clean)
    best_match, best_score = "", 0
    for ct in card_titles:
        ct_tokens = set(ct)
        overlap = len(q_tokens & ct_tokens)
        if overlap > best_score:
            best_score = overlap
            best_match = ct

    return best_match if best_score >= 3 else ""


# ===== 记忆技巧生成 =====

def generate_keywords(card: m.KnowledgeCard) -> list:
    """从卡片内容生成关键词列表"""
    keywords = []
    title = card.title

    if card.answer:
        sentences = card.answer.split('。')
        first = sentences[0] if sentences else ""
        if len(first) > 5:
            text = first[:30] + "…" if len(first) > 30 else first
            keywords.append(f"{title} → {text}")

    for step in card.decomposition[:3]:
        parts = step.split(' → ')
        if len(parts) >= 2:
            concept = parts[0].strip()
            hint = parts[1].replace('为什么？', '').strip()[:15]
            keywords.append(f"{concept} → {hint}")

    if len(keywords) < 3:
        keywords.append(f"{title} → {card.core_principle}")

    return keywords[:6]


def generate_hierarchy(card: m.KnowledgeCard, all_titles: list) -> str:
    """检查是否有层级结构，生成 Mermaid 图"""
    title = card.title
    composition_kw = ['要素', '阶段', '步骤', '类型', '组成', '分类', '方面', '维度', '种', '类', '机理']
    has_comp = any(kw in title for kw in composition_kw)

    nodes = []
    for step in card.decomposition[:5]:
        concept = step.split(' → ')[0].strip() if ' → ' in step else step[:20]
        concept = re.sub(r'[：:（(].*', '', concept).strip()
        if concept and len(concept) <= 25:
            nodes.append(concept)

    if has_comp and len(nodes) >= 2:
        lines = ["```mermaid", "flowchart TB"]
        safe_title = title.replace('"', "'")
        lines.append(f'    Root["{safe_title}"]')
        for i, node in enumerate(nodes[:5]):
            safe_node = node.replace('"', "'")
            lines.append(f'    Root --> N{i}["{safe_node}"]')
        lines.append("```")
        return "\n".join(lines)

    return None


def generate_comparison_table(card: m.KnowledgeCard) -> list:
    """检查是否有对比需求，生成对比表格"""
    if any(kw in card.title for kw in ['同一性', '差异性']):
        if '同一性' in card.title:
            return [
                "| 同一性维度 | 具体表现 |",
                "|-----------|--------|",
                "| 能量条件 | 均依赖地形高差和重力势能 |",
                "| 固相物质条件 | 均需要松散岩土体 |",
                "| 液相物质条件 | 均需要水的参与 |",
                "| 触发条件 | 降雨/地震/人类活动是共同触发因素 |",
            ]
        if '差异性' in card.title:
            return [
                "| 比较维度 | 滑坡 | 泥石流 | 崩塌 |",
                "|---------|------|--------|------|",
                "| 坡度要求 | 15-50° | 需汇水地形 | 45-60° |",
                "| 物质组成 | 整体土体 | 松散堆积物+水 | 岩块 |",
                "| 含水量要求 | 低 | 高(40-60%) | 几乎无 |",
            ]

    if '异同' in card.title:
        return [
            "| 比较维度 | 灾害群 | 灾害链 | 灾害遭遇 |",
            "|---------|--------|--------|---------|",
            "| 因果关系 | 无因果关联 | 有直接因果 | 无因果，巧合叠加 |",
            "| 时空关系 | 同区域同时段集中 | 时间先后递进 | 同时或相继发生 |",
            "| 各灾种独立性 | 相互独立 | 相互依存 | 相互独立 |",
        ]

    return []


# ===== 主流程 =====

def main():
    answer_file = project_root / "output" / "processed" / "灾害学_复习题答案.md"
    v4_json = project_root / "output" / "json" / "灾害学_v4.json"

    if not answer_file.exists():
        print(f"答案文件不存在: {answer_file}")
        return
    if not v4_json.exists():
        print(f"v4 JSON 不存在: {v4_json}")
        return

    with open(v4_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    qa_map = parse_answers(str(answer_file))
    card_titles = [c["title"] for c in data["cards"]]

    print(f"解析出复习题: {len(qa_map)} 道")
    for t in qa_map:
        print(f"  [{t}] ({len(qa_map[t])} 字)")

    # 标题匹配 - 优先匹配非空答案，已经匹配的不再覆盖
    matched_count = 0
    qa_mapped = {}
    for q_title, q_answer in sorted(qa_map.items(), key=lambda x: -len(x[1])):
        matched = match_title(q_title, card_titles)
        if matched and matched not in qa_mapped:
            qa_mapped[matched] = q_answer
            matched_count += 1
            print(f"  ✅ [{q_title}] → [{matched}] ({len(q_answer)} 字)")
        elif matched and matched in qa_mapped:
            # 如果已有答案为空，用非空替代
            if not qa_mapped[matched] and q_answer:
                qa_mapped[matched] = q_answer
                print(f"  🔄 [{q_title}] → [{matched}] 更新为非空答案 ({len(q_answer)} 字)")
        else:
            print(f"  ❌ [{q_title}] → 未匹配")

    print(f"\n匹配: {matched_count}/{len(qa_map)}")

    # 填入答案并生成记忆技巧
    for card in data["cards"]:
        ct = card["title"]
        if ct in qa_mapped:
            card["answer"] = qa_mapped[ct]
            card["answer_source"] = "user_specified"
            print(f"  填入答案: {ct}")

        kc = m.KnowledgeCard(
            title=card["title"],
            answer=card["answer"],
            answer_source=card["answer_source"],
            core_principle=card["core_principle"],
            problem_solved=card["problem_solved"],
            decomposition=card["decomposition"],
            scenario_question=card["scenario_question"],
            judgment_chain=card["judgment_chain"],
            judgment_conclusion=card["judgment_conclusion"],
            memory_techniques=m.MemoryTechniques(),
            knowledge_interfaces=card["knowledge_interfaces"],
        )

        card["memory_techniques"] = m.MemoryTechniques(
            keywords=generate_keywords(kc),
            hierarchy=generate_hierarchy(kc, data["all_knowledge_titles"]),
            comparison_tables=generate_comparison_table(kc),
        ).to_dict()

    # 输出版本
    data["version"] = 5
    data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    json_dir = project_root / "output" / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    v5_path = json_dir / "灾害学_v5.json"
    with open(v5_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nJSON → {v5_path}")

    # 从 JSON 重建 Markdown
    print("正在生成 Markdown...")
    from scripts.card_generator import generate_markdown, generate_json as gen_json
    from scripts import models as m2

    def _dict_to_card(c: dict) -> m2.KnowledgeCard:
        return m2.KnowledgeCard.from_dict(c)

    pack = m2.CardPack(
        subject=data["subject"],
        source_file=data["source_file"],
        cards=[_dict_to_card(c) for c in data["cards"]],
        generated_at=data["generated_at"],
        version=data["version"],
        all_knowledge_titles=data["all_knowledge_titles"],
    )

    md_dir = project_root / "output" / "markdown"
    # 写 JSON
    gen_json(pack, str(json_dir))
    # 写 Markdown
    md_content, md_path = generate_markdown(pack, str(md_dir))
    print(f"Markdown → {md_path}")

    answered = sum(1 for c in data["cards"] if c["answer"])
    has_kw = sum(1 for c in data["cards"] if c["memory_techniques"]["keywords"])
    print(f"\n完成！已填入答案: {answered}/{len(data['cards'])} 张，记忆技巧: {has_kw}/{len(data['cards'])} 张")


if __name__ == "__main__":
    main()