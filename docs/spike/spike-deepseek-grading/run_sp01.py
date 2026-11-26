# -*- coding: utf-8 -*-
"""
SP-01 DeepSeek 结构化输出、延迟与费用 —— 实测脚本

依据：
  docs/spike/plan.md 第 2 节（SP-01 步骤、成功标准、产出）
  ADR-003 第 2 条（30 秒超时）、第 4 条（输出校验）
  docs/spike/spike-deepseek-grading/README.md 第 19 行（王麒博复核项）

用法：
  1) 设置环境变量 DEEPSEEK_API_KEY（必须，密钥不写进任何文件）
  2) 在本文件所在目录执行：py run_sp01.py
     （Windows 上若 `python` 命令无反应，一律改用 `py`；其他环境可用 python run_sp01.py）

自动产出（写入本目录）：
  prompt.md                       提示词版本（plan.md:65）
  evidence/raw_runs.csv           21 次调用摘要表
  evidence/raw_responses.jsonl    21 次完整记录（保留全部原始响应）
  evidence/summary.txt            结构通过率、P95、超时率、token 与费用估算依据

说明：
  - 样本全部为合成数据，不含真实学生答案（plan.md:52）。
  - 密钥只从环境变量读取（plan.md:52），任何产出文件都不含密钥。
  - 21 次调用会产生真实费用；单价以 DeepSeek 官网当日定价为准，本脚本不预置价格数字。
  - 统计分母与 P95 口径需由王麒博复核（本目录 README.md:19）。
"""
import os
import sys
import json
import csv
import time
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
EVIDENCE = BASE / "evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)

# 模型与地址写在最前面，以 DeepSeek 官网当日显示为准，可按需改
API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()

# ADR-003:36 后端模型调用超时 30 秒；本探针用它验证"同步方案能否成立"
TIMEOUT_SECONDS = 30.0
# 每个样本 7 次，共 21 次，取 20 次有效（plan.md:49）
REPEATS = 7
STAT_DENOMINATOR = 20

PROMPT_VERSION = "SP01-2026-11-22"

SYSTEM_PROMPT = """你是主观题阅卷助手。只输出一个 JSON 对象，不要输出任何解释、Markdown 或代码块标记。

JSON 结构必须严格如下：
{
  "rubricHits": [
    {"rubricId": "评分点ID", "hit": true 或 false, "score": 该评分点得分}
  ],
  "aiScore": 所有评分点得分之和,
  "aiReason": "简短理由"
}

规则：
1. rubricHits 必须覆盖题目给出的每一个评分点 ID，不多不少、不重复。
2. hit 只能是布尔值；命中(hit=true)时 score 等于该评分点满分，未命中(hit=false)时 score 为 0。
3. aiScore 必须等于所有 score 之和，且在 0 到题目满分之间。
4. aiReason 为字符串。
"""

