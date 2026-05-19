"""
reusable-review-rules wrapper.py
统一调用入口，供writer自检时自动执行 Vale + markdownlint + 其他规则。
输出格式：JSON lines，每条一行，包含文件路径、行号、规则ID、描述。
"""

import subprocess
import json
import sys
from pathlib import Path


DEFAULT_RULES_DIR = Path(__file__).parent


def run_vale(file_path: str) -> list[dict]:
    """调用 Vale CLI 检查文档风格和术语"""
    result = subprocess.run(
        ["vale", "--output", "JSON", file_path],
        capture_output=True, text=True, timeout=30
    )
    issues = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            entry = json.loads(line)
            issues.append({
                "tool": "vale",
                "severity": entry.get("Severity", "warning"),
                "rule": entry.get("Check", ""),
                "file": entry.get("File", ""),
                "line": entry.get("Line", 0),
                "message": entry.get("Message", ""),
            })
        except json.JSONDecodeError:
            pass
    return issues


def run_markdownlint(file_path: str) -> list[dict]:
    """调用 markdownlint CLI 检查 Markdown 格式"""
    result = subprocess.run(
        ["markdownlint", "--json", file_path],
        capture_output=True, text=True, timeout=30
    )
    issues = []
    try:
        data = json.loads(result.stdout)
        if isinstance(data, list):
            for entry in data:
                issues.append({
                    "tool": "markdownlint",
                    "severity": "warning",
                    "rule": entry.get("ruleNames", [""])[0] if entry.get("ruleNames") else "",
                    "file": entry.get("fileName", ""),
                    "line": entry.get("lineNumber", 0),
                    "message": entry.get("ruleDescription", ""),
                })
        elif isinstance(data, dict):
            # Some versions output dict with fileName as key
            for fname, entries in data.items():
                for entry in entries:
                    issues.append({
                        "tool": "markdownlint",
                        "severity": "warning",
                        "rule": entry.get("ruleNames", [""])[0] if entry.get("ruleNames") else "",
                        "file": fname,
                        "line": entry.get("lineNumber", 0),
                        "message": entry.get("ruleDescription", ""),
                    })
    except json.JSONDecodeError:
        pass
    return issues


def check_all(file_path: str) -> dict:
    """运行所有可用规则，返回结果"""
    results = {
        "vale": run_vale(file_path),
        "markdownlint": run_markdownlint(file_path),
    }
    results["total_issues"] = sum(len(v) for v in results.values())
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wrapper.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    results = check_all(file_path)
    print(json.dumps(results, indent=2, ensure_ascii=False))
