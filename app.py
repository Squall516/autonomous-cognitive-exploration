import json
import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from ace.store import Store, ConflictError
from ace.engine import explore, compare, get_backend

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
st.set_page_config(page_title='ACE · 自主认知探索', page_icon='◈', layout='wide')
st.markdown('''<style>
.block-container {max-width:1280px;padding-top:2.5rem;}
h1 {letter-spacing:-1.2px;} [data-testid="stMetric"] {background:white;border:1px solid #E3E9EF;border-radius:12px;padding:16px;}
[data-testid="stSidebar"] {border-right:1px solid #E3E9EF;}
</style>''', unsafe_allow_html=True)
db_path = Path(os.getenv('ACE_DB', 'data/ace.sqlite3'))
store = Store(db_path if db_path.is_absolute() else ROOT / db_path)

with st.sidebar:
    st.markdown('### ◈ ACE LAB')
    st.caption('Autonomous Cognitive Exploration')
    configured_mode = os.getenv('ACE_MODE', 'simulation')
    if configured_mode not in ('simulation', 'ollama'):
        st.error('ACE_MODE 无效，请使用 simulation 或 ollama。')
        st.stop()
    mode = st.selectbox('运行模式', ['simulation', 'ollama'],
                        index=['simulation', 'ollama'].index(configured_mode),
                        format_func=lambda x: '规则模拟 · 无需模型' if x == 'simulation' else '本地 Ollama · 真实模型')
    backend = get_backend(mode)
    st.caption('持久化：SQLite · 本地文件')
    if st.button('载入可复现演示记忆', use_container_width=True):
        loaded = store.seed(json.loads((ROOT / 'data/demo.json').read_text()))
        st.success('已载入 3 条合成记忆。' if loaded else '演示记忆已存在，不重复导入。')
    st.divider()
    st.caption('探索仅生成分析和验证计划，不执行外部动作。')
    st.caption('数据保留在本机；选择模型模式时，输入会发送至配置的 Ollama 地址。')

st.caption('RESEARCH PROTOTYPE / LOCAL-FIRST / v0.1')
st.title('跨时间的探索，留下可追踪的线索')
st.write('持续记忆 → 状态更新 → 下一步问题 → 可审计记录')
if mode == 'simulation':
    st.warning('当前为确定性规则模拟，不调用语言模型。行为差异由程序规则产生，仅用于验证系统流程。')
else:
    st.info('当前为本地模型模式。需要预先运行 Ollama 并安装模型；失败时不会自动伪装为模拟结果。')
st.caption('研究边界：本实验只能观察记忆输入对系统行为的影响，不能证明意识存在。')

left, right = st.columns([2, 1])
with left:
    if st.button('自主探索一次', type='primary', use_container_width=True):
        try:
            with st.spinner('正在读取记忆、选择问题并保存状态…'):
                explore(store, backend)
            st.success('探索完成，结果与状态已保存。')
        except (ValueError, RuntimeError, ConflictError) as exc:
            st.error(str(exc))
with right:
    count = st.number_input('有限探索轮数', min_value=1, max_value=5, value=3)
    if st.button('运行有限探索循环', use_container_width=True):
        progress = st.progress(0)
        for index in range(int(count)):
            try:
                explore(store, backend)
                progress.progress((index + 1) / int(count))
            except (ValueError, RuntimeError) as exc:
                st.error('循环停止；前 %s 轮已保存。%s' % (index, exc))
                break
        else:
            st.success('已完成 %s 轮。每轮均基于上一轮更新后的状态。' % count)

snapshot = store.snapshot()
runs = store.records('exploration')
comparisons = store.records('comparison')
cols = st.columns(4)
for col, label, value in zip(cols, ['持久记忆', '探索轮次', '未解决问题', '对照实验'],
                            [len(snapshot['memories']), len(runs), len(snapshot['state']['unresolved']), len(comparisons)]):
    col.metric(label, value)

state_tab, memory_tab, exploration_tab, history_tab, comparison_tab = st.tabs(
    ['自我状态', '记忆时间线', '自主探索记录', '状态变化历史', 'A/B 对照实验'])

