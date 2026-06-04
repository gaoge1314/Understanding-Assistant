"""
迁移脚本：将旧版 Markdown 卡包（理解路径卡包格式 v3）升级为新版（知识卡包格式 v4）
保留所有现有数据，新字段填充为空，直接输出 Markdown 和 JSON（跳过校验）。
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from scripts.models import CardPack, KnowledgeCard, MemoryTechniques


def parse_old_markdown(filepath: str) -> CardPack:
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    subject = re.search(r'# 📚 《(.+?)》', text)
    subject = subject.group(1) if subject else "未知科目"

    time_match = re.search(r'生成时间：(.+?) \|', text)
    generated_at = time_match.group(1) if time_match else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    card_blocks = re.split(r'\n---\n\n## 卡片 \d+/\d+：', text)
    card_blocks = card_blocks[1:] if len(card_blocks) > 1 else []

    cards = []
    for block in card_blocks:
        title = block.split('\n')[0].strip()

        cp = re.search(r'### 💡 核心原理\s*(.+?)(?=\n### |\Z)', block, re.DOTALL)
        core_principle = cp.group(1).strip() if cp else ''

        ps = re.search(r'### 🎯 它解决了什么问题\s*(.+?)(?=\n### |\Z)', block, re.DOTALL)
        problem_solved = ps.group(1).strip() if ps else ''

        dec = re.search(r'### 🔧 分解理解\s*\n(.*?)(?=\n### |\Z)', block, re.DOTALL)
        decomposition = []
        if dec:
            for line in dec.group(1).strip().split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    decomposition.append(line[2:])
                elif line and not line.startswith('<!--') and not line.startswith('```'):
                    decomposition.append(line)

        sq = re.search(r'\*\*题目\*\*[：:]\s*(.+?)(?:\n)', block)
        scenario_question = sq.group(1).strip() if sq else ''

        jc = re.search(r'\*\*判断链\*\*[：:]\s*\n(.*?)(?=\n\*\*结论\*\*|\Z)', block, re.DOTALL)
        judgment_chain = []
        if jc:
            for line in jc.group(1).strip().split('\n'):
                line = line.strip()
                if line:
                    judgment_chain.append(line)

        conc = re.search(r'\*\*结论\*\*[：:]\s*(.+?)(?:\n\n|\n---|\Z)', block, re.DOTALL)
        judgment_conclusion = conc.group(1).strip() if conc else ''

        ki = re.search(r'### 🔗 与其他知识的关键接口\s*\n(.*?)(?=\n---|\Z)', block, re.DOTALL)
        knowledge_interfaces = []
        if ki:
            for line in ki.group(1).strip().split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    knowledge_interfaces.append(line[2:].strip())
                elif line.startswith('→'):
                    knowledge_interfaces.append(line.strip())

        card = KnowledgeCard(
            title=title,
            answer="",       # 旧数据无答案
            answer_source="",
            core_principle=core_principle,
            problem_solved=problem_solved,
            decomposition=decomposition,
            scenario_question=scenario_question,
            judgment_chain=judgment_chain,
            judgment_conclusion=judgment_conclusion,
            memory_techniques=MemoryTechniques(),
            knowledge_interfaces=knowledge_interfaces,
        )
        cards.append(card)

    return CardPack(
        subject=subject,
        source_file=str(filepath),
        cards=cards,
        generated_at=generated_at,
        version=4,
        all_knowledge_titles=[c.title for c in cards],
    )


def generate_json_v4(pack: CardPack, output_dir: str) -> dict:
    """直接生成 JSON，跳过校验"""
    json_content = json.dumps(pack.to_dict(), ensure_ascii=False, indent=2)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"{pack.subject}_v{pack.version}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json_content)
    print(f"  JSON → {json_path}")
    return json.loads(json_content)


def main():
    old_md = project_root / "output" / "markdown" / "灾害学_理解路径卡包.md"
    if not old_md.exists():
        print(f"文件不存在: {old_md}")
        return

    print("正在解析旧版 Markdown...")
    pack = parse_old_markdown(str(old_md))
    print(f"  解析完成：{len(pack.cards)} 张卡片")

    print("正在生成新版知识卡包...")
    md_dir = project_root / "output" / "markdown"
    json_dir = project_root / "output" / "json"

    from scripts.card_generator import generate_markdown
    generate_markdown(pack, str(md_dir), skip_validation=True)
    generate_json_v4(pack, str(json_dir))

    print("")
    print("迁移完成！")
    print(f"  旧文件: {old_md}（保留，未删除）")
    print(f"  新文件: {md_dir / f'{pack.subject}_知识卡包.md'}")
    print(f"  新文件: {json_dir / f'{pack.subject}_v{pack.version}.json'}")
    print("")
    print("注意：answer（答案）和 memory_techniques（记忆技巧）字段为空，")
    print("因为旧版格式不包含这些数据。如需补充，可编辑 JSON 后重新运行本脚本。")


if __name__ == "__main__":
    main()