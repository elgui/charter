"""`review.required`: done also needs a `review:` evidence line whose anchor resolves (off by default)."""
import unittest

from helpers import make_project, run_hook, cleanup
from test_gates import write_call
from test_review_regressions import set_config, commit_all, decision, done_unit


class ReviewRequired(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def gate(self, evidence):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", done_unit(evidence)))
        return decision(out), so + se

    def test_off_by_default(self):
        self.assertNotEqual(self.gate("- `$ make test` → exit 0")[0], "deny")

    def test_required_refuses_done_without_a_review_line(self):
        set_config(self.root, review={"required": True})
        commit_all(self.root, "review required")
        d, out = self.gate("- `$ make test` → exit 0")
        self.assertEqual(d, "deny", out)
        self.assertIn("review:", out)

    def test_a_review_line_without_an_anchor_is_not_enough(self):
        set_config(self.root, review={"required": True})
        commit_all(self.root, "review required")
        self.assertEqual(self.gate("- `$ make test` → exit 0\n- review: codex — approve")[0], "deny")

    def test_an_anchored_review_line_passes(self):
        set_config(self.root, review={"required": True})
        commit_all(self.root, "review required")
        d, out = self.gate("- `$ make test` → exit 0\n- review: codex gpt-5.6 — approve — https://github.com/o/r/pull/1#issuecomment-2")
        self.assertNotEqual(d, "deny", out)


if __name__ == "__main__":
    unittest.main()
