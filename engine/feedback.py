import json
import threading
from datetime import datetime, timezone

class FeedbackRecorder:
    lock = threading.Lock()

    def __init__(self, path):
        self.path = path

    def record(self, category, text, interpretation, previous=None):
        event = {'timestamp': datetime.now(timezone.utc).isoformat(), 'category': category, 'message': text, 'interpretation': interpretation, 'previous': previous, 'status': 'pending_review'}
        with self.lock:
            # Rotação limitada: arquivo atual + uma geração anterior de até ~1 MB.
            if self.path.exists() and self.path.stat().st_size > 1_000_000:
                self.path.replace(self.path.with_suffix('.previous.jsonl'))
            with self.path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + '\n')
