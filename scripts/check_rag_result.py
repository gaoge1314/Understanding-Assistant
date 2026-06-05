"""临时检查脚本：查看 LightRAG 新输出的图谱"""
import os, xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files = [
    "rag_storage/graph_chunk_entity_relation.graphml",
    "rag_storage/kv_store_full_entities.json",
    "rag_storage/kv_store_full_relations.json",
]

for f in files:
    path = os.path.join(BASE, f)
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"✅ {f}  ({size:,} bytes)")
    else:
        print(f"❌ {f}  不存在")

graphml = os.path.join(BASE, "rag_storage/graph_chunk_entity_relation.graphml")
if os.path.exists(graphml):
    tree = ET.parse(graphml)
    root = tree.getroot()
    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
    nodes = root.findall(".//g:node", ns)
    edges = root.findall(".//g:edge", ns)
    print(f"\n📊 图谱统计: {len(nodes)} 节点, {len(edges)} 边")

    print("\n📋 前 20 个节点示例 (中文实体名):")
    for n in nodes[:20]:
        d0 = n.find("g:data[@key='d0']", ns)
        label = d0.text if d0 is not None else "(无标签)"
        print(f"   {label}")

    # 检查是否有英文实体
    import re
    en_count = 0
    for n in nodes:
        d0 = n.find("g:data[@key='d0']", ns)
        label = d0.text if d0 is not None else ""
        if label and re.search(r'[a-zA-Z]', label):
            en_count += 1
            if en_count <= 10:
                print(f"   ⚠️ 英文实体: {label}")
    print(f"\n⚠️ 含英文的实体数: {en_count}/{len(nodes)}")
print("\n--- 完成 ---")