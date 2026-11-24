# -*- coding: utf-8 -*-
"""
Half-2 40-Minute Exam Watcher & Auto-Snapshotter (`exam_watcher.py`)
Watches `exam_rooms/P2_*/submission.py`, archives every distinct SHA-256 edit into
`history/vNN_MMmSSs_<sha8>.py` + `history/timeline.jsonl`, and writes `CUTOFF_40m00s_<sha8>.py`
when each room reaches the 40:00 (2400s) exam limit.

Prevents lost intermediate pivots, accidental overwrites, or overtime confusion.
"""

from __future__ import annotations
import argparse
import ast
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PART2_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ROOMS_DIR = PART2_DIR / "exam_rooms"
CUTOFF_SECONDS = 40 * 60


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_ast(source_text: str) -> Tuple[bool, str]:
    if not source_text or not source_text.strip():
        return False, "Empty submission file"
    try:
        tree = ast.parse(source_text, filename="submission.py")
        compile(source_text, "submission.py", "exec")
    except SyntaxError as exc:
        return False, f"SyntaxError line {exc.lineno}: {exc.msg}"
    except Exception as exc:
        return False, str(exc)

    top_funcs = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    missing = [fn for fn in ("build_dungeon", "decide_action") if fn not in top_funcs]
    if missing:
        return False, f"Missing required top-level function(s): {', '.join(missing)}"
    return True, ""


def _format_mmss(seconds: float) -> str:
    sec = max(0, int(round(seconds)))
    return f"{sec // 60:02d}m{sec % 60:02d}s"


