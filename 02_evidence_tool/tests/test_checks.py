"""Repeatable checks required by the assignment, plus the defects found in review.

Run:  python -m unittest -v
Each test copies data/ and config/ into a temp folder, changes one thing, and
re-runs the full pipeline — nothing is mocked.
"""
import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evidence_tool.inputs import InputError  # noqa: E402
from evidence_tool.metrics import OVERALL  # noqa: E402
from evidence_tool.pipeline import run, write_outputs  # noqa: E402

PRICE = Decimal("9.99")


class Workspace:
    """A throw-away copy of the inputs that a test can edit."""

    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "data", self.tmp / "data")
        shutil.copytree(ROOT / "config", self.tmp / "config")

    def append_events(self, *rows):
        with open(self.tmp / "data/event_log.csv", "a", newline="", encoding="utf-8") as f:
            for r in rows:
                f.write(",".join(r) + "\n")

    def rewrite_events(self, keep):
        p = self.tmp / "data/event_log.csv"
        lines = p.read_text(encoding="utf-8").splitlines()
        p.write_text("\n".join([lines[0]] + [l for l in lines[1:] if keep(l)]) + "\n", encoding="utf-8")

    def edit_json(self, name, fn):
        p = self.tmp / "config" / name
        data = json.loads(p.read_text(encoding="utf-8"))
        fn(data)
        p.write_text(json.dumps(data), encoding="utf-8")

    def run(self):
        return run(self.tmp / "data", self.tmp / "config")

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def overall(result):
    a = result["analysis"]
    return a["funnel"][OVERALL], a["money"][OVERALL], a["costs"][OVERALL]


