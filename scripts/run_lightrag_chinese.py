"""
LightRAG 中文重跑脚本
设置 SUMMARY_LANGUAGE=Chinese，让 LightRAG 输出全中文实体
"""
import os
import sys
import json
import asyncio
import logging
import logging.config
from functools import partial

# ========== 核心设置：中文输出 ==========
os.environ["SUMMARY_LANGUAGE"] = "Chinese"  # 关键：告诉 LLM 用中文输出

# ========== LLM 配置：DeepSeek ==========
os.environ["LLM_MODEL"] = "deepseek-v4-flash"
os.environ["LLM_BINDING_HOST"] = "https://api.deepseek.com"
os.environ["LLM_BINDING_API_KEY"] = "sk-894795de35f2414e85a46f5903494a7c"

# ========== Embedding 配置：Ollama bge-m3 ==========
os.environ["EMBEDDING_MODEL"] = "bge-m3:latest"
os.environ["EMBEDDING_BINDING_HOST"] = "http://localhost:11434"
os.environ["EMBEDDING_DIM"] = "1024"
os.environ["MAX_EMBED_TOKENS"] = "8192"

# 项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_DIR = os.path.join(BASE_DIR, "rag_storage")
JSON_PATH = os.path.join(BASE_DIR, "output", "json", "灾害学_v5.json")

sys.path.insert(0, os.path.join(BASE_DIR, "LightRAG-main"))

from lightrag import LightRAG
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.llm.ollama import ollama_embed
from lightrag.utils import EmbeddingFunc, logger


async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], keyword_extraction=False, **kwargs
) -> str:
    return await openai_complete_if_cache(
        os.getenv("LLM_MODEL", "deepseek-chat"),
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=os.getenv("LLM_BINDING_API_KEY"),
        base_url=os.getenv("LLM_BINDING_HOST", "https://api.deepseek.com"),
        **kwargs,
    )


def configure_logging():
    """配置日志"""
    log_file = os.path.join(BASE_DIR, "rag_storage", "lightrag_chinese_run.log")
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": "%(levelname)s: %(message)s"},
            "detailed": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
        },
        "handlers": {
            "console": {"formatter": "default", "class": "logging.StreamHandler", "stream": "ext://sys.stderr"},
            "file": {"formatter": "detailed", "class": "logging.handlers.RotatingFileHandler",
                     "filename": log_file, "maxBytes": 10485760, "backupCount": 3, "encoding": "utf-8"},
        },
        "loggers": {"lightrag": {"handlers": ["console", "file"], "level": "INFO", "propagate": False}},
    })
    logger.setLevel(logging.INFO)


def clean_cache():
    """清除旧缓存文件，让 LightRAG 重新抽取"""
    files_to_delete = [
        "graph_chunk_entity_relation.graphml",
        "kv_store_doc_status.json",
        "kv_store_full_docs.json",
        "kv_store_text_chunks.json",
        "kv_store_entity_chunks.json",
        "kv_store_relation_chunks.json",
        "kv_store_full_entities.json",
        "kv_store_full_relations.json",
        "kv_store_llm_response_cache.json",
    ]
    for file_name in files_to_delete:
        file_path = os.path.join(WORKING_DIR, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"  已清除: {file_name}")


async def main():
    configure_logging()

    # 1. 清除旧缓存
    print("=" * 50)
    print("步骤1: 清除旧缓存")
    print("=" * 50)
    clean_cache()

    # 2. 初始化 LightRAG（带中文语言设置）
    print("\n" + "=" * 50)
    print("步骤2: 初始化 LightRAG（SUMMARY_LANGUAGE=Chinese）")
    print("=" * 50)

    # ========== 中文实体类型指导（覆盖英文默认值）==========
    CHINESE_ENTITY_GUIDANCE = """使用以下类型之一对每个实体进行分类。如果没有合适的类型，请使用「其他」。

**关键规则：所有实体名称必须使用中文输出，不得使用英文名称。** 专有名词（如人名、地名、组织名）若无通用中文译名才可保留原文。

- 概念: 抽象思想、理论、原理、信念、学科
- 方法: 流程、程序、技术、算法、策略、工作流程
- 事件: 发生的事件、事故、灾害、会议、过程
- 地点: 地理位置（城市、国家、建筑、区域、自然地点）
- 组织: 公司、机构、政府机构、研究院、团体
- 人物: 真实或虚构的个人、研究者、专家
- 内容: 创造性或信息性作品（书籍、文章、报告、文档）
- 数据: 定量或结构化信息（统计数据、数据集、测量结果）
- 自然物: 非生命自然物体（矿物、化学物质、天体）"""

    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=int(os.getenv("EMBEDDING_DIM", "1024")),
            max_token_size=int(os.getenv("MAX_EMBED_TOKENS", "8192")),
            func=partial(
                ollama_embed.func,
                embed_model=os.getenv("EMBEDDING_MODEL", "bge-m3:latest"),
                host=os.getenv("EMBEDDING_BINDING_HOST", "http://localhost:11434"),
            ),
        ),
        addon_params={
            "language": "Chinese",
            "entity_types_guidance": CHINESE_ENTITY_GUIDANCE,  # 中文实体类型指导
        },
    )
    await rag.initialize_storages()
    print("  初始化完成")

    # 3. 读取卡片数据
    print("\n" + "=" * 50)
    print("步骤3: 读取卡片数据")
    print("=" * 50)
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    cards = data["cards"]
    print(f"  共 {len(cards)} 张卡片")

    # 4. 逐张插入卡片
    print("\n" + "=" * 50)
    print("步骤4: 插入卡片文本到 LightRAG（将输出中文实体）")
    print("=" * 50)

    for i, card in enumerate(cards, 1):
        title = card["title"]
        answer = card.get("answer", "")
        print(f"  [{i}/{len(cards)}] {title}...", end=" ", flush=True)

        # 构建插入文本：标题 + 答案
        text = f"## {title}\n\n{answer}"

        try:
            await rag.ainsert(text)
            print("✓")
        except Exception as e:
            print(f"✗ 错误: {e}")

    # 5. 保存
    print("\n" + "=" * 50)
    print("步骤5: 保存存储")
    print("=" * 50)
    await rag.finalize_storages()
    print("  保存完成")

    # 6. 检查结果
    graphml_path = os.path.join(WORKING_DIR, "graph_chunk_entity_relation.graphml")
    if os.path.exists(graphml_path):
        import xml.etree.ElementTree as ET
        tree = ET.parse(graphml_path)
        root = tree.getroot()
        ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
        nodes = root.findall(".//g:node", ns)
        edges = root.findall(".//g:edge", ns)
        print(f"\n  图谱生成成功!")
        print(f"  节点数: {len(nodes)}")
        print(f"  边数: {len(edges)}")

        # 显示前10个节点名称（检查是否中文）
        print(f"\n  前10个节点示例:")
        for node in nodes[:10]:
            data_elem = node.find("g:data[@key='d0']", ns)
            label = data_elem.text if data_elem is not None else "(无标签)"
            print(f"    - {label}")
    else:
        print(f"\n  警告: 图谱文件未生成，可能需要运行 LightRAG 服务器模式")

    print("\n" + "=" * 50)
    print("完成! LightRAG 中文抽取完成")
    print("接下来运行: python scripts/build_relations.py")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())