class RoomTracker:
    def __init__(self, room_dir: Path, cutoff_seconds: float = CUTOFF_SECONDS):
        self.room_dir = room_dir
        self.sub_path = room_dir / "submission.py"
        self.history_dir = room_dir / "history"
        self.timeline_path = self.history_dir / "timeline.jsonl"
        self.start_ts_path = room_dir / ".exam_start_ts"
        self.cutoff_seconds = cutoff_seconds

        self.version_idx = 0
        self.last_sha = ""
        self.baseline_sha = ""
        self.last_valid_snapshot: Optional[Path] = None
        self.last_valid_sha: str = ""
        self.cutoff_written = False
        self._load_existing_state()

    def _load_existing_state(self) -> None:
        base_file = self.room_dir / ".baseline_sha256"
        if base_file.exists():
            self.baseline_sha = base_file.read_text(encoding="utf-8").strip()

        if self.history_dir.exists():
            for p in sorted(self.history_dir.glob("CUTOFF_*.py")):
                self.cutoff_written = True
                break
        if self.timeline_path.exists():
            for line in self.timeline_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    self.version_idx = max(self.version_idx, int(rec.get("version_num", 0)))
                    self.last_sha = rec.get("sha256", self.last_sha)
                    if (
                        rec.get("ast_valid")
                        and rec.get("event") in ("BASELINE", "EDIT")
                        and rec.get("snapshot_file")
                    ):
                        cand = self.history_dir / rec["snapshot_file"]
                        if cand.exists():
                            self.last_valid_snapshot = cand
                            self.last_valid_sha = rec.get("sha256", "")
                except Exception:
                    pass

    def get_start_ts(self) -> Optional[float]:
        if self.start_ts_path.exists():
            try:
                return float(self.start_ts_path.read_text(encoding="utf-8").strip())
            except Exception:
                return None
        return None

    def set_start_ts(self, ts: Optional[float] = None, force: bool = False) -> float:
        """Write-once start clock unless `force=True` is explicitly requested."""
        existing = self.get_start_ts()
        if existing is not None and not force:
            return existing
        val = time.time() if ts is None else float(ts)
        self.start_ts_path.write_text(f"{val:.3f}\n", encoding="utf-8")
        self._append_timeline({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(val)),
            "epoch": round(val, 3),
            "elapsed_s": 0.0,
            "event": "CLOCK_START",
            "forced": bool(force),
        })
        return val

    def start_exam(self, now: Optional[float] = None, force: bool = False) -> Tuple[float, List[str]]:
        cur_now = time.time() if now is None else float(now)
        start_ts = self.set_start_ts(ts=cur_now, force=force)
        logs = self.poll_once(now=cur_now)
        return start_ts, logs

    def _append_timeline(self, record: Dict[str, Any]) -> None:
        self.history_dir.mkdir(parents=True, exist_ok=True)
        with open(self.timeline_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def poll_once(self, now: Optional[float] = None, auto_start_on_edit: bool = True) -> List[str]:
        logs: List[str] = []
        cur_now = time.time() if now is None else float(now)
        start_ts = self.get_start_ts()

        # 1. Track any submission edits if file exists
        if self.sub_path.exists():
            try:
                raw = self.sub_path.read_bytes()
            except Exception:
                raw = None

            if raw is not None:
                sha = _sha256_bytes(raw)
                if sha != self.last_sha:
                    text = raw.decode("utf-8-sig", errors="replace")
                    ast_ok, syn_err = _check_ast(text)
                    if not self.baseline_sha and self.version_idx == 0 and not self.timeline_path.exists():
                        self.baseline_sha = sha
                        (self.room_dir / ".baseline_sha256").write_text(sha + "\n", encoding="utf-8")
                        tag = "v00_baseline"
                        event_type = "BASELINE"
                    else:
                        if start_ts is None and auto_start_on_edit and sha != self.baseline_sha:
                            start_ts = self.set_start_ts(cur_now)
                            logs.append(f"[START-AUTO] {self.room_dir.name} clock started on first edit")
                        self.version_idx += 1
                        elapsed = (cur_now - start_ts) if start_ts is not None else 0.0
                        tag = f"v{self.version_idx:02d}_{_format_mmss(elapsed)}"
                        event_type = "OVERTIME_EDIT" if (start_ts is not None and elapsed > self.cutoff_seconds) else "EDIT"

                    snap_name = f"{tag}_{sha[:8]}.py"
                    self.history_dir.mkdir(parents=True, exist_ok=True)
                    snap_path = self.history_dir / snap_name
                    snap_path.write_bytes(raw)

                    rec = {
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(cur_now)),
                        "epoch": round(cur_now, 3),
                        "elapsed_s": round((cur_now - start_ts), 2) if start_ts is not None else 0.0,
                        "event": event_type,
                        "version_num": self.version_idx,
                        "snapshot_file": snap_name,
                        "sha256": sha,
                        "bytes": len(raw),
                        "lines": len(text.splitlines()),
                        "ast_valid": ast_ok,
                        "syntax_error": syn_err,
                    }
                    self._append_timeline(rec)
                    self.last_sha = sha
                    if ast_ok and event_type != "OVERTIME_EDIT":
                        self.last_valid_snapshot = snap_path
                        self.last_valid_sha = sha
                    logs.append(
                        f"[{event_type}] {self.room_dir.name} -> {snap_name} "
                        f"(lines={rec['lines']}, ast={ast_ok})"
                    )

        # 2. Unconditionally enforce 40:00 cutoff EVEN if submission.py was temporarily deleted/missing
        start_ts = self.get_start_ts()
        if start_ts is not None and not self.cutoff_written:
            elapsed = cur_now - start_ts
            if elapsed >= self.cutoff_seconds:
                self.cutoff_written = True
                src_path = None
                if self.last_valid_snapshot and self.last_valid_snapshot.exists():
                    src_path = self.last_valid_snapshot
                elif self.sub_path.exists():
                    sub_text = self.sub_path.read_text(encoding="utf-8-sig", errors="replace")
                    sub_ok, _ = _check_ast(sub_text)
                    if sub_ok:
                        src_path = self.sub_path

                if src_path is not None:
                    src_bytes = src_path.read_bytes()
                    c_sha = _sha256_bytes(src_bytes)
                    ast_ok, syn_err = _check_ast(src_bytes.decode("utf-8-sig", errors="replace"))
                    cutoff_name = f"CUTOFF_40m00s_{c_sha[:8]}.py"
                    self.history_dir.mkdir(parents=True, exist_ok=True)
                    (self.history_dir / cutoff_name).write_bytes(src_bytes)
                    self._append_timeline({
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(cur_now)),
                        "epoch": round(cur_now, 3),
                        "elapsed_s": round(elapsed, 2),
                        "event": "CUTOFF_40M",
                        "version_num": self.version_idx,
                        "snapshot_file": cutoff_name,
                        "source_snapshot": src_path.name,
                        "sha256": c_sha,
                        "bytes": len(src_bytes),
                        "lines": len(src_bytes.decode("utf-8-sig", errors="replace").splitlines()),
                        "ast_valid": ast_ok,
                        "syntax_error": syn_err,
                    })
                    logs.append(f"[CUTOFF 40:00] {self.room_dir.name} frozen -> {cutoff_name} (from {src_path.name})")
                else:
                    self._append_timeline({
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(cur_now)),
                        "epoch": round(cur_now, 3),
                        "elapsed_s": round(elapsed, 2),
                        "event": "CUTOFF_40M_MISSING",
                        "version_num": self.version_idx,
                    })
                    logs.append(f"[CUTOFF 40:00 MISSING] {self.room_dir.name} had no valid snapshot or submission.py")

        return logs


def discover_rooms(rooms_dir: Path) -> List[Path]:
    if not rooms_dir.exists():
        return []
    return sorted(
        p for p in rooms_dir.iterdir()
        if p.is_dir() and ((p / "submission.py").exists() or (p / ".exam_start_ts").exists() or (p / "history").exists())
    )


