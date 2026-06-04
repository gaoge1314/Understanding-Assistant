"""
知识卡包输出格式化工具：Markdown / JSON 输出 + 知识图谱生成
"""
import json
from pathlib import Path
from typing import Tuple

from .models import CardPack
from .validator import ValidationError, validate_card_pack


def generate_knowledge_graph(pack: CardPack) -> str:
    edges = []
    seen = set()

    for card in pack.cards:
        for iface in card.knowledge_interfaces:
            target = iface.target_title or (iface.raw_text.replace("→ ", "").split("：")[0].strip() if iface.raw_text else "")
            if target in (pack.all_knowledge_titles or []):
                edge = (card.title, target)
                if edge not in seen:
                    seen.add(edge)
                    edges.append(edge)

    if not edges:
        return ""

    all_nodes = set()
    for src, dst in edges:
        all_nodes.add(src)
        all_nodes.add(dst)

    lines = ["```mermaid", "flowchart LR"]
    node_ids = {}
    for i, title in enumerate(pack.all_knowledge_titles or [], 1):
        if title in all_nodes:
            safe = title.replace('"', "'")
            node_ids[title] = f"n{i}"
            lines.append(f'    n{i}["{safe}"]')

    for src, dst in edges:
        lines.append(f"    {node_ids[src]} --> {node_ids[dst]}")

    lines.append("```")
    return "\n".join(lines)


def generate_markdown(pack: CardPack, output_dir: str = None, skip_validation: bool = False) -> Tuple[str, str]:
    if not skip_validation:
        errors = validate_card_pack(pack)
        if errors:
            raise ValidationError("\n".join(errors))

    lines = []
    lines.append(f"# 📚 《{pack.subject}》知识卡包")
    lines.append(f"> 生成时间：{pack.generated_at} | 共 {len(pack.cards)} 张卡片 | v{pack.version}")
    lines.append("")

    # 目录
    lines.append("## 📑 目录")
    lines.append("")
    lines.append("| # | 知识点 | 核心原理 |")
    lines.append("|---|--------|----------|")
    for i, card in enumerate(pack.cards):
        principle_short = card.core_principle[:20] + "…" if len(card.core_principle) > 20 else card.core_principle
        lines.append(f"| {i+1} | {card.title} | {principle_short} |")
    lines.append("")
    lines.append("")

    for i, card in enumerate(pack.cards):
        lines.append("---")
        lines.append("")
        lines.append(f"## 卡片 {i+1}/{len(pack.cards)}：{card.title}")
        lines.append("")

        # ① 答案（考试默写）
        lines.append("### ① 答案（考试默写）")
        lines.append("")
        if card.answer:
            lines.append(card.answer)
        else:
            lines.append("*（数据迁移，答案字段为空。如需补充请编辑 JSON 后重新生成）*")
        lines.append("")
        if card.answer_source:
            source_label = {"user_specified": "用户指定", "ai_extracted": "AI提取", "ai_generated": "AI生成"}
            lines.append(f"> 来源：{source_label.get(card.answer_source, '未知')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ② 理解路径
        lines.append("### ② 理解路径")
        lines.append("")
        lines.append(f"**核心原理**：{card.core_principle}")
        lines.append("")
        lines.append(f"**它解决了什么问题**：{card.problem_solved}")
        lines.append("")
        lines.append("**分解理解**：")
        for step in card.decomposition:
            if step.startswith("<!-- mermaid -->"):
                lines.append(step)
            else:
                lines.append(f"- {step}")
        lines.append("")
        lines.append("**典型判断情境**：")
        lines.append(f"**题目**：{card.scenario_question}")
        lines.append("")
        lines.append("**判断链**：")
        for step in card.judgment_chain:
            lines.append(f"{step}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ③ 记忆技巧
        lines.append("### ③ 记忆技巧")
        lines.append("")

        mt = card.memory_techniques
        if mt and mt.keywords:
            lines.append("**关键词**：")
            for kw in mt.keywords:
                lines.append(f"- {kw}")
            lines.append("")

        if mt and mt.hierarchy:
            lines.append("**层级关系**：")
            lines.append(mt.hierarchy)
            lines.append("")

        if mt and mt.comparison_tables:
            lines.append("**对比表格**：")
            for table in mt.comparison_tables:
                lines.append(table)
                lines.append("")

        if not mt or not mt.keywords:
            lines.append("*（数据迁移，记忆技巧字段为空。）*")
            lines.append("")
        lines.append("---")
        lines.append("")

        # ④ 知识接口
        lines.append("### ④ 与其他知识的关键接口")
        lines.append("")
        for iface in card.knowledge_interfaces:
            display = iface.raw_text or (f"→ {iface.target_title}：{iface.relation}" if iface.target_title else "")
            lines.append(f"- {display}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # 总结表格
    lines.append("## 📊 知识点总结")
    lines.append("")
    lines.append("| 知识点 | 核心原理 | 关联知识 |")
    lines.append("|--------|----------|----------|")
    for card in pack.cards:
        interfaces = "、".join([
            iface.raw_text or (f"→ {iface.target_title}" if iface.target_title else "")
            for iface in card.knowledge_interfaces
        ])
        lines.append(f"| {card.title} | {card.core_principle} | {interfaces} |")
    lines.append("")

    # 关系图
    graph = generate_knowledge_graph(pack)
    if graph:
        lines.append("## 🔗 知识点关系图")
        lines.append("")
        lines.append(graph)
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("💪 **主动加深**（选做，效果远超再看一遍）")
    lines.append("• 禁术语复述 → 用大白话讲，不准用专业词")
    lines.append("• 找生活类比 → 找个日常场景套进去")
    lines.append("• 自己出考题 → 想一道能考倒别人的题")

    md_content = "\n".join(lines)

    md_path = None
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        md_path = out / f"{pack.subject}_理解路径卡包.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    return md_content, str(md_path) if md_path else None


def generate_json(pack: CardPack, output_dir: str = None) -> Tuple[str, str]:
    errors = validate_card_pack(pack)
    if errors:
        raise ValidationError("\n".join(errors))

    json_content = json.dumps(pack.to_dict(), ensure_ascii=False, indent=2)

    json_path = None
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        json_path = out / f"{pack.subject}_v{pack.version}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_content)

    return json_content, str(json_path) if json_path else None