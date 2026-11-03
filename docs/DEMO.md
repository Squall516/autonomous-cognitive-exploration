# Review demonstration

## 60-second outline

- 0–10 s: state the memory/state/exploration research question; explicitly disclaim consciousness claims.
- 10–25 s: load the supplied synthetic observations in a fresh database, show the timeline and self-state.
- 25–40 s: select simulation, trigger one round, inspect citations and before/after state. Explain that a bounded loop needs no new user question between rounds.
- 40–55 s: show the saved real Qwen3 JSON alongside the simulation example. Compare A/B contexts and outputs; point out missing original citations and vague plans.
- 55–60 s: state the next evaluation step and the lack of evidence for consciousness or general cognitive improvement.

`simulation-review.png` is an unaltered screenshot of the running Streamlit app, containing only `data/demo.json` and rule-generated outputs (3 rounds, 1 A/B pair). It is not a real-model screenshot. The real-model evidence is `qwen-review-20261103.json`.

## Reproduce a real exploration and A/B pair

After the README installation steps and starting Ollama with `qwen3:4b-instruct`, run from the repository root with the virtual environment activated:

```bash
python - <<'PYCODE'
import json, tempfile, time
from pathlib import Path
from ace.store import Store
from ace.engine import Ollama, explore, compare
with tempfile.TemporaryDirectory() as temp:
    store = Store(Path(temp) / 'run.sqlite3')
    store.seed(json.loads(Path('data/demo.json').read_text()))
    backend = Ollama()
    for name, action in [
        ('exploration', lambda: explore(store, backend)),
        ('comparison', lambda: compare(store, backend, '下一步应如何验证传感器 S-17 的异常读数？')),
    ]:
        start = time.perf_counter()
        record = action()
        print(json.dumps({'stage': name, 'elapsed_seconds': time.perf_counter()-start,
                          'record': record}, ensure_ascii=False, indent=2))
    assert store.export() == Store(store.path).export()
PYCODE
```

This prints actual results without overwriting an existing database or artifact. Save stdout to a new local filename if needed; inspect it before publication. Both groups use the same clean state, question and generation settings; only A sees memory, including the preceding exploration's derived records. Temperature 0/seed 42 do not promise bit-for-bit reproducibility across hardware or versions. Timing includes validation/persistence overhead. No semantic quality score was computed.
