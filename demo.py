"""Create a fresh deterministic demo without needing Streamlit or a model."""
import argparse
import json
from pathlib import Path
from ace.store import Store
from ace.engine import Simulation, explore, compare


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='data/repro-demo.sqlite3')
    parser.add_argument('--export', default='data/repro-demo.json')
    args = parser.parse_args()
    if Path(args.db).exists():
        parser.error('目标数据库已存在；请指定新的 --db 路径以保护已有实验。')
    store = Store(args.db)
    fixture = Path(__file__).parent / 'data/demo.json'
    store.seed(json.loads(fixture.read_text()))
    backend = Simulation()
    for _ in range(3):
        explore(store, backend)
    compare(store, backend, '下一步应如何验证传感器 S-17 的异常读数？')
    target = Path(args.export)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(store.export(), ensure_ascii=False, indent=2))
    print('完成：3 轮探索、1 次对照；数据库 %s；记录 %s' % (args.db, target))


if __name__ == '__main__':
    main()
