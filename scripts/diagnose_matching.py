"""临时诊断脚本：分析卡片标题与 LightRAG 实体名的匹配问题"""
import json
import os
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. 读卡片标题
with open(os.path.join(BASE, "output", "json", "灾害学_v5.json"), "r", encoding="utf-8") as f:
    pack = json.load(f)
titles = [c["title"] for c in pack["cards"]]

# 2. 读图谱实体名
graphml = os.path.join(BASE, "rag_storage", "graph_chunk_entity_relation.graphml")
tree = ET.parse(graphml)
ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
entities = []
for n in tree.findall(".//g:node", ns):
    d0 = n.find("g:data[@key='d0']", ns)
    if d0 is not None and d0.text:
        entities.append(d0.text)

# 3. 精确匹配
exact_matched = set()
for t in titles:
    if t in entities:
        exact_matched.add(t)

# 4. 包含匹配
contain_matched = set(exact_matched)
contain_mapping = {}
for t in titles:
    if t in contain_matched:
        continue
    for e in entities:
        if t in e or e in t:
            contain_matched.add(t)
            contain_mapping[t] = e
            break

# 5. 关键词匹配：取标题中最有区分度的关键词
# 去除标点、空格、括号内容，提取核心名词
import re

def extract_keywords(title):
    """提取标题中的关键词"""
    # 去除括号及其内容
    cleaned = re.sub(r'[（(][^）)]*[）)]', '', title)
    # 去除引号书名号
    cleaned = re.sub(r'[《》""「」]', '', cleaned)
    # 按分隔符拆分
    parts = re.split(r'[、，,\s]', cleaned)
    # 取最长部分（通常是核心概念）
    parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]
    return parts

keyword_matched = set(contain_matched)
keyword_mapping = {}
unmatched = []
for t in titles:
    if t in keyword_matched:
        continue
    keywords = extract_keywords(t)
    best_match = None
    best_score = 0
    for e in entities:
        score = sum(1 for kw in keywords if kw in e)
        if score > best_score:
            best_score = score
            best_match = e
    if best_match and best_score >= 1:
        keyword_matched.add(t)
        keyword_mapping[t] = (best_match, best_score)
    else:
        unmatched.append(t)

# 6. 输出报告
print("=" * 60)
print(f"卡片总数: {len(titles)}")
print(f"图谱实体数: {len(entities)}")
print(f"\n精确匹配: {len(exact_matched)} 张")
print(f"包含匹配(+): {len(contain_matched) - len(exact_matched)} 张")
print(f"关键词匹配(+): {len(keyword_matched) - len(contain_matched)} 张")
print(f"\n总匹配: {len(keyword_matched)}/{len(titles)}")
print(f"未匹配: {len(unmatched)}/{len(titles)}")

if unmatched:
    print("\n" + "=" * 60)
    print("=== 未匹配的卡片及其相似实体 ===")
    print("=" * 60)
    for t in unmatched:
        print(f"\n❌ 卡片: {t}")
        keywords = extract_keywords(t)
        # 找最相似的实体（含任意关键词的）
        similar = []
        for e in entities:
            for kw in keywords:
                if kw in e:
                    similar.append(e)
                    break
        if similar:
            print(f"   关键词: {keywords}")
            print(f"   相似实体 (部分): {similar[:5]}")
        else:
            print(f"   关键词: {keywords}")
            print(f"   无相似实体")

print("\n" + "=" * 60)
print("=== 包含匹配的映射 ===")
for t, e in contain_mapping.items():
    print(f"  {t}  ↔  {e}")

print("\n=== 关键词匹配的映射 ===")
for t, (e, score) in keyword_mapping.items():
    print(f"  {t}  ↔  {e}  (score={score})")