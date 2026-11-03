import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ace.store import Store, initial_state, ConflictError
from ace.engine import Simulation, Ollama, explore, compare, validate

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / 'data/demo.json').read_text())


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'test.sqlite3'
        self.store = Store(self.path)
        self.backend = Simulation()

    def tearDown(self):
        self.temp.cleanup()

    def test_ollama_default_matches_installed_qwen3_model(self):
        with patch.dict(os.environ, {}, clear=True):
            backend = Ollama()
        self.assertEqual(backend.model, 'qwen3:4b-instruct')
        self.assertEqual(backend.url, 'http://127.0.0.1:11434')

    def test_restart_restores_all_data(self):
        self.store.seed(FIXTURE)
        explore(self.store, self.backend)
        compare(self.store, self.backend, '如何复测？')
        self.assertEqual(self.store.export(), Store(self.path).export())
        self.assertEqual(len(Store(self.path).records('state_history')), 1)

    def test_demo_seed_is_idempotent(self):
        self.assertTrue(self.store.seed(FIXTURE))
        self.assertFalse(self.store.seed(FIXTURE))
        self.assertEqual(len(self.store.snapshot()['memories']), 3)

    def test_exploration_chain_and_citations(self):
        self.store.seed(FIXTURE)
        first = explore(self.store, self.backend)
        second = explore(self.store, self.backend)
        self.assertEqual(second['output']['question'], first['output']['next_question'])
        self.assertEqual(second['input']['context']['state'], first['state_update']['after'])
        self.assertEqual(len(self.store.snapshot()['memories']), 7)
        self.assertEqual(len(self.store.records('state_history')), 2)
        for record in (first, second):
            valid = {m['id'] for m in record['input']['context']['memories']}
            self.assertTrue(set(record['output']['references']) <= valid)

    def test_ab_isolation_and_no_state_mutation(self):
        self.store.seed(FIXTURE)
        explore(self.store, self.backend)
        before = self.store.snapshot()
        record = compare(self.store, self.backend, '如何复测？')
        a, b = record['A']['input'], record['B']['input']
        self.assertEqual(a['question'], b['question'])
        self.assertEqual(a['policy'], b['policy'])
        self.assertEqual(a['context']['state'], b['context']['state'])
        self.assertEqual(b['context']['state'], initial_state())
        self.assertEqual(b['context']['memories'], [])
        self.assertNotEqual(record['A']['output']['result'], record['B']['output']['result'])
        self.assertEqual(record['B']['output']['references'], [])
        self.assertEqual(before, self.store.snapshot())

    def test_empty_history_ab_is_identical(self):
        record = compare(self.store, self.backend, '如何复测？')
        self.assertEqual(record['A'], record['B'])

    def test_failure_has_no_partial_commit(self):
        before = self.store.export()
        with patch.object(self.backend, 'generate', side_effect=RuntimeError('offline')):
            with self.assertRaises(RuntimeError):
                explore(self.store, self.backend)
        self.assertEqual(before, self.store.export())

    def test_invalid_model_citation_rejected(self):
        output = self.backend.generate({'state': initial_state(), 'memories': []})
        output['references'] = [999]
        with patch.object(self.backend, 'generate', return_value=output):
            with self.assertRaises(ValueError):
                explore(self.store, self.backend)
        self.assertEqual(self.store.records('exploration'), [])

    def test_transaction_rolls_back_on_database_failure(self):
        before = self.store.export()
        with self.store.connect() as db:
            db.execute("CREATE TRIGGER fail_history BEFORE INSERT ON state_history BEGIN SELECT RAISE(ABORT,'test'); END")
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            explore(self.store, self.backend)
        self.assertEqual(before, self.store.export())

    def test_concurrent_state_change_rejects_stale_output(self):
        generate = self.backend.generate
        def intervening(context, question=None):
            self.store.add_memory('experience', '并发的新观察')
            return generate(context, question)
        with patch.object(self.backend, 'generate', side_effect=intervening):
            with self.assertRaises(ConflictError):
                explore(self.store, self.backend)
        self.assertEqual(self.store.records('exploration'), [])
        self.assertEqual(len(self.store.snapshot()['memories']), 1)

    def test_simulation_reproducibility(self):
        self.store.seed(FIXTURE)
        other = Store(Path(self.temp.name) / 'other.sqlite3')
        other.seed(FIXTURE)
        for _ in range(3):
            a = explore(self.store, self.backend)
            b = explore(other, self.backend)
            self.assertEqual(a['output'], b['output'])
            self.assertEqual(a['state_update'], b['state_update'])

    def test_recent_window_and_validation(self):
        for i in range(15):
            self.store.add_memory('experience', '观察 %s' % i)
        record = explore(self.store, self.backend)
        self.assertEqual(len(record['input']['context']['memories']), 12)
        with self.assertRaises(ValueError):
            compare(self.store, self.backend, ' ')
        with self.assertRaises(ValueError):
            self.store.add_memory('invalid', 'text')

    def test_ab_second_group_failure_does_not_save_partial_result(self):
        context = {'state': initial_state(), 'memories': []}
        first_output = self.backend.generate(context, '共同问题')
        with patch.object(self.backend, 'generate', side_effect=[first_output, RuntimeError('offline')]):
            with self.assertRaises(RuntimeError):
                compare(self.store, self.backend, '共同问题')
        self.assertEqual(self.store.records('comparison'), [])

    def test_malformed_ollama_envelope_is_reported(self):
        from io import BytesIO
        with patch('urllib.request.urlopen', return_value=BytesIO(b'[]')):
            with self.assertRaises(RuntimeError):
                Ollama().generate({'state': initial_state(), 'memories': []})

    def test_ollama_request_contract_without_real_model(self):
        from io import BytesIO
        context = {'state': initial_state(), 'memories': []}
        output = self.backend.generate(context, '共同问题')
        response = BytesIO(json.dumps({'response': json.dumps(output)}).encode())
        with patch('urllib.request.urlopen', return_value=response) as mock:
            result = Ollama().generate(context, '共同问题')
            self.assertEqual(validate(result, context, '共同问题'), output)
            payload = json.loads(mock.call_args[0][0].data)
            self.assertFalse(payload['stream'])
            self.assertFalse(payload['think'])
            self.assertEqual(payload['options'], {'temperature': 0, 'seed': 42})


if __name__ == '__main__':
    unittest.main()