class Base(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()

    def tearDown(self):
        self.ws.close()


class TestBaseline(Base):
    """Hand-verified numbers for the supplied data."""

    def test_overall_funnel(self):
        f, m, _ = overall(self.ws.run())
        self.assertEqual([f[k] for k in ("first_open", "qualified", "qualified_scan", "free_suggestion_viewed",
                                         "first_time_payer", "delivered_guide", "unrefunded_delivered")],
                         [50, 42, 34, 32, 10, 8, 6])

    def test_money(self):
        _, m, _ = overall(self.ws.run())
        self.assertEqual(m["verified_tx"], 10)
        self.assertEqual(m["collected_cash"], PRICE * 10)
        self.assertEqual(m["refunds"], PRICE * 2)
        self.assertEqual(m["pending_not_collected"], PRICE * 2)
        self.assertEqual(m["paid_not_delivered"], PRICE * 2)
        self.assertEqual(round(m["net_after_commission"], 2), Decimal("67.93"))

    def test_priorities_and_cards(self):
        r = self.ws.run()
        self.assertEqual([p["id"] for p in r["priorities"]], ["PR-DELIVERY", "PR-SCAN-ENTRY", "PR-PAYWALL-CLARITY"])
        self.assertEqual(len(r["priorities"][0]["participants"]), 4)
        self.assertEqual(sorted(c["type"] for c in r["cards"]), ["aso", "short_content"])


class TestRequiredChecks(Base):
    """The five repeatable checks named in the assignment."""

    def test_1_reprocessing_is_idempotent(self):
        first = self.ws.run()
        out1, out2 = self.ws.tmp / "o1", self.ws.tmp / "o2"
        write_outputs(first, out1)
        write_outputs(self.ws.run(), out2)
        for name in ("report.html", "analysis.json", "experiment_cards.json", "experiment_cards.md"):
            self.assertEqual((out1 / name).read_bytes(), (out2 / name).read_bytes(), name)
        # importing the same events again adds no users and no sales
        p = self.ws.tmp / "data/event_log.csv"
        body = p.read_text(encoding="utf-8").splitlines()[1:]
        with open(p, "a", encoding="utf-8") as f:
            f.write("\n".join(body) + "\n")
        f1, m1, _ = overall(first)
        f2, m2, _ = overall(self.ws.run())
        self.assertEqual(f1, f2)
        self.assertEqual(m1, m2)

    def test_2_zero_paid_shows_na_not_zero(self):
        self.ws.rewrite_events(lambda l: ",TX_" not in l)
        r = self.ws.run()
        f, m, c = overall(r)
        self.assertEqual(f["first_time_payer"], 0)
        self.assertEqual(m["collected_cash"], 0)
        for ch in r["analysis"]["channels"] + [OVERALL]:
            costs = r["analysis"]["costs"][ch]
            self.assertIsNone(costs["first_pay_cac_cash"], ch)
            self.assertIsNone(costs["delivered_cac_cash"], ch)
        write_outputs(r, self.ws.tmp / "o")
        html = (self.ws.tmp / "o/report.html").read_text(encoding="utf-8")
        self.assertIn(">N/A<", html)

    def test_3_new_refund_moves_the_right_metrics(self):
        before = self.ws.run()
        self.ws.append_events(["E09001", "U001", "TX_U001_01", "2026-06-21 15:00:00", "refunds", "ASA_Brand"])
        self.ws.edit_json("params.json", lambda p: p.update(cutoff="2026-06-22 00:00:00"))
        after = self.ws.run()
        fb, mb, _ = overall(before)
        fa, ma, _ = overall(after)
        self.assertEqual(fa["first_time_payer"], fb["first_time_payer"])        # still a payer
        self.assertEqual(fa["delivered_guide"], fb["delivered_guide"])          # still delivered
        self.assertEqual(fa["unrefunded_delivered"], fb["unrefunded_delivered"] - 1)
        self.assertEqual(ma["refunds"], mb["refunds"] + PRICE)
        # refunded sale loses its net (price − commission) and the commission is reversed
        self.assertEqual(mb["net_after_commission"] - ma["net_after_commission"], PRICE * Decimal("0.85"))

    def test_3b_refund_after_cutoff_is_not_known(self):
        before = self.ws.run()
        self.ws.append_events(["E09001", "U001", "TX_U001_01", "2026-07-01 09:00:00", "refunds", "ASA_Brand"])
        self.ws.edit_json("params.json", lambda p: p.update(cutoff="2026-06-21 14:00:00"))
        self.assertEqual(overall(self.ws.run())[0], overall(before)[0])

    def test_4_same_participant_more_feedback_adds_no_participant(self):
        before = self.ws.run()
        with open(self.ws.tmp / "data/feedback_sessions.csv", "a", encoding="utf-8") as f:
            f.write('S19,P06,Payment stuck in pending again,"Still pending after an hour.",Gateway retry needed\n')
        after = self.ws.run()
        self.assertEqual(after["research"]["participants"], before["research"]["participants"])
        self.assertEqual(after["research"]["sessions"], before["research"]["sessions"] + 1)
        p_before = next(p for p in before["priorities"] if p["id"] == "PR-DELIVERY")
        p_after = next(p for p in after["priorities"] if p["id"] == "PR-DELIVERY")
        self.assertEqual(p_after["participants"], p_before["participants"])
        self.assertIn("S19", [c["session_id"] for c in p_after["citations"]])
        self.assertEqual(next(s for s in after["sessions"] if s["session_id"] == "S19")["kind"], "re-test #2")

    def test_5_cost_parameter_change(self):
        before = self.ws.run()
        self.ws.edit_json("params.json", lambda p: p.update(labor_rate_usd_per_hour=50, shared_tools_usd=112))
        after = self.ws.run()
        cb, ca = before["analysis"]["costs"], after["analysis"]["costs"]
        for ch in before["analysis"]["channels"]:
            self.assertEqual(ca[ch]["delivered_cac_cash"], cb[ch]["delivered_cac_cash"], ch)  # cash CAC unchanged
            self.assertEqual(ca[ch]["labor"], cb[ch]["labor"] * 2, ch)                      # labor doubles
        self.assertEqual(ca[OVERALL]["shared"], cb[OVERALL]["shared"] + 100)               # shared once
        self.assertEqual(ca[OVERALL]["cash_contribution"], cb[OVERALL]["cash_contribution"] - 100)


class TestCountingRules(Base):
    def test_new_verification_event_adds_no_revenue(self):
        before = self.ws.run()
        self.ws.append_events(["E09002", "U001", "TX_U001_01", "2026-06-20 10:12:00", "verifications", "ASA_Brand"])
        _, mb, _ = overall(before)
        _, ma, _ = overall(self.ws.run())
        self.assertEqual(ma["collected_cash"], mb["collected_cash"])
        self.assertEqual(ma["verified_tx"], mb["verified_tx"])

    def test_undelivered_affects_delivery_not_payers(self):
        before = self.ws.run()
        self.ws.rewrite_events(lambda l: not l.startswith("E00161,"))  # drop TX_U001_01 delivery
        after = self.ws.run()
        fb, mb, _ = overall(before)
        fa, ma, _ = overall(after)
        self.assertEqual(fa["first_time_payer"], fb["first_time_payer"])
        self.assertEqual(fa["delivered_guide"], fb["delivered_guide"] - 1)
        self.assertEqual(fa["unrefunded_delivered"], fb["unrefunded_delivered"] - 1)
        self.assertEqual(ma["collected_cash"], mb["collected_cash"])     # cash was still collected
        self.assertEqual(ma["paid_not_delivered"], mb["paid_not_delivered"] + PRICE)

    def test_pending_is_not_collected_cash(self):
        _, m, _ = overall(self.ws.run())
        self.assertEqual(m["pending_tx"], 2)
        self.assertEqual(m["collected_cash"], PRICE * m["verified_tx"])

    def test_conflicting_duplicate_is_an_error_not_a_merge(self):
        self.ws.append_events(["E00002", "U001", "", "2026-06-20 09:02:10", "scan", "ASA_Brand"])
        r = self.ws.run()
        self.assertIn("event.duplicate_conflict", [i["code"] for i in r["issues"]])

    def test_shared_costs_only_in_overall(self):
        r = self.ws.run()
        for ch in r["analysis"]["channels"]:
            self.assertNotIn("shared", r["analysis"]["costs"][ch])
        self.assertEqual(r["analysis"]["costs"][OVERALL]["shared"], Decimal("20.00"))


class TestValidation(Base):
    def test_missing_column_is_a_clear_error(self):
        p = self.ws.tmp / "data/channel_data.csv"
        p.write_text(p.read_text().replace("cash_costs", "cost"), encoding="utf-8")
        with self.assertRaisesRegex(InputError, "missing required column.*cash_costs"):
            self.ws.run()

    def test_invalid_cost_is_reported_and_cac_is_na(self):
        p = self.ws.tmp / "data/channel_data.csv"
        p.write_text(p.read_text().replace("450.0", "abc"), encoding="utf-8")
        r = self.ws.run()
        self.assertIn("channel.invalid_cost", [i["code"] for i in r["issues"]])
        self.assertIsNone(r["analysis"]["costs"]["ASA_Brand"]["delivered_cac_cash"])

    def test_unknown_event_type_and_bad_timestamp_are_reported(self):
        self.ws.append_events(["E09003", "U001", "", "yesterday", "first_open", "ASA_Brand"],
                              ["E09004", "U001", "", "2026-06-20 11:00:00", "installed", "ASA_Brand"])
        codes = [i["message"] for i in self.ws.run()["issues"] if i["code"] == "event.invalid"]
        self.assertTrue(any("timestamp" in c for c in codes))
        self.assertTrue(any("unknown event_type" in c for c in codes))

    def test_raw_feedback_with_unquoted_commas_is_repaired(self):
        r = self.ws.run()
        s01 = next(s for s in r["sessions"] if s["session_id"] == "S01")
        self.assertEqual(s01["observed_behavior"], "Scanned room successfully on first try, hesitated at paywall")
        self.assertEqual(s01["user_statements"], "Why do I have to pay before seeing the full report?")
        self.assertTrue(s01["repaired"])
        self.assertIn("feedback.repaired_rows", [i["code"] for i in r["issues"]])

    def test_broken_citation_is_reported(self):
        self.ws.edit_json("experiments.json",
                          lambda d: d["cards"][0]["evidence"].append({"session": "S99", "field": "user_statements"}))
        self.assertIn("card.bad_citation", [i["code"] for i in self.ws.run()["issues"]])

    def test_exactly_two_cards_required(self):
        self.ws.edit_json("experiments.json", lambda d: d["cards"].pop())
        with self.assertRaisesRegex(InputError, "exactly 2 cards"):
            self.ws.run()


class TestReadinessAndCopy(Base):
    def test_cards_blocked_while_delivery_not_ready(self):
        r = self.ws.run()
        self.assertTrue(all(c["status"] == "BLOCKED" and not c["approved_for_launch"] for c in r["cards"]))

    def test_flag_true_but_data_not_ready_stays_blocked(self):
        self.ws.edit_json("params.json", lambda p: p["readiness"].update(commercial_delivery_ready=True))
        r = self.ws.run()
        self.assertTrue(all(c["status"] == "BLOCKED" for c in r["cards"]))
        self.assertIn("readiness.flag_contradicts_data", [i["code"] for i in r["issues"]])

    def test_ready_data_and_flag_gives_draft_never_approved(self):
        self.ws.edit_json("params.json", lambda p: p["readiness"].update(commercial_delivery_ready=True))
        self.ws.append_events(["E09005", "U014", "TX_U014_01", "2026-06-20 10:20:00", "delivery", "ASA_Category"],
                              ["E09006", "U040", "TX_U040_01", "2026-06-20 10:20:00", "delivery", "Pinterest_SEO"])
        self.ws.rewrite_events(lambda l: "TX_U015_01" not in l and "TX_U031_01" not in l)
        r = self.ws.run()
        self.assertTrue(r["delivery_ready"])
        self.assertTrue(all(c["status"] == "DRAFT" and not c["approved_for_launch"] for c in r["cards"]))

    def test_forbidden_claim_fails_copy_check(self):
        self.ws.edit_json("experiments.json", lambda d: d["cards"][1]["copy"].update(hook="This will go viral"))
        r = self.ws.run()
        card = next(c for c in r["cards"] if c["type"] == "short_content")
        self.assertFalse(card["copy_check"]["passed"])

    def test_keyword_volume_is_rejected(self):
        self.ws.edit_json("experiments.json",
                          lambda d: d["cards"][0]["keyword_intent_groups"][0].update(search_volume_monthly=12000))
        card = next(c for c in self.ws.run()["cards"] if c["type"] == "aso")
        self.assertFalse(card["copy_check"]["passed"])

    def test_budget_over_cap_is_flagged(self):
        self.ws.edit_json("experiments.json", lambda d: d["cards"][0].update(budget_cap_usd=1400))
        r = self.ws.run()
        self.assertFalse(r["budget"]["within_cap"])


class TestCli(Base):
    def test_cli_runs_and_strict_mode(self):
        out = self.ws.tmp / "cli_out"
        cmd = [sys.executable, str(ROOT / "analyze.py"), "--data", str(self.ws.tmp / "data"),
               "--config", str(self.ws.tmp / "config"), "--out", str(out)]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((out / "report.html").exists())
        (self.ws.tmp / "data/event_log.csv").unlink()
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(res.returncode, 2)
        self.assertIn("Missing input file", res.stderr)


if __name__ == "__main__":
    unittest.main()
