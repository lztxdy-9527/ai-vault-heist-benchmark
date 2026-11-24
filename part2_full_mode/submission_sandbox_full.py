"""Fresh, deadline-enforced contestant processes with immutable in-memory SHA-256 locking & respawn (Half 2 v2.2)."""
import hashlib
import json
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional


class SubmissionProcess:
    def __init__(
        self,
        path,
        *,
        source_bytes: Optional[bytes] = None,
        expected_sha256: Optional[str] = None,
    ):
        self.path = Path(path)
        raw = source_bytes if source_bytes is not None else self.path.read_bytes()
        if len(raw) > 1_000_000:
            raise ValueError('Submission exceeds 1 MB')
        actual_sha = hashlib.sha256(raw).hexdigest()
        if expected_sha256 is not None and actual_sha != expected_sha256:
            raise ValueError(
                f'Submission hash mismatch for {self.path}: expected {expected_sha256}, got {actual_sha}'
            )
        self.locked_bytes: bytes = raw
        self.locked_sha256: str = actual_sha
        self.locked_source: str = raw.decode('utf-8-sig')
        self.process = None
        self.replies = queue.Queue()
        self.respawn()

    def respawn(self):
        self.close()
        # Never re-read from disk on respawn: always reload the verified locked in-memory source.
        self.replies = queue.Queue()
        self.process = subprocess.Popen(
            [sys.executable, '-I', '-u', str(Path(__file__).with_name('submission_worker_full.py'))],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        threading.Thread(target=self._read, daemon=True).start()
        try:
            self._receive(5.0)  # Interpreter startup outside contestant import budget.
            self.call('load', 1.5, source=self.locked_source)
        except BaseException:
            self.close()
            raise

    def _read(self):
        proc = self.process
        while proc and proc.stdout:
            try:
                line = proc.stdout.readline(2_000_002)
            except Exception:
                self.replies.put(None)
                return
            if not line or len(line) > 2_000_000:
                self.replies.put(None)
                return
            self.replies.put(line)

    def _receive(self, timeout):
        try:
            line = self.replies.get(timeout=timeout)
        except queue.Empty:
            self.close()
            raise TimeoutError('Contestant deadline exceeded') from None
        if line is None:
            raise RuntimeError('Contestant worker stopped')
        response = json.loads(line)
        if not response.get('ok'):
            raise RuntimeError(response.get('error', 'Worker error'))
        return response.get('result')

    def call(self, op, timeout, **payload):
        if not self.process or self.process.poll() is not None:
            raise RuntimeError('Contestant worker unavailable')
        self.process.stdin.write(json.dumps({'op': op, **payload}, ensure_ascii=True) + '\n')
        self.process.stdin.flush()
        return self._receive(timeout)

    def close(self):
        if self.process:
            try:
                if self.process.poll() is None:
                    self.process.kill()
                self.process.wait(timeout=5)
            except Exception:
                pass
            for stream in (self.process.stdin, self.process.stdout):
                if stream:
                    try:
                        stream.close()
                    except Exception:
                        pass
            self.process = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
