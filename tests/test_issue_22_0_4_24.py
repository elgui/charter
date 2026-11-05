"""Issue #22: stop diff producers at the byte budget, before buffering the whole output."""
import sys
import tempfile
import unittest
from pathlib import Path
from helpers import PKG
sys.path.insert(0, str(PKG / ".charter"))
import lib

class BoundedDiff(unittest.TestCase):
    def test_large_stdout_and_stderr_are_stopped_at_the_combined_budget(self):
        for stream in ("stdout", "stderr"):
            with self.subTest(stream=stream), tempfile.TemporaryDirectory() as tmp:
                marker = Path(tmp) / "finished"
                script = (f"import sys,time; from pathlib import Path; sys.{stream}.write('x'*2000000); "
                          f"sys.{stream}.flush(); time.sleep(0.2); Path({str(marker)!r}).write_text('unbounded')")
                r = lib.run_bounded([sys.executable, "-c", script], 60000)
                self.assertTrue(r.truncated)
                self.assertLessEqual(len(r.stdout.encode()) + len(r.stderr.encode()), 60000)
                self.assertFalse(marker.exists())
    def test_small_diff_is_kept_whole(self):
        r = lib.run_bounded([sys.executable, "-c", "print('small diff')"], 60000)
        self.assertEqual(r.stdout, "small diff\n")
        self.assertEqual(r.returncode, 0)
        self.assertFalse(r.truncated)