# 3 个合成样本：10 分简答(2 评分点)、20 分论述(4 评分点)、空答案（plan.md:48）
SAMPLES = [
    {
        "id": "S1",
        "desc": "10分简答题/2个评分点",
        "totalScore": 10,
        "rubric": [
            {"rubricId": "R1", "score": 6, "desc": "写出事务的原子性含义"},
            {"rubricId": "R2", "score": 4, "desc": "举出一个原子性被破坏的例子"},
        ],
        "stem": "简述数据库事务的原子性，并举例说明。",
        "referenceAnswer": "原子性指事务内的操作要么全部成功、要么全部回滚，不允许只执行一部分；例如转账扣款成功但入账失败时，必须整体回滚。",
        "studentAnswer": "原子性就是一个事务里的操作不能只做一半，要么都成功要么都撤销。比如转账时 A 扣了钱 B 没收到，这就破坏了原子性，需要回滚。",
    },
    {
        "id": "S2",
        "desc": "20分论述题/4个评分点",
        "totalScore": 20,
        "rubric": [
            {"rubricId": "R3", "score": 5, "desc": "说明幂等的定义"},
            {"rubricId": "R4", "score": 5, "desc": "说明唯一约束的作用"},
            {"rubricId": "R5", "score": 5, "desc": "说明条件更新的作用"},
            {"rubricId": "R6", "score": 5, "desc": "说明定时扫描兜底的必要性"},
        ],
        "stem": "论述在交卷场景中如何保证重复提交只产生一次状态迁移。",
        "referenceAnswer": "幂等指同一请求重复执行结果不变；唯一约束防止同一答卷插入多行；条件更新 UPDATE ... WHERE status='DRAFT' 保证只有第一次能改状态；定时扫描作为请求兜底，处理进程崩溃或请求丢失。",
        "studentAnswer": "交卷要幂等。首先对 (paperId, studentId) 加唯一约束，重复插入会冲突。然后用条件更新，只有 DRAFT 才能改成 SUBMITTED，并发时第二个请求更新不到行。最后加定时扫描，防止请求丢了没人交卷。",
    },
    {
        "id": "S3",
        "desc": "空答案（用 S1 的题目）",
        "totalScore": 10,
        "rubric": [
            {"rubricId": "R1", "score": 6, "desc": "写出事务的原子性含义"},
            {"rubricId": "R2", "score": 4, "desc": "举出一个原子性被破坏的例子"},
        ],
        "stem": "简述数据库事务的原子性，并举例说明。",
        "referenceAnswer": "原子性指事务内的操作要么全部成功、要么全部回滚，不允许只执行一部分；例如转账扣款成功但入账失败时，必须整体回滚。",
        "studentAnswer": "",
    },
]


def build_user_message(sample):
    return json.dumps({
        "type": "SHORT_ANSWER" if sample["totalScore"] == 10 else "ESSAY",
        "stem": sample["stem"],
        "referenceAnswer": sample["referenceAnswer"],
        "totalScore": sample["totalScore"],
        "rubric": [
            {"rubricId": r["rubricId"], "score": r["score"], "description": r["desc"]}
            for r in sample["rubric"]
        ],
        "studentAnswer": sample["studentAnswer"],
    }, ensure_ascii=False)


def call_once(sample, timeout):
    """调用一次 DeepSeek，返回耗时、HTTP 状态、token 与原始响应。"""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(sample)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "stream": False,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + API_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    base = {
        "startedAt": started,
        "elapsedSec": 0.0,
        "httpStatus": "",
        "content": "",
        "promptTokens": "",
        "completionTokens": "",
        "totalTokens": "",
        "error": "",
        "detail": "",
    }
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            elapsed = time.perf_counter() - t0
            body = json.loads(raw)
            usage = body.get("usage", {}) or {}
            base.update({
                "elapsedSec": round(elapsed, 3),
                "httpStatus": getattr(resp, "status", 200),
                "content": body["choices"][0]["message"]["content"],
                "promptTokens": usage.get("prompt_tokens", ""),
                "completionTokens": usage.get("completion_tokens", ""),
                "totalTokens": usage.get("total_tokens", ""),
            })
            return base
    except urllib.error.HTTPError as e:
        base["elapsedSec"] = round(time.perf_counter() - t0, 3)
        base["httpStatus"] = e.code
        base["error"] = "HTTP_%d" % e.code
        try:
            base["detail"] = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return base
    except Exception as e:
        base["elapsedSec"] = round(time.perf_counter() - t0, 3)
        name = type(e).__name__
        if "Timeout" in name or "timed out" in str(e).lower():
            base["error"] = "TIMEOUT"
        else:
            base["error"] = "NETWORK_" + name
        base["detail"] = str(e)[:200]
        return base


