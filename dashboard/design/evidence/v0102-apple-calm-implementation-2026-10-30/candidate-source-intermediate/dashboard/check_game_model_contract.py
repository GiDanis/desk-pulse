"""Real-store model descriptions never invent recurrent memory or traffic proof."""
import tempfile,unittest
from game_store import GameStore
from game_model_contract import model_rows


class ModelDescriptionChecks(unittest.TestCase):
    def test_existing_sac_replay_is_not_reported_as_recurrent_memory(self):
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);driver=next(d for d in store.drivers() if d['name']=='Memoria')
            rows=model_rows(store,driver)
            memory=next(r for r in rows if r['title']=='Memoria della guida')
            self.assertIn('Senza stato ricorrente',memory['description'])
            self.assertEqual(next(r['value'] for r in rows if r['title']=='Migliore traffico'),'Non registrato')
            self.assertEqual(next(r['value'] for r in rows if r['title']=='Versione gara conservata'),'Non registrato')

    def test_maestro_has_no_fictitious_personal_learning_model(self):
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);self.assertEqual(model_rows(store,store.drivers()[0]),[])


if __name__=='__main__':unittest.main()