def run_self_test() -> None:
    def _bot(tag: str) -> str:
        return (
            f"def build_dungeon():\n    return {{'v': {tag!r}}}\n\n"
            "def decide_action(state, memory):\n    return 'WAIT'\n"
        )

    tmp_root = Path(tempfile.mkdtemp(prefix="exam_watcher_test_"))
    try:
        # Case A: Broken syntax at cutoff falls back to v01 + write-once clock immutability
        room = tmp_root / "P2_99_test_codex"
        room.mkdir(parents=True)
        sub = room / "submission.py"
        t0 = 1_700_000_000.0

        sub.write_text(_bot("base"), encoding="utf-8")
        tracker = RoomTracker(room, cutoff_seconds=10.0)
        logs0 = tracker.poll_once(now=t0)
        assert any("BASELINE" in l for l in logs0), logs0

        # Start clock explicitly and test write-once immutability
        c1 = tracker.set_start_ts(t0 + 1.0)
        c2 = tracker.set_start_ts(t0 + 500.0)
        assert c1 == c2 == t0 + 1.0, "Start clock must be write-once unless force=True"

        sub.write_text(_bot("1"), encoding="utf-8")
        logs1 = tracker.poll_once(now=t0 + 3.0)
        assert any("v01_" in l for l in logs1), logs1

        sub.write_text("def build_dungeon(:\n", encoding="utf-8")
        logs2 = tracker.poll_once(now=t0 + 5.0)
        assert any("ast=False" in l for l in logs2), logs2

        logs3 = tracker.poll_once(now=t0 + 12.5)
        assert any("CUTOFF 40:00" in l for l in logs3), logs3
        cutoffs = list((room / "history").glob("CUTOFF_40m00s_*.py"))
        assert len(cutoffs) == 1
        assert "'v': '1'" in cutoffs[0].read_text(encoding="utf-8")

        # Case B: Missing/deleted submission.py at cutoff STILL generates CUTOFF from v01!
        room_del = tmp_root / "P2_98_deleted_test"
        room_del.mkdir(parents=True)
        sub_del = room_del / "submission.py"
        sub_del.write_text(_bot("base"), encoding="utf-8")
        tr_del = RoomTracker(room_del, cutoff_seconds=10.0)
        tr_del.poll_once(now=t0)
        tr_del.set_start_ts(t0)
        sub_del.write_text(_bot("saved_ok"), encoding="utf-8")
        tr_del.poll_once(now=t0 + 2.0)
        sub_del.unlink()  # Delete submission.py before 10s deadline!
        logs_del = tr_del.poll_once(now=t0 + 11.0)
        assert any("CUTOFF 40:00" in l for l in logs_del), logs_del
        cut_del = list((room_del / "history").glob("CUTOFF_40m00s_*.py"))
        assert len(cut_del) == 1
        assert "saved_ok" in cut_del[0].read_text(encoding="utf-8")

        # Case C: Zero-byte truncation, top-level return, and missing entry-point fallback -> restores v01
        room_edge = tmp_root / "P2_97_edge_syntax_test"
        room_edge.mkdir(parents=True)
        sub_edge = room_edge / "submission.py"
        sub_edge.write_text(_bot("base_edge"), encoding="utf-8")
        tr_edge = RoomTracker(room_edge, cutoff_seconds=10.0)
        tr_edge.poll_once(now=t0)
        tr_edge.set_start_ts(t0)
        sub_edge.write_text(_bot("good_v01"), encoding="utf-8")
        logs_e1 = tr_edge.poll_once(now=t0 + 2.0)
        assert any("v01_" in l and "ast=True" in l for l in logs_e1), logs_e1

        # 1) 0-byte file
        sub_edge.write_text("", encoding="utf-8")
        logs_zero = tr_edge.poll_once(now=t0 + 4.0)
        assert any("ast=False" in l for l in logs_zero), logs_zero
        # 2) Top-level return outside function (passes ast.parse, fails compile)
        sub_edge.write_text("def build_dungeon(): pass\ndef decide_action(s, m): pass\nreturn 1\n", encoding="utf-8")
        logs_ret = tr_edge.poll_once(now=t0 + 6.0)
        assert any("ast=False" in l for l in logs_ret), logs_ret
        # 3) Missing required entry point `decide_action`
        sub_edge.write_text("def build_dungeon():\n    return {}\n", encoding="utf-8")
        logs_miss = tr_edge.poll_once(now=t0 + 8.0)
        assert any("ast=False" in l for l in logs_miss), logs_miss

        logs_e_cut = tr_edge.poll_once(now=t0 + 12.0)
        assert any("CUTOFF 40:00" in l for l in logs_e_cut), logs_e_cut
        cut_edge = list((room_edge / "history").glob("CUTOFF_40m00s_*.py"))
        assert len(cut_edge) == 1
        assert "good_v01" in cut_edge[0].read_text(encoding="utf-8")

        # 4) Verify invalid baseline + zero-byte at cutoff produces CUTOFF_40M_MISSING without sealing empty file
        room_empty = tmp_root / "P2_96_only_empty_test"
        room_empty.mkdir(parents=True)
        (room_empty / "submission.py").write_text("", encoding="utf-8")
        tr_empty = RoomTracker(room_empty, cutoff_seconds=10.0)
        tr_empty.poll_once(now=t0)
        tr_empty.set_start_ts(t0)
        logs_emp = tr_empty.poll_once(now=t0 + 11.0)
        assert any("CUTOFF 40:00 MISSING" in l for l in logs_emp), logs_emp
        assert not list((room_empty / "history").glob("CUTOFF_*.py"))

        # Case D: Repeated `--start` after 2500s overtime edit must preserve t0 and NOT seal overtime edit
        room_rep = tmp_root / "P2_95_repeat_start_test"
        room_rep.mkdir(parents=True)
        sub_rep = room_rep / "submission.py"
        sub_rep.write_text(_bot("base_rep"), encoding="utf-8")
        tr_rep1 = RoomTracker(room_rep, cutoff_seconds=2400.0)
        tr_rep1.poll_once(now=t0)
        tr_rep1.start_exam(now=t0, force=False)
        sub_rep.write_text(_bot("v01_ontime"), encoding="utf-8")
        tr_rep1.poll_once(now=t0 + 100.0)

        # Simulate 2500s overtime write followed by a fresh process running `--start` without `--force-restart-clock`
        sub_rep.write_text(_bot("v2_overtime"), encoding="utf-8")
        tr_rep2 = RoomTracker(room_rep, cutoff_seconds=2400.0)
        ts_rep, logs_rep = tr_rep2.start_exam(now=t0 + 2500.0, force=False)
        assert ts_rep == t0, f"Repeated start_exam must preserve original clock {t0}, got {ts_rep}"
        assert any("OVERTIME_EDIT" in l for l in logs_rep), f"Expected OVERTIME_EDIT log, got {logs_rep}"
        assert not any("v01_00m00s" in l for l in logs_rep), f"Must not label overtime edit as 00m00s: {logs_rep}"
        cut_rep = list((room_rep / "history").glob("CUTOFF_40m00s_*.py"))
        assert len(cut_rep) == 1
        cut_text = cut_rep[0].read_text(encoding="utf-8")
        assert "v01_ontime" in cut_text and "v2_overtime" not in cut_text

        print(
            "[PASS] exam_watcher --self-test passed "
            "(write-once clock + broken/empty/return/missing-entry fallback + deleted-file cutoff + repeated --start overtime seal)"
        )
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Half-2 40-min Exam Watcher & Auto-Snapshotter")
    parser.add_argument("--rooms-dir", type=str, default=str(DEFAULT_ROOMS_DIR))
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--start", type=str, help="Start 40:00 clock for matching room substring or 'ALL'")
    parser.add_argument("--force-restart-clock", action="store_true", help="Explicitly overwrite an already-started .exam_start_ts clock")
    parser.add_argument("--watch", action="store_true", help="Continuous 0.5s polling daemon")
    parser.add_argument("--self-test", action="store_true", help="Run isolated snapshot & cutoff regression test")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return

    rooms_dir = Path(args.rooms_dir)
    rooms = discover_rooms(rooms_dir)
    trackers = {r: RoomTracker(r) for r in rooms}

    if args.start:
        cur_now = time.time()
        for r, tr in trackers.items():
            if args.start.upper() == "ALL" or args.start.lower() in r.name.lower():
                ts, logs = tr.start_exam(now=cur_now, force=args.force_restart_clock)
                for line in logs:
                    print(line)
                print(f"[CLOCK SET] {r.name} -> start_ts={ts:.3f} (now={cur_now:.3f}, 40m00s deadline)")
        if not args.watch:
            return

    if not args.watch:
        for tr in trackers.values():
            for line in tr.poll_once():
                print(line)
        return

    print(f"[WATCHING] {len(trackers)} exam rooms in {rooms_dir} (poll={args.interval}s, Ctrl+C to stop)")
    try:
        while True:
            for r in discover_rooms(rooms_dir):
                if r not in trackers:
                    trackers[r] = RoomTracker(r)
            now = time.time()
            for tr in trackers.values():
                for line in tr.poll_once(now=now):
                    print(line, flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[WATCHER STOPPED]")


if __name__ == "__main__":
    main()