def validate(content, sample):
    """ADR-003:43-45 第 4 条输出校验（整题原子），返回 (是否通过, 失败类别)。"""
    if not isinstance(content, str) or not content.strip():
        return False, "EMPTY_CONTENT"
    try:
        data = json.loads(content)
    except Exception:
        return False, "NON_JSON"
    if not isinstance(data, dict):
        return False, "NOT_OBJECT"
    for key in ("rubricHits", "aiScore", "aiReason"):
        if key not in data:
            return False, "MISSING_FIELD:" + key
    hits = data["rubricHits"]
    if not isinstance(hits, list):
        return False, "TYPE_ERROR:rubricHits"
    expected = {r["rubricId"]: r["score"] for r in sample["rubric"]}
    seen = []
    total = 0
    for h in hits:
        if not isinstance(h, dict):
            return False, "TYPE_ERROR:rubricHit"
        rid, hit, score = h.get("rubricId"), h.get("hit"), h.get("score")
        if not isinstance(rid, str):
            return False, "TYPE_ERROR:rubricId"
        if rid not in expected:
            return False, "UNKNOWN_RUBRIC_ID:" + rid
        seen.append(rid)
        if not isinstance(hit, bool):
            return False, "TYPE_ERROR:hit"
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            return False, "TYPE_ERROR:score"
        want = expected[rid] if hit else 0
        if score != want:
            return False, "HIT_SCORE_MISMATCH"
        total += score
    if len(seen) != len(set(seen)):
        return False, "DUPLICATE_RUBRIC_ID"
    if set(seen) != set(expected):
        return False, "RUBRIC_ID_INCOMPLETE"
    ai = data["aiScore"]
    if isinstance(ai, bool) or not isinstance(ai, (int, float)):
        return False, "TYPE_ERROR:aiScore"
    if total != ai:
        return False, "SCORE_SUM_MISMATCH"
    if not (0 <= ai <= sample["totalScore"]):
        return False, "SCORE_OUT_OF_RANGE"
    if not isinstance(data["aiReason"], str):
        return False, "TYPE_ERROR:aiReason"
    return True, "OK"


def p95(values):
    """最近秩法：排序后取 ceil(0.95*n)-1 位置（0 基）。口径需王麒博复核。"""
    s = sorted(values)
    if not s:
        return None
    idx = math.ceil(0.95 * len(s)) - 1
    return s[max(0, min(idx, len(s) - 1))]


