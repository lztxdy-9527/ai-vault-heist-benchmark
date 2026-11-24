"""Fresh, deadline-enforced contestant processes with bounded JSON IPC."""
import json
import queue
import subprocess
import sys
import threading
from pathlib import Path


class SubmissionProcess:
    def __init__(self, path):
        self.process = None
        source = Path(path).read_text(encoding='utf-8-sig')
        if len(source) > 1_000_000:
            raise ValueError('Submission exceeds 1 MB')
        self.replies = queue.Queue()
        self.process = subprocess.Popen(
            [sys.executable, '-I', '-u', str(Path(__file__).with_name('submission_worker.py'))],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        threading.Thread(target=self._read, daemon=True).start()
        try:
            self._receive(5.0)  # Interpreter startup is outside contestant import time.
            self.call('load', 1.5, source=source)
        except BaseException:
            self.close()
            raise

    def _read(self):
        while self.process and self.process.stdout:
            line = self.process.stdout.readline(2_000_002)
            if not line:
                self.replies.put(None)
                return
            if len(line) > 2_000_000:
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
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait(timeout=5)
            for stream in (self.process.stdin, self.process.stdout):
                if stream:
                    stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
