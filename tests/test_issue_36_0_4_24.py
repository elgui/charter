"""Issue #36: a resume note is owner input, not log metadata."""
import unittest
import test_chain_0_4_7 as fixture

class ResumePrivacy(fixture.ChainCase):
    def test_resume_logs_note_length_without_the_note(self):
        self.start()
        self.assertEqual(fixture.cli(self.root, "stop").returncode, 0)
        note = "person" + "@example.invalid private note"
        result = fixture.resume(self.root, note)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn(note, self.events())
        gate_log = (self.root / ".git" / "charter" / "log.jsonl").read_text()
        self.assertNotIn(note, gate_log)
        self.assertIn(f"note: {len(note)} characters", self.events())
