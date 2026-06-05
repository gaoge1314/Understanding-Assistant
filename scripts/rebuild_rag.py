"""
LightRAG 重跑脚本（中文模式）
1. 设置 SUMMARY_LANGUAGE=Chinese
2. 清除旧缓存
3. 重新插入卡片数据
"""

import os
import sys
import asyncio
import json
import logging
import logging.config
from functools import partial
from pathlib import Path

# 核心：设置中文输出
os.environ["SUMMARY_LANGUAGE"] = "Chinese"

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.llm.ollama import ollama_embed
from lightrag.utils import EmbeddingFunc, logger, set_verbose_debug


# ===== 配置 =====
WORKING_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rag_storage")
JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "json", "灾害学_v5.json")
API_KEY = "sk-894795de35f2414e85a46f5903494a7c"
API_BASE = "https://api.deepseek.com"
LLM_MODEL = "deepseek-v4-flash"


async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], keyword_extraction=False, **kwargs
) -> str:
    return await openai_complete_if_cache(
        LLM_MODEL,
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=API_KEY,
        base_url=API_BASE,
        **kwargs,
    )


async def initialize_rag():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=1024,
            max_token_size=8192,
            func=partial(
                ollama_embed.func,
                embed_model="bge-m3:latest",
                host="http://localhost:11434",
            ),
        ),
    )

    await rag.initialize_storages()  # Auto-initializes pipeline_status
    return rag


async def main():
    print("=" * 60)
    print("LightRAG 中文重跑脚本")
    print(f"SUMMARY_LANGUAGE = {os.environ.get('SUMMARY_LANGUAGE', '(not set)')}")
    print(f"工作目录: {WORKING_DIR}")
    print("=" * 60)

    # 1. 清除旧缓存文件
    files_to_delete = [
        "graph_chunk_entity_relation.graphml",
        "kv_store_doc_status.json",
        "kv_store_full_docs.json",
        "kv_store_full_entities.json",
        "kv_store_text_chunks.json",
        "vdb_chunks.json",
        "vdb_entities.json",
        "vdb_relationships.json",
        "kv_store_llm_response_cache.json",
        "pipeline_status.json",
    ]

    for file in files_to_delete:
        file_path = os.path.join(WORKING_DIR, file)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"  [已删除] {file_path}")

    print("\n缓存清除完成，开始初始化 RAG...")

    # 2. 初始化 RAG
    rag = await initialize_rag()
    print("RAG 初始化完成")

    # 3. 读取卡片数据
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 4. 构建插入文本：卡片标题 + 答案
    insert_texts = []
    for card in data["cards"]:
        text = f"## {card['title']}\n\n{card['answer']}"
        insert_texts.append(text)
    full_text = "\n\n".join(insert_texts)

    print(f"\n卡片总数: {len(data['cards'])}")
    print(f"总文本长度: {len(full_text)} 字符")
    print("开始插入文档到 LightRAG（预计需要几分钟）...\n")

    # 5. 插入文档
    await rag.ainsert(full_text)

    print("\n" + "=" * 60)
    print("✅ LightRAG 插入完成！")
    print("=" * 60)

    # 6. 确保所有存储完成
    await rag.finalize_storages()


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.