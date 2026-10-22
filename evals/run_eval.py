import json
from pathlib import Path
import httpx

CASES_FILE = Path(__file__).resolve().parent / "cases.json"
ENDPOINT_URL = "http://127.0.0.1:8000/changelog"


def run_evaluation():
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    passed = 0
    total = len(cases)
    failures = []

    print(f"Running evaluation on {total} test cases against {ENDPOINT_URL}...\n")

    with httpx.Client(timeout=35.0) as client:
        for case in cases:
            payload = {"commit": case["input"]}
            try:
                response = client.post(ENDPOINT_URL, json=payload)
                if response.status_code != 200:
                    failures.append(
                        (case, f"HTTP {response.status_code}: {response.text}")
                    )
                    continue

                data = response.json()
                predicted_type = data.get("type")

                if predicted_type == case["expected_type"]:
                    passed += 1
                else:
                    failures.append(
                        (
                            case,
                            f"Expected type '{case['expected_type']}', got '{predicted_type}'",
                        )
                    )
            except Exception as e:
                failures.append((case, f"Request failed: {str(e)}"))

    accuracy = (passed / total) * 100
    print(f"Results: {passed}/{total} passed ({accuracy:.1f}% accuracy)\n")

    if failures:
        print("Failures:")
        for case, reason in failures:
            print(f"- Case {case['id']} ('{case['input']}'): {reason}")
    else:
        print("All test cases matched expected output types!")


if __name__ == "__main__":
    run_evaluation()