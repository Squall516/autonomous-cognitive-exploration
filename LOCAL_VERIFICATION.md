# Local checkout verification — 3 November 2026

This report applies to the existing GitHub MVP checkout, based on commit `60f7a10`. It does not claim features or results from a separately developed later prototype.

## Environment and automated tests

- Python 3.9.6 in the project's `.venv`.
- Streamlit 1.50.0 and python-dotenv 1.1.1 already installed.
- pytest was missing. Installed pytest 8.4.2 and declared it in `requirements-dev.txt`.
- Existing baseline: **15 passed**, 0 failed (9.73 s).
- Final regression run using `.venv/bin/pytest -q`: **17 passed**, 0 failed (0.53 s). No tests removed, skipped or weakened.
- Added checks for the Qwen3 default and switching both UI modes without triggering generation. The request-contract test also checks `think=false`.
- An initial new test selected the memory-type widget by position; corrected the test to locate the actual mode widget by its label. Application behavior was not weakened to satisfy that test.
- `python -m pip check`: no broken requirements.

## Real local-model execution

Ollama's `/api/tags` listed `qwen3:4b-instruct` (Q4_K_M), digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`.

The previous default `qwen2.5:3b` did not match the installed model. The engine and `.env.example` now default to Qwen3. The existing generate API is retained, with `think=false` added.

One autonomous exploration and one A/B pair were actually executed against Ollama using the synthetic demo fixture, not mocked responses:

- Exploration: 7.644 seconds.
- A/B pair: 13.544 seconds total.
- Same question: `下一步应如何验证传感器 S-17 的异常读数？`
- A had the seeded history plus the new exploration output/judgment; B had no history. Both used an identical clean initial state, temperature 0 and seed 42.
- A cited IDs 4 and 5 (generated result/judgment), while B cited none. This does not establish independent evidence: A relied on derived records rather than citing the original synthetic observations.
- Answers remained descriptive rather than a fully specified controlled experiment. No quality score, causal result, statistical significance or consciousness claim is made.

A new ignored database, `data/local-validation-20261103.sqlite3`, holds this run. A separate local JSON report preserves the full result. These runtime artifacts are not uploaded. Reopening the database produced an identical logical export. Existing tracked fixtures and the original validation document were not overwritten.

## Dashboard and safety checks

Streamlit launched from this checkout on port 8503 using the validation database; its health endpoint returned `ok`, and the browser displayed the saved state/record counts. Port 8503 avoids unrelated earlier sessions. Automated UI tests exercised import, single exploration, finite loop, A/B comparison, manual memory input and both mode selections.

The `.gitignore` now covers additional local configurations, database formats, keys, environments, model weights, private directories and unreviewed data exports. The tracked/staged file lists and common secret patterns were checked before committing. Existing synthetic fixture bytes remain unchanged. These checks reduce accidental exposure but do not replace author review of future data.

## Restart commands

From the repository root:

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
ACE_DB=data/local-validation-20261103.sqlite3 python -m streamlit run app.py --server.port 8503
```

To start directly in the real backend, prepend `ACE_MODE=ollama`. New default runs without ACE_DB use `data/ace.sqlite3` instead. Model-output correctness and research conclusions still require author review.
