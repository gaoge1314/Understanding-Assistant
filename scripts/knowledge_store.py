import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import CardPack


class KnowledgeStore:
    """读取和写入卡包数据"""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        self.base_dir = base_dir
        self._ensure_dirs()

    def _ensure_dirs(self):
        for sub in ("json", "markdown", "knowledge", "processed"):
            Path(self.base_dir, sub).mkdir(parents=True, exist_ok=True)

    def save_pack(self, pack: CardPack, include_markdown: bool = True) -> dict:
        result = {}

        # JSON 输出
        json_dir = os.path.join(self.base_dir, "json")
        Path(json_dir).mkdir(parents=True, exist_ok=True)
        json_path = os.path.join(json_dir, f"{pack.subject}_v{pack.version}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(pack.to_dict(), f, ensure_ascii=False, indent=2)
        result["json_path"] = json_path

        return result

    def load_pack(self, subject: str, version: int = None) -> Optional[CardPack]:
        json_dir = os.path.join(self.base_dir, "json")
        if not os.path.isdir(json_dir):
            return None

        if version is not None:
            path = os.path.join(json_dir, f"{subject}_v{version}.json")
            if os.path.isfile(path):
                return self._read_json(path)
            return None

        # 找最新版本
        files = [f for f in os.listdir(json_dir) if f.startswith(f"{subject}_v") and f.endswith(".json")]
        if not files:
            return None
        files.sort(key=lambda x: int(x.split("_v")[1].split(".")[0]), reverse=True)
        return self._read_json(os.path.join(json_dir, files[0]))

    def _read_json(self, path: str) -> CardPack:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CardPack.from_dict(data)