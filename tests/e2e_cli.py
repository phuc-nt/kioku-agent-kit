"""End-to-End test for Kioku CLI — runs all 6 commands against real DBs."""

import json
import subprocess
import sys


def run_cli(*args: str) -> dict | str:
    """Run a kioku CLI command and return parsed JSON or raw output."""
    result = subprocess.run(
        ["uv", "run", "kioku", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}", file=sys.stderr)
        raise RuntimeError(f"CLI command failed: kioku {' '.join(args)}\n{result.stderr}")

    output = result.stdout.strip()
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return output


import datetime


def main():
    print("🚀 Bắt đầu CLI E2E Test...")
    errors = []

    # 1. save
    print("\n[TEST] kioku save")
    try:
        res = run_cli(
            "save",
            "Cuối tuần đi cà phê với Mai, thảo luận về dự án OpenClaw rất thú vị.",
            "--mood",
            "excited",
            "--tags",
            "weekend,project,openclaw",
        )
        assert res["status"] == "saved", f"Expected saved, got {res['status']}"
        assert res["mood"] == "excited"
        assert res["tags"] == ["weekend", "project", "openclaw"]
        assert "event_time" in res, "Phase 7: event_time field must be present in save response"
        print(f"  ✅ Saved: {res['timestamp']}, event_time={res.get('event_time')}")
    except Exception as e:
        errors.append(f"save: {e}")
        print(f"  ❌ {e}")

    # 2. search
    print("\n[TEST] kioku search")
    try:
        today_str = datetime.date.today().isoformat()
        res = run_cli(
            "search", "Dự án OpenClaw", "--limit", "5", "--from", today_str, "--to", today_str
        )
        assert res["count"] >= 1, f"Expected >= 1 result, got {res['count']}"
        assert any("OpenClaw" in r["content"] or "dự án" in r["content"] for r in res["results"])
        print(f"  ✅ Found {res['count']} results")
    except Exception as e:
        errors.append(f"search: {e}")
        print(f"  ❌ {e}")

    # 3. recall
    print("\n[TEST] kioku recall")
    try:
        res = run_cli("recall", "Mai", "--hops", "2", "--limit", "10")
        assert "entity" in res
        assert res["entity"] == "Mai"
        print(f"  ✅ Entity 'Mai': {res['connected_count']} connections")
    except Exception as e:
        errors.append(f"recall: {e}")
        print(f"  ❌ {e}")

    # 4. explain
    print("\n[TEST] kioku explain")
    try:
        res = run_cli("explain", "Mai", "OpenClaw")
        assert "from" in res
        assert res["from"] == "Mai"
        assert res["to"] == "OpenClaw"
        print(f"  ✅ Connected: {res['connected']}")
    except Exception as e:
        errors.append(f"explain: {e}")
        print(f"  ❌ {e}")

    # 5. dates
    print("\n[TEST] kioku dates")
    try:
        res = run_cli("dates")
        assert res["count"] >= 1, f"Expected >= 1 date, got {res['count']}"
        print(f"  ✅ {res['count']} dates: {res['dates'][:3]}...")
    except Exception as e:
        errors.append(f"dates: {e}")
        print(f"  ❌ {e}")

    # 6. timeline
    print("\n[TEST] kioku timeline")
    try:
        yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        res = run_cli("timeline", "--limit", "5", "--from", yesterday_str, "--to", tomorrow_str)
        assert res["count"] >= 1, f"Expected >= 1 entry, got {res['count']}"
        print(f"  ✅ {res['count']} timeline entries")
    except Exception as e:
        errors.append(f"timeline: {e}")
        print(f"  ❌ {e}")

    # 7. timeline --sort-by event_time (Phase 7)
    print("\n[TEST] kioku timeline --sort-by event_time")
    try:
        res = run_cli("timeline", "--limit", "5", "--sort-by", "event_time")
        assert "sort_by" in res, "Phase 7: sort_by field must be in timeline response"
        assert res["sort_by"] == "event_time"
        print(f"  ✅ {res['count']} timeline entries (sorted by event_time)")
    except Exception as e:
        errors.append(f"timeline --sort-by event_time: {e}")
        print(f"  ❌ {e}")

    # 8. save with relative time (Phase 7 — test event_time extraction)
    print("\n[TEST] kioku save (relative time)")
    try:
        res = run_cli(
            "save",
            "Hôm qua đi ăn phở với Minh, rất ngon.",
            "--mood",
            "happy",
            "--tags",
            "food,friend",
        )
        assert res["status"] == "saved"
        assert "event_time" in res
        print(f"  ✅ Saved with event_time={res.get('event_time')}")
    except Exception as e:
        errors.append(f"save (relative time): {e}")
        print(f"  ❌ {e}")

    # Summary
    print("\n" + "=" * 50)
    if errors:
        print(f"❌ {len(errors)} test(s) FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("🎉 Tất cả 8 CLI E2E tests PASSED!")


if __name__ == "__main__":
    main()
