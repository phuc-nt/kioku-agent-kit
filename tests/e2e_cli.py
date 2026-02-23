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


def main():
    print("🚀 Bắt đầu CLI E2E Test...")
    errors = []

    # 1. save
    print("\n[TEST] kioku save")
    try:
        res = run_cli("save", "CLI E2E test: đi cà phê với Lan, bàn về dự án AI rất hào hứng.", "--mood", "excited", "--tags", "test,cli,e2e")
        assert res["status"] == "saved", f"Expected saved, got {res['status']}"
        assert res["mood"] == "excited"
        assert res["tags"] == ["test", "cli", "e2e"]
        print(f"  ✅ Saved: {res['timestamp']}")
    except Exception as e:
        errors.append(f"save: {e}")
        print(f"  ❌ {e}")

    # 2. search
    print("\n[TEST] kioku search")
    try:
        res = run_cli("search", "dự án AI", "--limit", "5")
        assert res["count"] >= 1, f"Expected >= 1 result, got {res['count']}"
        assert any("AI" in r["content"] or "dự án" in r["content"] for r in res["results"])
        print(f"  ✅ Found {res['count']} results")
    except Exception as e:
        errors.append(f"search: {e}")
        print(f"  ❌ {e}")

    # 3. recall
    print("\n[TEST] kioku recall")
    try:
        res = run_cli("recall", "Lan")
        assert "entity" in res
        assert res["entity"] == "Lan"
        print(f"  ✅ Entity 'Lan': {res['connected_count']} connections")
    except Exception as e:
        errors.append(f"recall: {e}")
        print(f"  ❌ {e}")

    # 4. explain
    print("\n[TEST] kioku explain")
    try:
        res = run_cli("explain", "Lan", "AI")
        assert "from" in res
        assert res["from"] == "Lan"
        assert res["to"] == "AI"
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
        res = run_cli("timeline", "--limit", "5")
        assert res["count"] >= 1, f"Expected >= 1 entry, got {res['count']}"
        print(f"  ✅ {res['count']} timeline entries")
    except Exception as e:
        errors.append(f"timeline: {e}")
        print(f"  ❌ {e}")

    # Summary
    print("\n" + "=" * 50)
    if errors:
        print(f"❌ {len(errors)} test(s) FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("🎉 Tất cả 6 CLI E2E tests PASSED!")


if __name__ == "__main__":
    main()
