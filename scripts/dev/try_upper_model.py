"""상위 모델(gemini-3.8-flash)을 한 번 불러 호출 설정이 먹는지 본다. 하루 한도(20회) 가운데 1회를 쓴다.

무료 한도가 풀린 뒤(한국 시간 17시) 배치를 돌리기 전에 한 번만 돌린다. 지어낸 짧은 특약 글에
급부 추출 지시문(extract/benefits.py의 PROMPT)과 스키마(SCHEMA)를 그대로 써서, 실제 추출과 같은 꼴의 요청을 보낸다.
503이 와도 다시 부르지 않는다(한 번만 부른다).

  GEMINI_API_KEY=... python3 scripts/dev/try_upper_model.py                     # config.GENERATION 설정 그대로
  GEMINI_API_KEY=... python3 scripts/dev/try_upper_model.py --level medium      # 사고 수준만 바꿔 견주기
  GEMINI_API_KEY=... python3 scripts/dev/try_upper_model.py --max-tokens 65536
  python3 scripts/dev/try_upper_model.py --dry-run                               # 보낼 요청만 찍는다. 키가 없어도 되고 부르지 않는다

찍는 것: HTTP 상태, finishReason, 토큰 사용량(입력, 사고, 답, 합계), 걸린 시간, 응답에서 읽은 급부 수.
키는 환경변수 GEMINI_API_KEY에서만 읽는다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from postlife import config  # noqa: E402
from postlife.extract import benefits as B  # noqa: E402
from postlife.gemini import Gemini, GeminiError, GeminiTruncated, usage_text  # noqa: E402

# 지어낸 특약 글이다. 실제 공시 문서의 문구가 아니다.
TITLE = "무배당 예시건강특약(갱신형)"
TEXT = """(특약보험가입금액 1,000만원 기준)
급부명 | 지급사유 | 지급금액
예시진단보험금 | 피보험자가 보장개시일 이후에 예시질환으로 진단확정되었을 때 (최초 1회한) | 1년미만 500만원 / 1년이상 1,000만원
예시입원보험금 | 피보험자가 예시질환의 치료를 직접 목적으로 4일 이상 입원하였을 때 (3일 초과 1일당, 120일 한도) | 2만원
예시수술보험금 | 피보험자가 예시질환의 치료를 직접 목적으로 수술을 받았을 때 (수술 1회당) | 100만원
주) 보장개시일은 계약일부터 그날을 포함하여 90일이 지난 날의 다음날로 합니다."""


class _DryRun(Exception):
    pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default=config.MODEL_SUMMARY)
    p.add_argument("--level", choices=["low", "medium", "high"], help="thinkingLevel을 이 값으로 바꿔 보낸다")
    p.add_argument("--max-tokens", type=int, help="maxOutputTokens를 이 값으로 바꿔 보낸다")
    p.add_argument("--timeout", type=float, help="응답 대기 시간(초). 없으면 config.TIMEOUT")
    p.add_argument("--dry-run", action="store_true", help="요청 본문만 찍고 부르지 않는다")
    args = p.parse_args(argv)

    model = args.model
    gen = dict(config.GENERATION.get(model) or {})
    if args.level:
        gen["thinkingConfig"] = {"thinkingLevel": args.level}
    if args.max_tokens:
        gen["maxOutputTokens"] = args.max_tokens

    record: dict = {}

    def post(url, headers=None, json=None, timeout=None):
        record.update(url=url, body=json, timeout=timeout)
        if args.dry_run:
            raise _DryRun()
        import requests

        start = time.monotonic()
        try:
            resp = requests.post(url, headers=headers, json=json, timeout=timeout)
        finally:
            record["seconds"] = time.monotonic() - start
        record["status"] = resp.status_code
        return resp

    gemini = Gemini(
        api_key="dry-run" if args.dry_run else None,       # 실제 호출은 환경변수 GEMINI_API_KEY만 쓴다
        post=post,
        generation={model: gen},
        timeout={model: args.timeout} if args.timeout else None,
        retry_wait={model: ()},                             # 503이 와도 다시 부르지 않는다
        timeout_retries={model: 0},
    )
    prompt = B.PROMPT.format(title=TITLE, text=TEXT)

    error: GeminiError | None = None
    raw = None
    try:
        raw = gemini.generate(model, prompt, schema=B.SCHEMA)
    except _DryRun:
        pass
    except GeminiError as e:
        error = e

    sent = record.get("body") or {}
    print(f"모델 {model}, 대기 상한 {record.get('timeout')}초, 지시문 {len(prompt):,}자")
    print("generationConfig (responseSchema 제외):",
          json.dumps({k: v for k, v in (sent.get("generationConfig") or {}).items() if k != "responseSchema"},
                     ensure_ascii=False))
    if args.dry_run:
        print("--dry-run: 부르지 않았습니다.")
        return 0

    meta = gemini.last_meta
    print(f"HTTP 상태 {record.get('status', '응답 없음')}, 걸린 시간 {record.get('seconds', 0.0):.1f}초, 요청 수 {gemini.calls.get(model, 0)}")
    if meta:
        print(f"finishReason {meta.get('finishReason') or '(없음)'}")
        print("토큰 사용량:", usage_text(meta.get("usage") or {}, (sent.get("generationConfig") or {}).get("maxOutputTokens")))
        print("usageMetadata 원본:", json.dumps(meta.get("usage") or {}, ensure_ascii=False))
    if isinstance(error, GeminiTruncated):
        print("결과: 토큰 상한에서 잘림 →", error)
        return 1
    if error is not None:
        print("결과: 실패 →", error)
        return 1
    items = raw.get("benefits") if isinstance(raw, dict) else None
    print(f"결과: 성공, 급부 {len(items) if isinstance(items, list) else '?'}건")
    print(json.dumps(raw, ensure_ascii=False, indent=1)[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
