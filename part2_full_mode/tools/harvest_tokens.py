# -*- coding: utf-8 -*-
"""
Half-2 Native Multi-Platform Token & Billing Harvester (`harvest_tokens.py`)

Reads ONLY documented, user-accessible local session logs across all 6 tournament platforms:
1. AGY (Antigravity): `<brain>/<conv-id>/.system_generated/logs/transcript.jsonl` (bound via `agy_session_binding.json`)
2. Codex CLI/IDE: `<LOCAL_USER_HOME>\\.codex\\sessions\\**\\rollout-*.jsonl` (matched by `session_meta.payload.cwd`)
3. OpenCode: `<LOCAL_USER_HOME>\\.local\\share\\opencode\\opencode.db` table `session_v2` (matched by `directory`)
4. DSH: `<LOCAL_USER_HOME>\\.dsh\\.dshw-usage.json` (`events` within exam time window)
5. VS Code Roo-Cline: `<LOCAL_USER_HOME>\\AppData\\Roaming\\Code\\User\\globalStorage\\hybridtalentcomputing.roo-cline-chinese\\tasks\\*\\history_item.json`
6. Manual / CodeBuddy: optional `<room>/manual_billing.json`

Preserves native units (USD / CNY / % Quota), decomposes exact 3-way tokens:
  input_uncached + input_cached + output_incl_thinking = total_tokens
Tags `[实测]` / `[估算]` / `[缺失]` and computes episode Measured Coverage %.
"""

from __future__ import annotations
import argparse
import glob
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PART2_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ROOMS_DIR = PART2_DIR / "exam_rooms"
DEFAULT_LEDGER_OUT = PART2_DIR / "docs" / "token_ledger_part2.md"

HOME = Path.home()
CODEX_SESSIONS_DIR = HOME / ".codex" / "sessions"
OPENCODE_DB_PATH = HOME / ".local" / "share" / "opencode" / "opencode.db"
DSH_USAGE_PATH = HOME / ".dsh" / ".dshw-usage.json"
ROO_TASKS_DIR = (
    HOME / "AppData" / "Roaming" / "Code" / "User" / "globalStorage"
    / "hybridtalentcomputing.roo-cline-chinese" / "tasks"
)
AGY_BRAIN_DIR = HOME / ".gemini" / "antigravity" / "brain"


from datetime import datetime


def _norm_path(p: str) -> str:
    return os.path.normcase(os.path.normpath(str(p).strip()))


