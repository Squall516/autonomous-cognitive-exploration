import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


@unittest.skipIf(AppTest is None, 'Streamlit 未安装；仅跳过界面测试')
class DashboardTests(unittest.TestCase):
    def test_mode_switch_does_not_trigger_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {'ACE_DB': str(Path(temp) / 'modes.sqlite3'), 'ACE_MODE': 'simulation'}):
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=20)
                next(item for item in app.selectbox if item.label == '运行模式').select('ollama').run(timeout=20)
                self.assertFalse(app.exception)
                self.assertTrue(any('本地模型模式' in item.value for item in app.info))
                self.assertEqual(app.metric[1].value, '0')
                next(item for item in app.selectbox if item.label == '运行模式').select('simulation').run(timeout=20)
                self.assertFalse(app.exception)
                self.assertTrue(any('确定性规则模拟' in item.value for item in app.warning))
                self.assertEqual(app.metric[1].value, '0')

    def test_complete_demo_flow(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {'ACE_DB': str(Path(temp) / 'ui.sqlite3'), 'ACE_MODE': 'simulation'}):
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=20)
                self.assertFalse(app.exception)
                def click(label):
                    next(b for b in app.button if b.label == label).click().run(timeout=20)
                    self.assertFalse(app.exception)
                click('载入可复现演示记忆')
                click('自主探索一次')
                self.assertEqual(app.metric[1].value, '1')
                click('运行有限探索循环')
                self.assertEqual(app.metric[1].value, '4')
                click('运行 A/B 对照')
                self.assertEqual(app.metric[3].value, '1')
                app.text_area[0].set_value('界面录入的合成观察')
                click('保存记忆')
                self.assertEqual(app.metric[0].value, '12')
                app.run()
                self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