with state_tab:
    state = snapshot['state']
    st.subheader('当前关注的问题')
    st.info(state['focus'])
    a, b = st.columns(2)
    with a:
        st.markdown('#### 已有判断 · 暂定')
        for item in state['judgments']:
            st.write('• ' + item)
        if not state['judgments']:
            st.caption('尚无判断；开始一次探索。')
    with b:
        st.markdown('#### 未解决的问题')
        for item in state['unresolved']:
            st.write('• ' + item)
    st.markdown('#### 最近的状态变化')
    for item in state['recent_changes']:
        st.write('• ' + item)
    st.caption('状态档案是可更新的数据结构；不代表主观体验。档案保留最近 20 条判断及问题，完整历史见变化记录。')

with memory_tab:
    with st.form('add_memory', clear_on_submit=True):
        st.markdown('#### 记录一条经历或判断')
        kind = st.selectbox('类型', ['experience', 'judgment', 'result'])
        content = st.text_area('内容', max_chars=8000, placeholder='记录观察条件、结果及不确定性…')
        submitted = st.form_submit_button('保存记忆')
    if submitted:
        try:
            store.add_memory(kind, content)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    if not snapshot['memories']:
        st.info('还没有记忆。从侧栏载入演示数据，或添加一条自己的观察。')
    for m in reversed(snapshot['memories']):
        with st.container(border=True):
            st.caption('#%s · %s · %s · %s' % (m['id'], m['kind'], m['created_at'], m['source']))
            st.write(m['content'])

with exploration_tab:
    if not runs:
        st.info('点击“自主探索一次”生成首条完整记录。')
    for row in runs:
        record = row['payload']
        output = record['output']
        with st.expander('#%s · %s' % (row['id'], output['question']), expanded=row == runs[0]):
            st.caption(row['created_at'] + ' · ' + record['backend'])
            st.markdown('**选择理由**')
            st.write(output['reason'])
            st.markdown('**引用的历史信息**')
            cited = [m for m in record['input']['context']['memories'] if m['id'] in output['references']]
            for m in cited:
                st.write('#%s：%s' % (m['id'], m['content']))
            if not cited:
                st.caption('未引用历史记忆。')
            st.markdown('**探索结果**')
            st.write(output['result'])
            st.markdown('**状态更新**')
            for change in record['state_update']['after']['recent_changes']:
                st.write(change)
            st.json(record, expanded=False)

with history_tab:
    history = store.records('state_history')
    if not history:
        st.info('每次成功探索都会保存一份状态前后快照。')
    for row in history:
        with st.expander('探索 #%s · %s' % (row['exploration_id'], row['created_at'])):
            a, b = st.columns(2)
            with a:
                st.caption('BEFORE')
                st.json(row['before_state'])
            with b:
                st.caption('AFTER')
                st.json(row['after_state'])

with comparison_tab:
    st.subheader('同一个问题，两种记忆条件')
    st.write('A：可访问最近 12 条历史记忆。B：历史为空。两组均使用同一个干净初始状态、同一后端和生成参数；结果不会进入探索记忆。')
    with st.form('comparison'):
        question = st.text_input('共同问题', value='下一步应如何验证传感器 S-17 的异常读数？', max_chars=2000)
        run_comparison = st.form_submit_button('运行 A/B 对照')
    if run_comparison:
        try:
            with st.spinner('运行隔离的 A/B 对照…'):
                compare(store, backend, question)
            st.rerun()
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
    for row in comparisons:
        record = row['payload']
        with st.expander('对照 #%s · %s' % (row['id'], record['question']), expanded=row == comparisons[0]):
            a, b = st.columns(2)
            for col, group, title in [(a, 'A', 'A / 有历史'), (b, 'B', 'B / 无历史')]:
                with col:
                    st.markdown('#### ' + title)
                    st.caption(record[group]['backend'])
                    st.write(record[group]['output']['result'])
                    st.write('选择理由：' + record[group]['output']['reason'])
                    st.write('下一步：' + record[group]['output']['next_question'])
                    st.caption('引用：' + str(record[group]['output']['references']))
            st.json(record['metrics'])
            st.caption(record['limitation'])
            st.json(record, expanded=False)

st.divider()
st.download_button('导出完整实验记录 · JSON', json.dumps(store.export(), ensure_ascii=False, indent=2),
                   file_name='ace-experiment.json', mime='application/json')
st.caption('ACE / 可追踪的行为连续性实验 · 所有时间戳使用 UTC')
