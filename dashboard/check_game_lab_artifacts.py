"""A collector cannot change the inputs of an already running experiment."""
import json,tempfile,unittest
from pathlib import Path
import numpy as np
from game_lab.artifacts import atomic_report,freeze_dataset


class ArtifactChecks(unittest.TestCase):
    def test_only_published_episodes_are_frozen_and_verified(self):
        with tempfile.TemporaryDirectory() as root:
            source=Path(root)/'source';source.mkdir();target=Path(root)/'frozen'
            np.savez(source/'train-1.npz',x=np.zeros((1,90)))
            (source/'train-incomplete.npz').write_bytes(b'partial')
            atomic_report(source/'collection-train-1.json',dict(rows=[{'file':'train-1.npz'}]))
            first=freeze_dataset(source,target)
            self.assertEqual(first['episodes'],1);self.assertFalse((target/'train-incomplete.npz').exists())
            np.savez(source/'train-1.npz',x=np.ones((1,90)))
            self.assertEqual(freeze_dataset(source,target),first)
            with np.load(target/'train-1.npz') as data:self.assertEqual(data['x'].sum(),0)
            (target/'train-1.npz').write_bytes(b'changed')
            with self.assertRaises(ValueError):freeze_dataset(source,target)

    def test_missing_published_file_leaves_no_partial_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            source=Path(root)/'source';source.mkdir();target=Path(root)/'frozen'
            atomic_report(source/'collection-train-1.json',dict(rows=[{'file':'train-missing.npz'}]))
            with self.assertRaises(FileNotFoundError):freeze_dataset(source,target)
            self.assertFalse(target.exists());self.assertEqual(sorted(p.name for p in Path(root).iterdir()),['source'])

    def test_unsafe_collection_boundary_is_labelled_and_keeps_causal_corrections(self):
        import torch
        from game_lab.dataset import collect,load_sequences
        class WrongWay:
            def __call__(self,x,state):return torch.tensor([[[1.,1.]]]),None
        with tempfile.TemporaryDirectory() as root:
            report=collect(root,seed=312,episodes=1,duration=30.,actor=WrongWay(),families=('solo',),stop_unsafe=True)
            row=report['rows'][0];self.assertTrue(row['censoredAtUnsafe'])
            with np.load(Path(root)/row['file'],allow_pickle=False) as f:
                self.assertTrue(bool(f['censoredAtUnsafe']));self.assertEqual(len(f['x']),int(f['firstUnsafeDecision']))
                self.assertGreater(len(f['x']),0);self.assertLess(len(f['x']),300)
            sequences=load_sequences(root);self.assertEqual(len(sequences),1)
            self.assertEqual(len(sequences[0]['x']),row['samples']);self.assertFalse(sequences[0]['rolloutClean'])


if __name__=='__main__':unittest.main()
