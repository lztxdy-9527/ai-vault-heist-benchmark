# -*- coding: utf-8 -*-
"""
Official Antigravity (AGY) Lifecycle Hook Logger (`agy_hook_logger.py`)
Triggered via `.agents/hooks.json` on `SessionStart` / `Stop` inside AGY exam rooms.
Reads JSON hook payload from stdin, binds `conversationId` + `transcriptPath` to the
matched exam room (`agy_session_binding.json`), and outputs `{}` to stdout.
Never accesses undocumented internals or credentials.
"""

from __future__ import annotations
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional


def _resolve_room_dir(payload: Dict[str, Any]) -> Optional[Path]:
    candidates = []
    for p in payload.get("workspacePaths") or []:
        if isinstance(p, str) and p:
            candidates.append(Path(p))
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd:
        candidates.append(Path(cwd))
    # Fallback: parent of .agents directory where hooks.json lives
    candidates.append(Path.cwd().parent)
    candidates.append(Path.cwd())

    for cand in candidates:
        try:
            res = cand.resolve()
        except Exception:
            continue
        if (res / "RULES_FULL_v22.md").exists() or "exam_rooms" in res.parts:
            if res.name == ".agents":
                return res.parent
            return res
    return None


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {"raw_parse_error": True}

    room_dir = _resolve_room_dir(payload)
    if room_dir is not None and room_dir.exists():
        binding_path = room_dir / "agy_session_binding.json"
        existing: Dict[str, Any] = {"sessions": {}}
        if binding_path.exists():
            try:
                existing = json.loads(binding_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {"sessions": {}}

        cid = str(payload.get("conversationId") or "").strip()
        if cid:
            sessions = existing.setdefault("sessions", {})
            rec = sessions.get(cid, {})
            rec.update({
                "conversationId": cid,
                "transcriptPath": payload.get("transcriptPath") or rec.get("transcriptPath", ""),
                "modelName": payload.get("modelName") or rec.get("modelName", ""),
                "lastHookEvent": payload.get("hookEventName", ""),
                "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })
            sessions[cid] = rec
            existing["primaryConversationId"] = cid
            existing["updatedAt"] = rec["updatedAt"]
            binding_path.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    sys.stdout.write("{}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