def main():
    if not API_KEY:
        print("没有读到 DEEPSEEK_API_KEY，请先设置环境变量再运行：")
        print("  PowerShell : $env:DEEPSEEK_API_KEY=\"你的密钥\"")
        print("  命令提示符 : set DEEPSEEK_API_KEY=你的密钥")
        print("  Git Bash   : export DEEPSEEK_API_KEY=你的密钥")
        sys.exit(1)

    total_calls = len(SAMPLES) * REPEATS
    print("模型 %s ｜ 超时 %.0f 秒 ｜ %d 个样本 × %d 次 = %d 次调用"
          % (MODEL, TIMEOUT_SECONDS, len(SAMPLES), REPEATS, total_calls))
    print("提示词版本 %s ｜ 统计分母 %d（plan.md:56）" % (PROMPT_VERSION, STAT_DENOMINATOR))
    print("-" * 60)

    rows = []
    n = 0
    for sample in SAMPLES:
        for i in range(REPEATS):
            n += 1
            r = call_once(sample, TIMEOUT_SECONDS)
            if r["error"]:
                ok, reason = False, r["error"]
            else:
                ok, reason = validate(r["content"], sample)
            row = {
                "runNo": n,
                "sampleId": sample["id"],
                "startedAt": r["startedAt"],
                "elapsedSec": r["elapsedSec"],
                "httpStatus": r["httpStatus"],
                "promptTokens": r["promptTokens"],
                "completionTokens": r["completionTokens"],
                "totalTokens": r["totalTokens"],
                "validateOk": ok,
                "failReason": reason,
                "error": r["error"],
                "detail": r["detail"],
                "content": r["content"],
            }
            rows.append(row)
            print("  [%2d/%d] %s  %6.2fs  %s  %s"
                  % (n, total_calls, sample["id"], r["elapsedSec"],
                     "通过" if ok else "不通过", reason))

    # 单独模拟超时与非 JSON，不混入 21 次统计（plan.md:51 / README.md:18）
    sim_timeout = call_once(SAMPLES[0], timeout=0.001)
    sim_nonjson_ok, sim_nonjson_reason = validate("这不是 JSON，只是一段普通文字。", SAMPLES[0])

    # ---- 写产出 ----
    csv_fields = ["runNo", "sampleId", "startedAt", "elapsedSec", "httpStatus",
                  "promptTokens", "completionTokens", "totalTokens",
                  "validateOk", "failReason", "error", "detail"]
    with open(EVIDENCE / "raw_runs.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)

    with open(EVIDENCE / "raw_responses.jsonl", "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with open(BASE / "prompt.md", "w", encoding="utf-8") as f:
        f.write("# SP-01 提示词\n\n")
        f.write("- promptVersion：`%s`\n" % PROMPT_VERSION)
        f.write("- 模型：`%s`（可在 run_sp01.py 顶部改）\n" % MODEL)
        f.write("- 接口：`%s`\n" % API_URL)
        f.write("- 实测日期：%s\n" % datetime.now().strftime("%Y-%m-%d"))
        f.write("- 密钥：仅环境变量 `DEEPSEEK_API_KEY`，不在本文件留痕\n\n")
        f.write("## System prompt\n\n```text\n")
        f.write(SYSTEM_PROMPT)
        f.write("\n```\n\n")
        f.write("## User message 模板\n\n")
        f.write("把题干、参考答案、题目满分、评分点（rubricId / score / description）、")
        f.write("学生答案组成 JSON 字符串作为 user 消息；样本全文见 `run_sp01.py` 的 `SAMPLES`。\n")

    all_times = [r["elapsedSec"] for r in rows]
    stat = rows[:STAT_DENOMINATOR]
    stat_times = [r["elapsedSec"] for r in stat]
    pass_all = sum(1 for r in rows if r["validateOk"])
    pass_stat = sum(1 for r in stat if r["validateOk"])
    timeouts = sum(1 for r in rows if r["error"] == "TIMEOUT")
    timeouts_stat = sum(1 for r in stat if r["error"] == "TIMEOUT")

    def num(v):
        return v if isinstance(v, (int, float)) else 0

    tok_in = sum(num(r["promptTokens"]) for r in rows)
    tok_out = sum(num(r["completionTokens"]) for r in rows)
    tok_total = sum(num(r["totalTokens"]) for r in rows)

    fail_count = {}
    for r in rows:
        if not r["validateOk"]:
            key = r["failReason"]
            fail_count[key] = fail_count.get(key, 0) + 1

    price_in = os.environ.get("DEEPSEEK_PRICE_INPUT_PER_MTOK", "").strip()
    price_out = os.environ.get("DEEPSEEK_PRICE_OUTPUT_PER_MTOK", "").strip()

    def to_price(s):
        """单价必须是数字；填了示例文字/中文时按未提供处理，不让脚本中断。"""
        try:
            v = float(s)
            return v if v >= 0 else None
        except (TypeError, ValueError):
            return None

    pin, pout = to_price(price_in), to_price(price_out)
    if pin is not None and pout is not None:
        total_cost = tok_in / 1_000_000 * pin + tok_out / 1_000_000 * pout
        avg_cost = total_cost / total_calls
        cost_lines = [
            "单价来源：运行前由用户在环境变量填 DeepSeek 官网当日定价（每百万 token）。",
            "  输入单价 %s / 百万 token，输出单价 %s / 百万 token" % (price_in, price_out),
            "  总费用 %s，单次平均费用 %s" % (round(total_cost, 6), round(avg_cost, 6)),
        ]
    else:
        cost_lines = [
            "单价未提供或不是数字，费用待估算：本脚本不预置价格数字。",
            "  计算式：费用 = 输入token/1,000,000 × 输入单价 + 输出token/1,000,000 × 输出单价",
            "  单价以 DeepSeek 官网当日定价为准；填入 DEEPSEEK_PRICE_INPUT_PER_MTOK /",
            "  DEEPSEEK_PRICE_OUTPUT_PER_MTOK 后重跑本脚本即可得到单次平均费用。",
        ]

    lines = []
    lines.append("SP-01 实测结果（由 run_sp01.py 自动生成）")
    lines.append("生成时间：%s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("模型：%s ｜ 提示词版本：%s ｜ 客户端超时：%.0f 秒（ADR-003:36）" % (MODEL, PROMPT_VERSION, TIMEOUT_SECONDS))
    lines.append("样本：3 个（S1 10分简答/2评分点、S2 20分论述/4评分点、S3 空答案），每个 7 次，共 %d 次（plan.md:48-49）" % total_calls)
    lines.append("")
    lines.append("=== 四项指标 ===")
    lines.append("结构校验通过率（全量 %d 次口径）：%d/%d = %.1f%%" % (total_calls, pass_all, total_calls, pass_all * 100.0 / total_calls))
    lines.append("结构校验通过率（plan.md:56 的 %d 次口径，取前 %d 次）：%d/%d = %.1f%%" % (STAT_DENOMINATOR, STAT_DENOMINATOR, pass_stat, STAT_DENOMINATOR, pass_stat * 100.0 / STAT_DENOMINATOR))
    lines.append("  目标：>= 90%%（20 次中 >= 18 次），来源 plan.md:56")
    lines.append("P95 延迟（%d 次口径，最近秩法 ceil(0.95*n)-1）：%s 秒" % (STAT_DENOMINATOR, p95(stat_times)))
    lines.append("P95 延迟（全量 %d 次口径，供参考）：%s 秒" % (total_calls, p95(all_times)))
    lines.append("  目标：<= 30 秒，来源 plan.md:57 / ADR-003:36")
    lines.append("超时率（全量 %d 次口径）：%d/%d = %.1f%%" % (total_calls, timeouts, total_calls, timeouts * 100.0 / total_calls))
    lines.append("超时率（%d 次口径）：%d/%d = %.1f%%" % (STAT_DENOMINATOR, timeouts_stat, STAT_DENOMINATOR, timeouts_stat * 100.0 / STAT_DENOMINATOR))
    lines.append("  目标：<= 5%，来源 plan.md:57；超时如实计数，不从分母剔除（本目录 README.md:16）")
    lines.append("单次费用估算：")
    for c in cost_lines:
        lines.append("  " + c)
    lines.append("")
    lines.append("=== token 合计（API usage 真实返回） ===")
    lines.append("输入 %d ｜ 输出 %d ｜ 合计 %d" % (tok_in, tok_out, tok_total))
    lines.append("")
    lines.append("=== 校验失败类型分布（ADR-003 第 4 条） ===")
    if fail_count:
        for k, v in sorted(fail_count.items(), key=lambda x: -x[1]):
            lines.append("  %s : %d 次" % (k, v))
    else:
        lines.append("  无失败")
    lines.append("")
    lines.append("=== 单独模拟（不混入上面 21 次统计，plan.md:51） ===")
    lines.append("  超时模拟：error=%s，耗时 %s 秒（把客户端超时降到 0.001 秒）" % (sim_timeout["error"], sim_timeout["elapsedSec"]))
    lines.append("  非 JSON 模拟：validateOk=%s，失败类别=%s" % (sim_nonjson_ok, sim_nonjson_reason))
    lines.append("")
    lines.append("=== 复核与口径说明 ===")
    lines.append("  分母取 20 次（plan.md:56）；第 21 次为备用样本，全量与 20 次两个口径均给出。")
    lines.append("  P95 用最近秩法；超时、解析失败、校验失败均如实计数（README.md:16）。")
    lines.append("  样本数、统计分母、P95 计算口径与费用来源由王麒博复核（README.md:19）。")
    lines.append("  数据文件：evidence/raw_runs.csv（摘要）、evidence/raw_responses.jsonl（21 条完整记录）。")
    lines.append("  本文件所有数字来自本次真实调用，未预置任何价格或阈值结果。")

    text = "\n".join(lines) + "\n"
    with open(EVIDENCE / "summary.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("-" * 60)
    print(text)
    print("产出已写入：prompt.md、evidence/raw_runs.csv、evidence/raw_responses.jsonl、evidence/summary.txt")


if __name__ == "__main__":
    main()
