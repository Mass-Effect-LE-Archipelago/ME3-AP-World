"""Offline parser/analysis tests for the career-trace probe; no game contact."""
import unittest

from tools.le3apbridge import career_trace_probe as probe


def record(sequence, method, leaving=0, route=1, depth=1, table=0, valid=0, values=0, invocation=None, thread=7):
    return ":".join(map(str, (sequence, invocation or sequence, thread, route, method, leaving,
                              depth, 0, table, valid, values)))


class FakeBridge:
    def __init__(self, records, capacity=128):
        self.records, self.capacity = records, capacity

    def request(self, text):
        _, after, limit = text.split()
        after, limit = int(after), int(limit)
        latest = len(self.records)
        oldest = max(1, latest - self.capacity + 1) if latest else 0
        selected = [r for i, r in enumerate(self.records, 1) if i >= oldest and i > after][:limit]
        return " ".join(["1", "career_trace_readonly", "31", str(oldest), str(latest), str(len(selected)), *selected])


def vanilla_commit():
    # FinalCommit seen via event and internal routes, then the vanilla order.
    return [record(1, 1, route=0, depth=1), record(2, 1, route=1, depth=2, invocation=2),
            record(3, 3, route=2), record(4, 3, leaving=1, route=2, invocation=3),
            record(5, 4, table=2, valid=15), record(6, 4, leaving=1, table=2, valid=15, invocation=5),
            record(7, 2, table=1, valid=15), record(8, 2, leaving=1, table=1, valid=15, values=0b0101, invocation=7),
            record(9, 5, route=2, table=1, valid=15, values=0b0101),
            record(10, 5, leaving=1, route=2, table=1, valid=15, values=0b0101, invocation=9),
            record(11, 1, leaving=1, depth=2, invocation=2), record(12, 1, leaving=1, route=0, depth=1, invocation=1)]


class CareerTraceProbeTests(unittest.TestCase):
    def test_parse_rejects_malformed_pages(self):
        for bad in ("ERR career_trace_disabled", "OK 1 career_trace_readonly 31 1 1 2 " + record(1, 1),
                    "OK 1 career_trace_readonly 31 1 1 1 1:2:3", "OK 1 career_trace_readonly 31 1 1 1 " + record(1, 9),
                    "OK 1 career_trace_readonly 31 1 2 2 " + record(2, 1) + " " + record(1, 1)):
            with self.assertRaises(ValueError):
                probe.parse_page(bad)

    def test_vanilla_order_exposes_seam_and_virmire_values(self):
        trace = probe.read_all(FakeBridge(vanilla_commit()).request)
        self.assertIsNone(trace["gap"])
        analysis = probe.analyze(trace)
        self.assertEqual(len(analysis["commits"]), 1)
        commit = analysis["commits"][0]
        self.assertTrue(commit["complete"] and commit["seam_observed"])
        self.assertEqual(commit["order"][0], "FinalCommit:enter")
        self.assertEqual(commit["virmire_after_plot_choices"],
                         {"13827": True, "13828": False, "13940": True, "13939": False})
        self.assertIn("FinalCommit:event", commit["routes"])
        self.assertIn("FinalCommit:internal", commit["routes"])
        self.assertEqual(analysis["findings"], [])

    def test_save_before_plot_choices_is_not_the_seam(self):
        records = [record(1, 1, depth=1), record(2, 5, route=2), record(3, 2), record(4, 2, leaving=1),
                   record(5, 1, leaving=1, depth=1)]
        commit = probe.analyze(probe.read_all(FakeBridge(records).request))["commits"][0]
        self.assertFalse(commit["seam_observed"])

    def test_preview_tables_counted_outside_commit(self):
        records = [record(1, 4, depth=0, table=3), record(2, 4, leaving=1, depth=0, table=3)]
        analysis = probe.analyze(probe.read_all(FakeBridge(records).request))
        self.assertEqual(analysis["commits"], [])
        self.assertEqual(analysis["preview_tables_initialized"], 1)

    def test_overwritten_ring_and_unfinished_commit_are_reported(self):
        records = [record(i, 4, depth=0, table=3) for i in range(1, 140)] + [record(140, 1, depth=1)]
        trace = probe.read_all(FakeBridge(records).request)
        self.assertEqual(trace["gap"], {"expected": 1, "first_available": 13})
        findings = probe.analyze(trace)["findings"]
        self.assertTrue(any("overwrote" in f for f in findings))
        self.assertTrue(any("not returned" in f for f in findings))


if __name__ == "__main__":
    unittest.main()
