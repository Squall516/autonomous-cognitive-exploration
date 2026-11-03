# 实际验证记录

日期：2026-11-03（Asia/Shanghai）。环境：macOS ARM64、Python 3.9.6、Streamlit 1.50.0。

- 已安装 requirements.txt，完整依赖记录见 requirements-lock.txt。
- 15 项测试全部通过，0 失败，0 跳过。包含真实 Streamlit AppTest 的导入、探索、循环、对照和添加记忆流程。
- 实际运行 demo.py：完成 3 轮探索和 1 次对照；输出见 data/example-run.json。
- 实际启动本地 Streamlit 服务，健康检查 /_stcore/health 返回 ok；浏览器确认面板可加载并检查布局。
- 追加畸形 Ollama 响应处理，验证其明确报错；增加 B 组失败不保存半次对照的测试。
- 未下载或运行真实 Ollama 模型。模型接口测试为 mock，不能视作真实推理验证。
- 本次测试中的 ScriptRunContext 警告来自 AppTest 的无界面运行环境，不影响测试结果。

测试命令：`python -m unittest discover -s tests -v`

```text
test_ab_isolation_and_no_state_mutation (test_core.CoreTests) ... ok
test_ab_second_group_failure_does_not_save_partial_result (test_core.CoreTests) ... ok
test_concurrent_state_change_rejects_stale_output (test_core.CoreTests) ... ok
test_demo_seed_is_idempotent (test_core.CoreTests) ... ok
test_empty_history_ab_is_identical (test_core.CoreTests) ... ok
test_exploration_chain_and_citations (test_core.CoreTests) ... ok
test_failure_has_no_partial_commit (test_core.CoreTests) ... ok
test_invalid_model_citation_rejected (test_core.CoreTests) ... ok
test_malformed_ollama_envelope_is_reported (test_core.CoreTests) ... ok
test_ollama_request_contract_without_real_model (test_core.CoreTests) ... ok
test_recent_window_and_validation (test_core.CoreTests) ... ok
test_restart_restores_all_data (test_core.CoreTests) ... ok
test_simulation_reproducibility (test_core.CoreTests) ... ok
test_transaction_rolls_back_on_database_failure (test_core.CoreTests) ... ok
test_complete_demo_flow (test_ui.DashboardTests) ... 2026-11-03 10:57:17.076 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
ok

----------------------------------------------------------------------
Ran 15 tests in 0.417s

OK

```
