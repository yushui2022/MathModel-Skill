"""Score realistic prompts against the ten Standard skill descriptions.

This is a deterministic lexical proxy for skill *discovery*, not a model-based
routing test. It exists to catch description collisions: if two skills describe
themselves in borrowed words, the proxy ranks both highly for the same prompt.
Use it as a fast regression signal when editing descriptions, and pair it with a
real model-based eval before claiming discovery quality.

Usage (repo root, stdlib only):

    python scripts/check_skill_triggers.py
    python scripts/check_skill_triggers.py --strict
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = REPO_ROOT / "skills"
CASES_FILE = REPO_ROOT / "evals" / "trigger-cases.json"
DESCRIPTION = re.compile(r"^description:[ \t]*(.+)$", re.M)
# A prompt that scores below this against every skill is treated as out of scope.
OUT_OF_SCOPE = 0.12


def read_description(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = DESCRIPTION.search(text)
    if not match:
        raise SystemExit(f"[FAIL] {skill_dir.name}: SKILL.md has no description line")
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return json.loads(value)
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value


def tokens(text: str) -> list[str]:
    text = text.lower()
    out = re.findall(r"[a-z0-9_.]+", text)
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        out.extend(run[index : index + 2] for index in range(len(run) - 1))
    return out


def build_index(documents: dict[str, str]) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    document_frequency: Counter[str] = Counter()
    counted: dict[str, Counter[str]] = {}
    for key, text in documents.items():
        bag = Counter(tokens(text))
        counted[key] = bag
        for token in set(bag):
            document_frequency[token] += 1
    total = len(documents)
    idf = {token: math.log((1 + total) / (1 + count)) + 1 for token, count in document_frequency.items()}

    def normalise(bag: Counter[str]) -> dict[str, float]:
        weighted = {token: count * idf.get(token, 1.0) for token, count in bag.items()}
        norm = math.sqrt(sum(value * value for value in weighted.values())) or 1.0
        return {token: value / norm for token, value in weighted.items()}

    return {key: normalise(bag) for key, bag in counted.items()}, idf


def rank(prompt: str, vectors: dict[str, dict[str, float]], idf: dict[str, float]) -> list[tuple[str, float]]:
    weighted = {token: count * idf.get(token, 1.0) for token, count in Counter(tokens(prompt)).items()}
    norm = math.sqrt(sum(value * value for value in weighted.values())) or 1.0
    prompt_vector = {token: value / norm for token, value in weighted.items()}
    scored = {
        key: sum(prompt_vector.get(token, 0.0) * weight for token, weight in vector.items())
        for key, vector in vectors.items()
    }
    return sorted(scored.items(), key=lambda item: -item[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any case misses")
    args = parser.parse_args(argv)

    skills = sorted(path for path in SKILLS.iterdir() if path.is_dir())
    documents = {path.name: read_description(path) for path in skills}
    vectors, idf = build_index(documents)
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]

    misses = 0
    for case in cases:
        ranked = rank(case["prompt"], vectors, idf)
        top, score = ranked[0]
        runner_up, _ = ranked[1]
        expected = case["expect"]
        if expected is None:
            passed = score < OUT_OF_SCOPE
            verdict = "OK  " if passed else "MISS"
        else:
            passed = top == expected
            verdict = "OK  " if passed else "MISS"
        misses += 0 if passed else 1
        print(f"[{verdict}] #{case['id']:02d} expect={expected or '(none)':38} top1={top:38} next={runner_up:38} score={score:.2f}")
        if not passed:
            print(f"        prompt: {case['prompt']}")

    print()
    print(f"trigger cases: {len(cases) - misses}/{len(cases)} matched")

    pairs = []
    names = list(documents)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            similarity = sum(vectors[left].get(token, 0.0) * weight for token, weight in vectors[right].items())
            pairs.append((similarity, left, right))
    print("closest description pairs (higher means more overlapping wording):")
    for similarity, left, right in sorted(pairs, reverse=True)[:3]:
        print(f"  {similarity:.3f}  {left} <-> {right}")

    if misses and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
