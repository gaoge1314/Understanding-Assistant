from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MemoryTechniques:
    """记忆技巧 — AI 自动从卡片内容生成"""
    keywords: List[str] = field(default_factory=list)
    hierarchy: Optional[str] = None
    comparison_tables: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "keywords": self.keywords,
            "hierarchy": self.hierarchy,
            "comparison_tables": self.comparison_tables,
        }

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "MemoryTechniques":
        if not d:
            return cls()
        return cls(
            keywords=d.get("keywords", []),
            hierarchy=d.get("hierarchy"),
            comparison_tables=d.get("comparison_tables", []),
        )


@dataclass
class KnowledgeInterface:
    """知识接口 — 结构化卡片间引用"""
    target_card_id: str = ""          # 目标卡片唯一标识
    target_title: str = ""            # 目标卡片标题（用于显示）
    relation: str = ""                # 关系描述
    raw_text: str = ""                # 原始文本（用于降级展示）

    def to_dict(self) -> dict:
        return {
            "target_card_id": self.target_card_id,
            "target_title": self.target_title,
            "relation": self.relation,
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, d) -> "KnowledgeInterface":
        if isinstance(d, str):
            # 后向兼容：旧格式是纯字符串
            return cls(raw_text=d)
        return cls(
            target_card_id=d.get("target_card_id", ""),
            target_title=d.get("target_title", ""),
            relation=d.get("relation", ""),
            raw_text=d.get("raw_text", ""),
        )


@dataclass
class KnowledgeCard:
    title: str
    card_id: str = ""                 # ★ 唯一标识，由标题生成

    # ① 答案
    answer: str = ""
    answer_source: str = ""  # "user_specified" | "ai_extracted" | "ai_generated"

    # ② 理解路径
    core_principle: str = ""
    problem_solved: str = ""
    decomposition: List[str] = field(default_factory=list)
    scenario_question: str = ""
    judgment_chain: List[str] = field(default_factory=list)
    judgment_conclusion: str = ""

    # ③ 记忆技巧
    memory_techniques: Optional[MemoryTechniques] = None

    # ④ 知识接口（后向兼容，新数据由 relations 替代）
    knowledge_interfaces: List[KnowledgeInterface] = field(default_factory=list)

    # ⑤ 关联（替代 knowledge_interfaces）
    relations: List[dict] = field(default_factory=list)

    # 语义画像（中间概念层产物）
    semantic_profile: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "card_id": self.card_id,
            "title": self.title,
            "answer": self.answer,
            "answer_source": self.answer_source,
            "core_principle": self.core_principle,
            "problem_solved": self.problem_solved,
            "decomposition": self.decomposition,
            "scenario_question": self.scenario_question,
            "judgment_chain": self.judgment_chain,
            "judgment_conclusion": self.judgment_conclusion,
            "memory_techniques": self.memory_techniques.to_dict() if self.memory_techniques else None,
            "knowledge_interfaces": [k.to_dict() for k in self.knowledge_interfaces],
            "relations": self.relations,
            "semantic_profile": self.semantic_profile,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KnowledgeCard":
        card = cls(title=d.get("title", ""))
        card.card_id = d.get("card_id", "")
        card.answer = d.get("answer", "")
        card.answer_source = d.get("answer_source", "")
        card.core_principle = d.get("core_principle", "")
        card.problem_solved = d.get("problem_solved", "")
        card.decomposition = d.get("decomposition", [])
        card.scenario_question = d.get("scenario_question", "")
        # 后向兼容：旧 JSON 的 scenario_answer → judgment_conclusion
        card.judgment_conclusion = d.get("judgment_conclusion", "") or d.get("scenario_answer", "")
        card.judgment_chain = d.get("judgment_chain", [])
        card.memory_techniques = MemoryTechniques.from_dict(d.get("memory_techniques"))
        # 知识接口：兼容旧格式（List[str]）和新格式（List[dict]）
        raw_ifaces = d.get("knowledge_interfaces", [])
        card.knowledge_interfaces = [KnowledgeInterface.from_dict(item) for item in raw_ifaces]
        # 关联（v5+ 新字段）
        card.relations = d.get("relations", [])
        # 语义画像（v5+ 新字段）
        card.semantic_profile = d.get("semantic_profile", {})
        return card


@dataclass
class CardPack:
    subject: str
    source_file: str
    cards: List[KnowledgeCard]
    generated_at: str
    version: int = 1
    all_knowledge_titles: Optional[List[str]] = None

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "source_file": self.source_file,
            "generated_at": self.generated_at,
            "version": self.version,
            "all_knowledge_titles": self.all_knowledge_titles or [],
            "cards": [c.to_dict() for c in self.cards],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CardPack":
        return cls(
            subject=d.get("subject", ""),
            source_file=d.get("source_file", ""),
            cards=[KnowledgeCard.from_dict(c) for c in d.get("cards", [])],
            generated_at=d.get("generated_at", ""),
            version=d.get("version", 1),
            all_knowledge_titles=d.get("all_knowledge_titles"),
        )