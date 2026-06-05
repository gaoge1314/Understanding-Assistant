"""临时脚本：列出图谱中所有实体名"""
import xml.etree.ElementTree as ET

tree = ET.parse(r"c:\Users\12977\Desktop\jiyikapian\rag_storage\graph_chunk_entity_relation.graphml")
ns = {"g": "http://graphml.graphdrawing.org/xmlns"}

entities = []
for n in tree.findall(".//g:node", ns):
    d0 = n.find("g:data[@key='d0']", ns)
    if d0 is not None and d0.text:
        entities.append(d0.text)

# 按长度降序排列，长实体更有可能是具体概念
entities.sort(key=lambda x: (-len(x), x))

print(f"=== 图谱实体总览 (共 {len(entities)} 个) ===\n")
for i, e in enumerate(entities, 1):
    print(f"{i:3d}. [{len(e):2d}字] {e}")