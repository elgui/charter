"""Issue #15: exercise the squash fixture with a numeric first abbreviation."""
import unittest
from unittest import mock
import test_review_regressions as review

class NumericSquash(unittest.TestCase):
    def test_historical_label_with_numeric_initial_abbreviation(self):
        fixture = review.SquashedEvidence("test_synthesis_labels_a_squashed_sha_historical")
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        real = fixture.sha
        values = iter(["1234567"])
        def sha(*args):
            return next(values, None) or real(*args)
        with mock.patch.object(fixture, "sha", side_effect=sha):
            fixture.test_synthesis_labels_a_squashed_sha_historical()