def _parse_ts_epoch(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        num = float(val)
        return num / 1000.0 if num > 1e12 else num
    s = str(val).strip()
    try:
        num = float(s)
        return num / 1000.0 if num > 1e12 else num
    except ValueError:
        pass
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return None


def _load_room_binding(room_dir: Path) -> Dict[str, Any]:
    binding: Dict[str, Any] = {}
    tb_path = room_dir / "token_session_binding.json"
    if tb_path.exists():
        try:
            loaded = json.loads(tb_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                binding.update(loaded)
        except Exception:
            pass

    st_file = room_dir / ".exam_start_ts"
    if "start_epoch" not in binding or binding.get("start_epoch") is None:
        if st_file.exists():
            try:
                binding["start_epoch"] = float(st_file.read_text(encoding="utf-8").strip())
            except Exception:
                pass
    elif binding.get("start_epoch") is not None:
        binding["start_epoch"] = _parse_ts_epoch(binding["start_epoch"])

    if binding.get("end_epoch") is not None:
        binding["end_epoch"] = _parse_ts_epoch(binding["end_epoch"])

    return binding


def _window_overlaps(
    first_ts: Optional[float],
    last_ts: Optional[float],
    start_epoch: Optional[float],
    end_epoch: Optional[float],
    pre_pad: float = 60.0,
    post_pad: float = 300.0,
    default_duration: float = 2700.0,
) -> bool:
    if start_epoch is None:
        return True
    end_bound = end_epoch if end_epoch is not None else (start_epoch + default_duration)
    hi = last_ts if last_ts is not None else first_ts
    lo = first_ts if first_ts is not None else last_ts
    if lo is None or hi is None:
        return False
    return hi >= (start_epoch - pre_pad) and lo <= (end_bound + post_pad)


def _matches_filter(value: str, flt: Any) -> bool:
    if not flt:
        return True
    val_l = value.lower()
    if isinstance(flt, list):
        return any(str(item).lower() in val_l for item in flt if str(item).strip())
    return str(flt).lower() in val_l


def parse_agy_room(room_dir: Path) -> Optional[Dict[str, Any]]:
    binding = room_dir / "agy_session_binding.json"
    if not binding.exists():
        return None
    data = json.loads(binding.read_text(encoding="utf-8"))
    sessions = data.get("sessions", {})
    if not sessions:
        return None

    steps_seen = set()
    uncached = cached = c_write = output = 0
    sources: List[str] = []
    models = set()
    for cid, meta in sessions.items():
        tp = Path(meta.get("transcriptPath", ""))
        if not tp.exists():
            tp = AGY_BRAIN_DIR / cid / ".system_generated" / "logs" / "transcript.jsonl"
        if not tp.exists():
            continue
        sources.append(str(tp))
        for line in tp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            s_idx = row.get("step_index")
            key = (cid, s_idx)
            if "input_tokens" in row or "output_tokens" in row:
                if key in steps_seen:
                    continue
                steps_seen.add(key)
                uncached += int(row.get("input_tokens") or 0)
                cached += int(row.get("cache_read_tokens") or 0)
                c_write += int(row.get("cache_write_tokens") or 0)
                output += int(row.get("output_tokens") or 0)
                if row.get("model"):
                    models.add(row["model"])
    if not sources:
        return None
    return {
        "platform": "AGY",
        "status": "[实测-AGY本地日志]",
        "raw_source": ", ".join(sources),
        "uncached_input": uncached,
        "cached_input": cached,
        "cache_write": c_write,
        "output_incl_thinking": output,
        "total_tokens": uncached + cached + c_write + output,
        "native_bill": f"{len(steps_seen)} steps (model={','.join(sorted(models)) or 'AGY'})",
        "cny_est": None,
    }


def parse_codex_room(room_dir: Path, binding: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if not CODEX_SESSIONS_DIR.exists():
        return None
    binding = binding or {}
    start_epoch = binding.get("start_epoch")
    end_epoch = binding.get("end_epoch")
    session_filter = binding.get("session_id")
    model_filter = binding.get("model_filter")

    target = _norm_path(str(room_dir))
    uncached = cached = output = total = 0
    matched_files: List[str] = []
    quota_notes: List[str] = []

    for fpath in sorted(CODEX_SESSIONS_DIR.rglob("rollout-*.jsonl")):
        cwd_match = False
        sess_id: Optional[str] = None
        first_ts: Optional[float] = None
        last_ts: Optional[float] = None
        session_model: str = ""
        last_usage: Optional[Dict[str, Any]] = None
        last_rate = None
        for line in fpath.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            ev_ts = _parse_ts_epoch(d.get("timestamp"))
            if ev_ts is not None:
                first_ts = ev_ts if first_ts is None else min(first_ts, ev_ts)
                last_ts = ev_ts if last_ts is None else max(last_ts, ev_ts)

            if d.get("type") == "session_meta":
                payload = d.get("payload", {})
                cwd = payload.get("cwd")
                if cwd and _norm_path(cwd) == target:
                    cwd_match = True
                sess_id = str(payload.get("id") or sess_id or "")
                meta_ts = _parse_ts_epoch(payload.get("timestamp"))
                if meta_ts is not None:
                    first_ts = meta_ts if first_ts is None else min(first_ts, meta_ts)
                    last_ts = meta_ts if last_ts is None else max(last_ts, meta_ts)
            elif d.get("type") == "turn_context":
                m_name = d.get("payload", {}).get("model")
                if m_name:
                    session_model = str(m_name)
            elif d.get("type") == "event_msg" and d.get("payload", {}).get("type") == "token_count":
                info = d["payload"].get("info")
                if isinstance(info, dict) and info.get("total_token_usage"):
                    last_usage = info["total_token_usage"]
                if d["payload"].get("rate_limits"):
                    last_rate = d["payload"]["rate_limits"]

        if not (cwd_match and last_usage):
            continue
        if session_filter:
            sid_text = f"{sess_id or ''} {fpath.name}"
            if not _matches_filter(sid_text, session_filter):
                continue
        if model_filter and not _matches_filter(session_model, model_filter):
            continue
        if first_ts is None or last_ts is None:
            mtime = fpath.stat().st_mtime
            first_ts = first_ts or mtime
            last_ts = last_ts or mtime
        if not _window_overlaps(first_ts, last_ts, start_epoch, end_epoch, pre_pad=60.0, post_pad=300.0):
            continue

        matched_files.append(fpath.name)
        inp_all = int(last_usage.get("input_tokens") or 0)
        inp_cached = int(last_usage.get("cached_input_tokens") or 0)
        out_all = int(last_usage.get("output_tokens") or 0)
        tot = int(last_usage.get("total_tokens") or (inp_all + out_all))
        uncached += max(0, inp_all - inp_cached)
        cached += inp_cached
        output += out_all
        total += tot
        if last_rate and isinstance(last_rate.get("secondary"), dict):
            quota_notes.append(f"Plus周额度累计{last_rate['secondary'].get('used_percent')}%")

    if not matched_files:
        return None
    return {
        "platform": "Codex",
        "status": "[实测-Codex本地JSONL]",
        "raw_source": ", ".join(matched_files),
        "uncached_input": uncached,
        "cached_input": cached,
        "cache_write": None,
        "output_incl_thinking": output,
        "total_tokens": total,
        "native_bill": "; ".join(quota_notes) or "Codex Plus 订阅额度",
        "cny_est": None,
    }


def parse_opencode_room(room_dir: Path, binding: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if not OPENCODE_DB_PATH.exists():
        return None
    binding = binding or {}
    start_epoch = binding.get("start_epoch")
    end_epoch = binding.get("end_epoch")
    session_filter = binding.get("session_id")
    model_filter = binding.get("model_filter")

    target = _norm_path(str(room_dir))
    conn = sqlite3.connect(str(OPENCODE_DB_PATH))
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(session_v2)").fetchall()}
        has_times = "time_created" in cols and "time_updated" in cols
        if has_times:
            rows = conn.execute(
                "SELECT id, directory, model, cost, tokens_input, tokens_output, "
                "tokens_reasoning, tokens_cache_read, tokens_cache_write, time_created, time_updated "
                "FROM session_v2"
            ).fetchall()
        else:
            rows = [
                (*r, None, None)
                for r in conn.execute(
                    "SELECT id, directory, model, cost, tokens_input, tokens_output, "
                    "tokens_reasoning, tokens_cache_read, tokens_cache_write FROM session_v2"
                ).fetchall()
            ]
    finally:
        conn.close()

    matched = []
    for row in rows:
        sid, r_dir, r_model, cost, t_in, t_out, t_reas, t_cr, t_cw, t_created, t_updated = row
        if not (r_dir and _norm_path(r_dir) == target):
            continue
        if session_filter and not _matches_filter(str(sid), session_filter):
            continue
        if model_filter and not _matches_filter(str(r_model or ""), model_filter):
            continue
        tc = _parse_ts_epoch(t_created)
        tu = _parse_ts_epoch(t_updated)
        if start_epoch is not None and not _window_overlaps(tc, tu, start_epoch, end_epoch, pre_pad=60.0, post_pad=300.0):
            continue
        matched.append(row)

    if not matched:
        return None
    uncached = cached = output = cache_write = 0
    cost_sum = 0.0
    ids = []
    for sid, _dir, _model, cost, t_in, t_out, t_reas, t_cr, t_cw, _tc, _tu in matched:
        ids.append(sid)
        uncached += int(t_in or 0)
        cached += int(t_cr or 0)
        cache_write += int(t_cw or 0)
        output += int(t_out or 0) + int(t_reas or 0)
        cost_sum += float(cost or 0.0)
    total = uncached + cached + cache_write + output
    return {
        "platform": "OpenCode",
        "status": "[实测-opencode.db]",
        "raw_source": f"session_v2:{','.join(ids)}",
        "uncached_input": uncached,
        "cached_input": cached,
        "cache_write": cache_write,
        "output_incl_thinking": output,
        "total_tokens": total,
        "native_bill": f"db cost=${cost_sum:.4f}" if cost_sum > 0 else "本地DB未填单价(按官方单价核算)",
        "cny_est": None,
    }


def _infer_dsh_model_filter(room_dir: Path, binding: Dict[str, Any]) -> Optional[str]:
    if binding.get("model_filter"):
        return str(binding["model_filter"])
    name_l = room_dir.name.lower()
    if "deepseek" in name_l:
        return "deepseek"
    return None


def parse_dsh_window(
    start_epoch: Optional[float] = None,
    end_epoch: Optional[float] = None,
    model_filter: Any = None,
) -> Optional[Dict[str, Any]]:
    if not DSH_USAGE_PATH.exists():
        return None
    data = json.loads(DSH_USAGE_PATH.read_text(encoding="utf-8"))
    events = data.get("events", [])
    if model_filter:
        events = [e for e in events if _matches_filter(str(e.get("model") or ""), model_filter)]
    if start_epoch is not None:
        end_bound = end_epoch if end_epoch is not None else (start_epoch + 2700.0)
        events = [
            e for e in events
            if start_epoch * 1000.0 - 30_000.0 <= float(e.get("ts", 0)) <= end_bound * 1000.0 + 60_000.0
        ]
    if not events:
        return None
    tot_cost = sum(float(e.get("cost") or 0.0) for e in events)
    tot_tok = sum(int(e.get("tokens") or 0) for e in events)
    models = sorted({str(e.get("model", "")) for e in events if e.get("model")})
    return {
        "platform": "DSH",
        "status": "[实测-DSH账单总量]" if tot_tok > 0 else "[缺失-待补采]",
        "raw_source": f"{DSH_USAGE_PATH} (filter={model_filter or 'all'})",
        "uncached_input": None,
        "cached_input": None,
        "cache_write": None,
        "output_incl_thinking": None,
        "total_tokens": tot_tok,
        "native_bill": f"¥{tot_cost:.2f} ({','.join(models)})",
        "cny_est": round(tot_cost, 2),
    }


def parse_roocline_room(room_dir: Path, binding: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if not ROO_TASKS_DIR.exists():
        return None
    binding = binding or {}
    start_epoch = binding.get("start_epoch")
    end_epoch = binding.get("end_epoch")
    session_filter = binding.get("session_id")
    model_filter = binding.get("model_filter")

    target = _norm_path(str(room_dir))
    tin = tout = c_write = c_read = 0
    cost_sum = 0.0
    tids = []
    for hi in ROO_TASKS_DIR.glob("*/history_item.json"):
        try:
            d = json.loads(hi.read_text(encoding="utf-8"))
        except Exception:
            continue
        ws = d.get("workspace")
        if not (ws and _norm_path(ws) == target):
            continue
        tid = hi.parent.name
        if session_filter and not _matches_filter(f"{tid} {d.get('id', '')}", session_filter):
            continue
        if model_filter and not _matches_filter(str(d.get("model") or ""), model_filter):
            continue
        ts = _parse_ts_epoch(d.get("ts"))
        if start_epoch is not None and not _window_overlaps(ts, ts, start_epoch, end_epoch, pre_pad=60.0, post_pad=300.0):
            continue

        tids.append(tid)
        tin += int(d.get("tokensIn") or 0)
        tout += int(d.get("tokensOut") or 0)
        c_write += int(d.get("cacheWrites") or 0)
        c_read += int(d.get("cacheReads") or 0)
        cost_sum += float(d.get("totalCost") or 0.0)
    if not tids:
        return None
    return {
        "platform": "Roo-Cline",
        "status": "[实测-RooCline本地任务]",
        "raw_source": f"tasks:{','.join(tids)}",
        "uncached_input": tin,
        "cached_input": c_read,
        "cache_write": c_write,
        "output_incl_thinking": tout,
        "total_tokens": tin + c_read + c_write + tout,
        "native_bill": f"${cost_sum:.4f}" if cost_sum > 0 else "按模型官方单价核算",
        "cny_est": None,
    }


def probe_all_sources() -> None:
    print("=== Read-Only Local Telemetry Probe (Stage 2 Gate) ===")
    failures: List[str] = []

    # 1. AGY transcript sample check
    agy_count = 0
    if not (AGY_BRAIN_DIR.exists() and AGY_BRAIN_DIR.is_dir()):
        failures.append(f"AGY_BRAIN_DIR missing or not a directory: {AGY_BRAIN_DIR}")
    else:
        try:
            _ = list(AGY_BRAIN_DIR.iterdir())
            agy_count = len(list(AGY_BRAIN_DIR.glob("*/.system_generated/logs/transcript.jsonl")))
        except Exception as exc:
            failures.append(f"AGY_BRAIN_DIR unreadable ({AGY_BRAIN_DIR}): {exc}")
    print(f"[1/5] AGY transcripts found: {agy_count} (dir={AGY_BRAIN_DIR})")

    # 2. Codex sessions check
    codex_count = 0
    if not (CODEX_SESSIONS_DIR.exists() and CODEX_SESSIONS_DIR.is_dir()):
        failures.append(f"CODEX_SESSIONS_DIR missing or not a directory: {CODEX_SESSIONS_DIR}")
    else:
        try:
            _ = list(CODEX_SESSIONS_DIR.iterdir())
            codex_count = len(list(CODEX_SESSIONS_DIR.rglob("rollout-*.jsonl")))
        except Exception as exc:
            failures.append(f"CODEX_SESSIONS_DIR unreadable ({CODEX_SESSIONS_DIR}): {exc}")
    print(f"[2/5] Codex rollout JSONLs found: {codex_count} (dir={CODEX_SESSIONS_DIR})")

    # 3. OpenCode sqlite check
    oc_count = 0
    if not (OPENCODE_DB_PATH.exists() and OPENCODE_DB_PATH.is_file()):
        failures.append(f"OPENCODE_DB_PATH missing or not a file: {OPENCODE_DB_PATH}")
    else:
        try:
            conn = sqlite3.connect(str(OPENCODE_DB_PATH))
            oc_count = conn.execute("SELECT COUNT(*) FROM session_v2").fetchone()[0]
            conn.close()
        except Exception as exc:
            failures.append(f"OPENCODE_DB_PATH query failed ({OPENCODE_DB_PATH}): {exc}")
    print(f"[3/5] OpenCode session_v2 rows: {oc_count} (db={OPENCODE_DB_PATH.exists()})")

    # 4. DSH usage json check
    dsh_sample = None
    if not (DSH_USAGE_PATH.exists() and DSH_USAGE_PATH.is_file()):
        failures.append(f"DSH_USAGE_PATH missing or not a file: {DSH_USAGE_PATH}")
    else:
        try:
            raw_dsh = json.loads(DSH_USAGE_PATH.read_text(encoding="utf-8"))
            if not isinstance(raw_dsh, dict) or not isinstance(raw_dsh.get("events"), list):
                failures.append(f"DSH_USAGE_PATH malformed (missing events list): {DSH_USAGE_PATH}")
            else:
                dsh_sample = parse_dsh_window(start_epoch=None)
        except Exception as exc:
            failures.append(f"DSH_USAGE_PATH unreadable ({DSH_USAGE_PATH}): {exc}")
    print(f"[4/5] DSH usage json: exists={DSH_USAGE_PATH.exists()} sample={dsh_sample['native_bill'] if dsh_sample else 'none'}")

    # 5. Roo-Cline tasks check
    rc_count = 0
    if not (ROO_TASKS_DIR.exists() and ROO_TASKS_DIR.is_dir()):
        failures.append(f"ROO_TASKS_DIR missing or not a directory: {ROO_TASKS_DIR}")
    else:
        try:
            _ = list(ROO_TASKS_DIR.iterdir())
            rc_count = len(list(ROO_TASKS_DIR.glob("*/history_item.json")))
        except Exception as exc:
            failures.append(f"ROO_TASKS_DIR unreadable ({ROO_TASKS_DIR}): {exc}")
    print(f"[5/5] Roo-Cline task records found: {rc_count} (dir={ROO_TASKS_DIR})")

    if failures:
        for msg in failures:
            print(f"[PROBE FAIL] {msg}")
        sys.exit(1)
    print("[PROBE OK] All 5 native telemetry parsers ready.")


def resolve_room_record(room: Path) -> Tuple[Dict[str, Any], bool]:
    binding = _load_room_binding(room)
    start_epoch = binding.get("start_epoch")
    end_epoch = binding.get("end_epoch")
    has_binding = (
        (room / ".exam_start_ts").exists()
        or (room / "agy_session_binding.json").exists()
        or (room / "token_session_binding.json").exists()
    )

    manual_path = room / "manual_billing.json"
    manual = json.loads(manual_path.read_text(encoding="utf-8")) if manual_path.exists() else {}

    rec = (
        parse_agy_room(room)
        or parse_codex_room(room, binding=binding)
        or parse_opencode_room(room, binding=binding)
        or parse_roocline_room(room, binding=binding)
    )
    if rec is None and "dsh" in room.name.lower() and start_epoch is not None:
        rec = parse_dsh_window(
            start_epoch=start_epoch,
            end_epoch=end_epoch,
            model_filter=_infer_dsh_model_filter(room, binding),
        )

    if manual:
        base = rec or {
            "platform": manual.get("platform", "Manual"),
            "status": manual.get("status", "[实测-账单/截图]"),
            "raw_source": manual.get("screenshot", "manual_billing.json"),
            "uncached_input": manual.get("uncached_input"),
            "cached_input": manual.get("cached_input"),
            "cache_write": manual.get("cache_write"),
            "output_incl_thinking": manual.get("output_incl_thinking"),
            "total_tokens": manual.get("total_tokens"),
            "native_bill": manual.get("native_bill", "见截图"),
            "cny_est": manual.get("cny_est"),
        }
        for k in ("status", "native_bill", "cny_est", "raw_source", "cache_write"):
            if k in manual and manual[k] is not None:
                base[k] = manual[k]
        rec = base

    if rec is None:
        if not has_binding and not manual:
            rec = {
                "platform": "Pending",
                "status": "[待开考-未绑定会话]",
                "raw_source": "尚未开考/未生成会话绑定",
                "uncached_input": None,
                "cached_input": None,
                "cache_write": None,
                "output_incl_thinking": None,
                "total_tokens": None,
                "native_bill": "待开考",
                "cny_est": None,
            }
        else:
            rec = {
                "platform": "Unknown",
                "status": "[缺失-待补采]",
                "raw_source": "无匹配本地日志或截图",
                "uncached_input": None,
                "cached_input": None,
                "cache_write": None,
                "output_incl_thinking": None,
                "total_tokens": None,
                "native_bill": "待补采",
                "cny_est": None,
            }
    return rec, has_binding


def verify_room_command(room_dir: Path) -> None:
    if not (room_dir.exists() and room_dir.is_dir()):
        print(f"[VERIFY FAIL] Room directory missing: {room_dir}")
        sys.exit(1)
    rec, has_binding = resolve_room_record(room_dir)
    if not has_binding:
        print(
            f"[VERIFY FAIL] Room '{room_dir.name}' has no session binding "
            "(.exam_start_ts / agy_session_binding.json / token_session_binding.json)."
        )
        sys.exit(1)
    tot = rec.get("total_tokens") or 0
    if not (str(rec.get("status", "")).startswith("[实测") and int(tot) > 0):
        print(
            f"[VERIFY FAIL] Room '{room_dir.name}' unresolved or zero tokens: "
            f"status={rec.get('status')} total_tokens={tot} source={rec.get('raw_source')}"
        )
        sys.exit(1)
    print(
        f"[VERIFY OK] {room_dir.name} | platform={rec['platform']} | "
        f"total_tokens={tot:,} | status={rec['status']}"
    )


def collect_ledger(rooms_dir: Path, out_path: Path, fx_rate: float = 7.25) -> None:
    rooms = sorted(p for p in rooms_dir.iterdir() if p.is_dir()) if rooms_dir.exists() else []
    rows = []
    measured_count = 0
    pre_exam_count = 0

    for room in rooms:
        rec, _has_binding = resolve_room_record(room)
        if rec["status"].startswith("[待开考"):
            pre_exam_count += 1
        elif rec["status"].startswith("[实测"):
            measured_count += 1
        rows.append((room.name, rec))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    total_seats = len(rows)
    active_seats = total_seats - pre_exam_count
    cov_str = (
        f"{measured_count} / {active_seats} ({100.0 * measured_count / active_seats:.1f}%)"
        if active_seats > 0
        else f"0 / 0 (N/A · 全部 {pre_exam_count} 席待开考)"
    )
    lines = [
        "# 下半场 `FULL` 全图明牌赛 · 原生多单位 Token 与实付费用台账 (`token_ledger_part2.md`)\n",
        f"> **锁定汇率**：`$1 USD = ¥{fx_rate:.2f} CNY` | **已开考实测覆盖率**：`{cov_str}` | **总席位**：`{total_seats}` (待开考 `{pre_exam_count}` 席不计入分母)\n",
        "| 考场目录 | 平台 | 实测状态 | 原始日志/凭证路径 | 非缓存输入 | 缓存读取 | 缓存写入 | 输出(含思考) | 总 Token | 原生账单/额度 |",
        "| :--- | :--- | :---: | :--- | ---: | ---: | ---: | ---: | ---: | :--- |",
    ]
    for rname, rec in rows:
        fmt_int = lambda v: f"{v:,}" if isinstance(v, int) else "—"
        lines.append(
            f"| `{rname}` | {rec['platform']} | {rec['status']} | `{rec['raw_source']}` | "
            f"{fmt_int(rec['uncached_input'])} | {fmt_int(rec['cached_input'])} | "
            f"{fmt_int(rec.get('cache_write'))} | {fmt_int(rec['output_incl_thinking'])} | "
            f"{fmt_int(rec['total_tokens'])} | {rec['native_bill']} |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"[LEDGER] Written {total_seats} rows (measured {cov_str}) -> {out_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Half-2 Native Multi-Platform Token Harvester")
    parser.add_argument("--probe", action="store_true", help="Read-only probe of all 5 local log stores")
    parser.add_argument("--verify-room", type=str, default=None, help="Verify binding and non-zero measured tokens for a single room")
    parser.add_argument("--rooms-dir", type=str, default=str(DEFAULT_ROOMS_DIR))
    parser.add_argument("--out", type=str, default=str(DEFAULT_LEDGER_OUT))
    parser.add_argument("--fx", type=float, default=7.25)
    args = parser.parse_args()

    if args.probe:
        probe_all_sources()
        return
    if args.verify_room:
        verify_room_command(Path(args.verify_room))
        return
    collect_ledger(Path(args.rooms_dir), Path(args.out), fx_rate=args.fx)


if __name__ == "__main__":
    main()
