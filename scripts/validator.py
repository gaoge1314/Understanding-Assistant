"""
卡包数据校验器
"""

from typing import List

from .models import CardPack


class ValidationError(Exception):
    pass


def validate_card_pack(pack: CardPack) -> List[str]:
    errors = []
    for i, card in enumerate(pack.cards):
        prefix = f"卡片 {i+1}（{card.title}）"
        if not card.title:
            errors.append(f"{prefix}：知识点名称为空")
        if not card.answer:
            errors.append(f"{prefix}：答案为空")
        if card.answer_source not in ("user_specified", "ai_extracted", "ai_generated", ""):
            errors.append(f"{prefix}：答案来源无效（{card.answer_source}）")
        if not card.core_principle:
            errors.append(f"{prefix}：核心原理为空")
        if not card.problem_solved:
            errors.append(f"{prefix}：'它解决了什么问题'为空")
        if not card.decomposition:
            errors.append(f"{prefix}：分解理解为空")
        else:
            for j, step in enumerate(card.decomposition):
                if step.startswith("<!-- mermaid -->"):
                    continue
        if not card.scenario_question:
            errors.append(f"{prefix}：典型判断情境题目为空")
        if not card.judgment_chain or len(card.judgment_chain) < 2:
            errors.append(f"{prefix}：判断链少于2步（当前{len(card.judgment_chain)}步）")
        if not card.judgment_conclusion:
            errors.append(f"{prefix}：判断结论为空")
        if not card.memory_techniques or not card.memory_techniques.keywords:
            errors.append(f"{prefix}：记忆技巧关键词为空")
        if len(card.knowledge_interfaces) < 1:
            errors.append(f"{prefix}：知识接口为空（当前{len(card.knowledge_interfaces)}条）")
    return errors