# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from typing import Optional

from app.models.knowledge_base import KnowledgeEntry

logger = get_logger(__name__)


class TrainingDataFormatterService:

    def format_entry(self, entry: KnowledgeEntry) -> list[dict]:
        content = entry.content or ""
        title = entry.title or ""

        # Q&A format: "Q: ...\n\nA: ..."
        if "Q:" in content and "A:" in content:
            return self._format_qa_content(content, entry)

        # Multi-turn conversation format: alternating User/Assistant lines
        if content.count("User:") > 1 and "Assistant:" in content:
            return self._format_multi_turn(content, entry)

        # Default: title is instruction, content is response
        if title and content:
            return [{
                "instruction": title.strip(),
                "response": content.strip(),
                "is_multi_turn": False,
                "turn_index": 0,
            }]

        return []

    def _format_qa_content(self, content: str, entry: KnowledgeEntry) -> list[dict]:
        pairs = []
        # Split on "Q:" to find multiple Q&A pairs
        parts = content.split("Q:")
        for part in parts:
            part = part.strip()
            if not part or "A:" not in part:
                continue
            q_part, a_part = part.split("A:", 1)
            q = q_part.strip()
            a = a_part.strip()
            if q and a:
                pairs.append({
                    "instruction": q,
                    "response": a,
                    "is_multi_turn": False,
                    "turn_index": 0,
                })
        return pairs

    def _format_multi_turn(self, content: str, entry: KnowledgeEntry) -> list[dict]:
        pairs = []
        lines = content.split("\n")
        current_user = None
        current_assistant = None
        turn_idx = 0

        for line in lines:
            line = line.strip()
            if line.startswith("User:"):
                if current_user and current_assistant:
                    pairs.append({
                        "instruction": current_user,
                        "response": current_assistant,
                        "is_multi_turn": True,
                        "turn_index": turn_idx,
                    })
                    turn_idx += 1
                current_user = line[5:].strip()
                current_assistant = None
            elif line.startswith("Assistant:"):
                current_assistant = line[10:].strip()

        # Last pair
        if current_user and current_assistant:
            pairs.append({
                "instruction": current_user,
                "response": current_assistant,
                "is_multi_turn": True,
                "turn_index": turn_idx,
            })

        return pairs

    def export_jsonl(self, examples: list[dict]) -> str:
        lines = []
        for ex in examples:
            record = {
                "messages": [
                    {"role": "user", "content": ex.get("instruction", "")},
                    {"role": "assistant", "content": ex.get("response", "")},
                ]
            }
            lines.append(json.dumps(record, ensure_ascii=False))
        return "\n".join(lines)
