import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def initial_state():
    return {"focus": "历史信息如何影响下一步探索？", "judgments": [],
            "unresolved": ["哪些历史信息值得再次验证？"], "recent_changes": []}


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class ConflictError(RuntimeError):
    pass


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
                    kind TEXT NOT NULL, content TEXT NOT NULL, source TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS state (
                    id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL,
                    payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS exploration (
                    id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS state_history (
                    id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
                    exploration_id INTEGER NOT NULL, before_state TEXT NOT NULL,
                    after_state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS comparison (
                    id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            ''')
            db.execute('INSERT OR IGNORE INTO state VALUES (1,0,?)', (dump(initial_state()),))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def snapshot(self):
        with self.connect() as db:
            db.execute('BEGIN')
            row = db.execute('SELECT * FROM state WHERE id=1').fetchone()
            memories = [dict(r) for r in db.execute('SELECT * FROM memory ORDER BY id')]
            return {"version": row['version'], "state": json.loads(row['payload']), "memories": memories}

    def add_memory(self, kind, content, source='user'):
        if kind not in ('experience', 'judgment', 'result') or not content.strip():
            raise ValueError('记忆类型无效或内容为空。')
        if len(content) > 8000:
            raise ValueError('单条记忆最多 8000 字符。')
        with self.connect() as db:
            db.execute('INSERT INTO memory(created_at,kind,content,source) VALUES(?,?,?,?)',
                       (now(), kind, content.strip(), source))
            db.execute('UPDATE state SET version=version+1 WHERE id=1')

    def seed(self, fixture):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM metadata WHERE key='demo_v1'").fetchone():
                return False
            for memory in fixture:
                db.execute('INSERT INTO memory(created_at,kind,content,source) VALUES(?,?,?,?)',
                           (memory['created_at'], memory['kind'], memory['content'], 'demo-fixture-v1'))
            db.execute("INSERT INTO metadata VALUES('demo_v1','loaded')")
            db.execute('UPDATE state SET version=version+1 WHERE id=1')
            return True

    def commit_exploration(self, snapshot, record, new_state):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            version = db.execute('SELECT version FROM state WHERE id=1').fetchone()[0]
            if version != snapshot['version']:
                raise ConflictError('生成期间记忆或状态已变化；本次未保存，请重新探索。')
            timestamp = now()
            cursor = db.execute('INSERT INTO exploration(created_at,payload) VALUES(?,?)',
                                (timestamp, dump(record)))
            run_id = cursor.lastrowid
            db.execute('INSERT INTO state_history(created_at,exploration_id,before_state,after_state) VALUES(?,?,?,?)',
                       (timestamp, run_id, dump(snapshot['state']), dump(new_state)))
            for kind, content in [('result', record['output']['result']),
                                  ('judgment', record['output']['judgment'])]:
                db.execute('INSERT INTO memory(created_at,kind,content,source) VALUES(?,?,?,?)',
                           (timestamp, kind, content, 'exploration:%s' % run_id))
            db.execute('UPDATE state SET version=version+1,payload=? WHERE id=1', (dump(new_state),))
            return run_id

    def save_comparison(self, record):
        with self.connect() as db:
            db.execute('INSERT INTO comparison(created_at,payload) VALUES(?,?)', (now(), dump(record)))

    def records(self, table):
        if table not in ('exploration', 'comparison', 'state_history'):
            raise ValueError('不支持的数据表。')
        with self.connect() as db:
            rows = [dict(r) for r in db.execute('SELECT * FROM ' + table + ' ORDER BY id DESC')]
        for row in rows:
            for key in ('payload', 'before_state', 'after_state'):
                if key in row:
                    row[key] = json.loads(row[key])
        return rows

    def export(self):
        return {"snapshot": self.snapshot(), "explorations": self.records('exploration'),
                "comparisons": self.records('comparison'), "history": self.records('state_history')}
