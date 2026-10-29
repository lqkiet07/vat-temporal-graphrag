"""End-to-end smoke test runner verifying all 5 scenarios against live server."""
import json
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8001"


def test_health() -> bool:
    print("\n--- Checking Health Endpoint ---")
    url = f"{BASE_URL}/api/health"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, f"Expected status 200, got {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Health Response: {data}")
        assert data.get("status") in ["healthy", "degraded"], "Unexpected health status"
        assert data.get("version") == "1.0.0"
        print("✓ Health check PASSED")
        return True


def test_scenario_1() -> bool:
    print("\n--- Test Scenario 1: Nominal VAT 2026 (use_llm=true, model=qwen2.5:7b) ---")
    url = f"{BASE_URL}/api/query"
    payload = {
        "query": "Doanh nghiệp tại Cần Thơ xuất khẩu phần mềm sang Nhật Bản vào tháng 03/2026 áp dụng thuế suất thuế GTGT bao nhiêu?",
        "as_of_date": "2026-03-20",
        "pipeline": "P3_FullSystem",
        "use_llm": True,
        "model": "qwen2.5:7b",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        elapsed = time.time() - t0
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Time taken: {elapsed:.2f}s")
        print(f"llm_used: {data.get('llm_used')}")
        print(f"citations: {data.get('citations')}")
        conclusion = data.get("irac_sections", {}).get("conclusion", "")
        print(f"conclusion: {conclusion}")

        assert data.get("llm_used") is True, f"Expected llm_used=True, got {data.get('llm_used')}"
        assert len(data.get("citations", [])) > 0, "Expected non-empty citations"
        assert "0%" in conclusion, f"Expected '0%' in conclusion, got: {conclusion}"
        print("✓ Scenario 1 PASSED")
        return True


def test_scenario_2() -> bool:
    print("\n--- Test Scenario 2: Temporal Trap 2024 ---")
    url = f"{BASE_URL}/api/query"
    payload = {
        "query": "Doanh nghiệp xuất khẩu dịch vụ vào tháng 05/2024 áp dụng điều kiện theo Luật 48/2024 có được không?",
        "as_of_date": "2024-05-15",
        "pipeline": "P3_FullSystem",
        "use_llm": False,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        warnings = data.get("warnings", [])
        risk_level = data.get("risk_level")
        risk_score = data.get("risk_score")
        conclusion = data.get("irac_sections", {}).get("conclusion", "")
        print(f"Risk: {risk_score} ({risk_level})")
        print(f"Warnings: {warnings}")
        print(f"Conclusion: {conclusion}")

        # Verify: catch temporal trap / warning that law not yet in effect
        has_temporal_warning = any(
            "chưa có hiệu lực" in w.lower() or "bẫy thời gian" in w.lower()
            for w in warnings
        ) or "chưa có hiệu lực" in conclusion.lower() or "bẫy thời gian" in conclusion.lower()

        assert has_temporal_warning, f"Expected temporal trap warning, got warnings: {warnings}"
        print("✓ Scenario 2 PASSED")
        return True


def test_scenario_3() -> bool:
    print("\n--- Test Scenario 3: Pure Out-of-Domain ---")
    url = f"{BASE_URL}/api/query"
    payload = {
        "query": "Thuật toán quy hoạch động tìm đường đi ngắn nhất hoạt động như thế nào?",
        "as_of_date": "2026-03-20",
        "pipeline": "P3_FullSystem",
        "use_llm": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        is_ood = data.get("is_out_of_domain")
        llm_used = data.get("llm_used")
        citations = data.get("citations", [])
        conclusion = data.get("irac_sections", {}).get("conclusion", "")
        print(f"is_out_of_domain: {is_ood}")
        print(f"llm_used: {llm_used}")
        print(f"citations: {citations}")
        print(f"conclusion: {conclusion}")

        assert is_ood is True, f"Expected is_out_of_domain=True, got {is_ood}"
        assert llm_used is False, f"Expected llm_used=False, got {llm_used}"
        assert len(citations) == 0, f"Expected empty citations, got {citations}"
        assert "không thuộc phạm vi" in conclusion.lower(), f"Expected polite refusal in conclusion, got: {conclusion}"
        print("✓ Scenario 3 PASSED")
        return True


def test_scenario_4() -> bool:
    print("\n--- Test Scenario 4: Tech-related Tax Query (Machine Learning) ---")
    url = f"{BASE_URL}/api/query"
    payload = {
        "query": "Dịch vụ phát triển machine learning cho đối tác nước ngoài chịu thuế suất GTGT mấy %?",
        "as_of_date": "2026-03-20",
        "pipeline": "P3_FullSystem",
        "use_llm": False,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        is_ood = data.get("is_out_of_domain")
        citations = data.get("citations", [])
        conclusion = data.get("irac_sections", {}).get("conclusion", "")
        print(f"is_out_of_domain: {is_ood}")
        print(f"citations: {citations}")
        print(f"conclusion: {conclusion}")

        assert is_ood is False, f"Expected is_out_of_domain=False (NOT blocked), got {is_ood}"
        assert len(citations) > 0, "Expected non-empty citations"
        assert "0%" in conclusion, f"Expected '0%' in tax conclusion, got: {conclusion}"
        print("✓ Scenario 4 PASSED")
        return True


def test_scenario_5() -> bool:
    print("\n--- Test Scenario 5: SSE Chat Stream ---")
    url = f"{BASE_URL}/api/chat/stream"
    payload = {
        "messages": [{"role": "user", "content": "Thuế suất xuất khẩu phần mềm là bao nhiêu?"}],
        "as_of_date": "2026-03-20",
        "model": "qwen2.5:7b",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        assert resp.status == 200
        lines = []
        for line in resp:
            decoded = line.decode("utf-8")
            if decoded.strip():
                lines.append(decoded.strip())

        events = [line.split(":", 1)[1].strip() for line in lines if line.startswith("event:")]
        print(f"Observed event types: {set(events)}")
        print(f"Total event frames: {len(events)}")

        assert "meta" in events, f"Expected 'meta' event in {events}"
        assert "token" in events, f"Expected 'token' event in {events}"
        assert "done" in events, f"Expected 'done' event in {events}"
        print("✓ Scenario 5 PASSED")
        return True


def main():
    print("==================================================")
    print("STARTING AUTOMATED SMOKE TEST SUITE")
    print(f"Target: {BASE_URL}")
    print("==================================================")

    results = {}
    try:
        results["Health"] = test_health()
        results["Scenario 1"] = test_scenario_1()
        results["Scenario 2"] = test_scenario_2()
        results["Scenario 3"] = test_scenario_3()
        results["Scenario 4"] = test_scenario_4()
        results["Scenario 5"] = test_scenario_5()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n==================================================")
    print("SMOKE TEST SUMMARY")
    print("==================================================")
    for test_name, status in results.items():
        print(f"{test_name:15}: {'PASSED' if status else 'FAILED'}")

    all_passed = all(results.values())
    if all_passed:
        print("\nAll 5 scenarios + health check completed successfully.")
        sys.exit(0)
    else:
        print("\nSome scenarios failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
