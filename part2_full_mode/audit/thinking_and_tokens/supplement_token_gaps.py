from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys

from tokenizers import Tokenizer

AUDIT = Path(__file__).resolve().parent
HOME = Path.home()
sys.path.insert(0, str(AUDIT / "deps"))
import zstandard

JST = timezone(timedelta(hours=9))
LEDGER_PATH = AUDIT / "tokens_supplement.json"
FIELDS = ("non_cached_input", "cache_read", "cache_write", "output", "reasoning", "total")
DEEP_TOKENIZER_SOURCE = "https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/tokenizer.json"
QWEN_TOKENIZER_SOURCE = "https://huggingface.co/Qwen/Qwen-tokenizer/blob/main/tokenizer.json"


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def count(tokenizer, text):
    return len(tokenizer.encode(text, add_special_tokens=False).ids)


def tokenizer_evidence(filename, url):
    path = AUDIT / "deps" / filename
    return Tokenizer.from_file(str(path)), {
        "file": f"deps/{filename}",
        "source": url,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def deepseek_usage(entry, tokenizer):
    total = 0
    nonempty = 0
    records = []
    path = Path(entry["source"])
    with path.open("rb") as file, zstandard.ZstdDecompressor().stream_reader(
        file, read_across_frames=True
    ) as reader:
        for number, line in enumerate(io.TextIOWrapper(reader, encoding="utf-8"), 1):
            event = json.loads(line)
            if event["type"] != "assistant/message":
                continue
            data = event["data"]
            blocks = [
                block["text"] for block in data["message"]["content"] if block["type"] == "reasoning"
            ]
            stream = [
                block.get("text", "")
                for item in data["stream"]
                if (block := item.get("chunk", {}).get("block", {})).get("type") == "reasoning"
            ]
            assert "".join(blocks) == "".join(stream)
            assert data["message"]["source"]["model"] == "deepseek-flash"
            estimate = sum(count(tokenizer, block) for block in blocks)
            nonempty += bool(estimate)
            total += estimate
            assert estimate <= data["usage"]["outputTokens"]
            records.append({"line": number, "seq": event["seq"], "reasoning": estimate,
                            "output": data["usage"]["outputTokens"]})
    assert len(records) == entry["usage_events"]
    assert sum(item["output"] for item in records) == entry["output"]
    return total, nonempty, records


def qwen_usage(tokenizer):
    project = HOME / ".qoder-cn/projects/REPO-part2-full-exam-rooms-P2-10-qwen-qoder"
    session = "d65221a8-0f42-4bc3-bfc6-2b4e555404d9"
    start = datetime(2026, 11, 20, 1, 2, tzinfo=JST)
    end = datetime(2026, 11, 20, 2, 48, tzinfo=JST)
    seen = set()
    groups = {}
    for path in [project / (session + ".jsonl"), *sorted((project / session).rglob("*.jsonl"))]:
        with path.open(encoding="utf-8") as file:
            for line in file:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") != "assistant" or not event.get("timestamp"):
                    continue
                time = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                identity = event.get("uuid") or line
                if not start <= time < end or identity in seen:
                    continue
                seen.add(identity)
                message = event["message"]
                message_id = message.get("id") or identity
                for block in message.get("content", []):
                    if not isinstance(block, dict) or block.get("type") != "thinking":
                        continue
                    if text := block.get("thinking"):
                        groups.setdefault(message_id, set()).add(text)

    # A persisted message can contain snapshots of the same streamed prefix.
    blocks = [
        text for versions in groups.values()
        for text in versions if not any(other != text and other.startswith(text) for other in versions)
    ]
    return sum(count(tokenizer, text) for text in blocks), len(blocks), len(seen)


def doubao_usage(tokenizer):
    path = next((HOME / ".marscode/logs/2026-11-20").rglob("051248-755*.log"))
    marker = "lite/get_messages response:"
    session = "6afa5cbb7a371afb4f0d910c"
    with path.open(encoding="utf-8") as file:
        snapshots = [
            (number, json.loads(line.split(marker, 1)[1])["data"]["items"])
            for number, line in enumerate(file, 1) if marker in line and session in line
        ]
    assert len(snapshots) == 2 and snapshots[0][1] == snapshots[1][1]
    rows = []
    archive = ["# 豆包下半场 · TRAE 历史记录中的 Thinking\n",
               "来源为同一聊天历史的 get_messages 响应。按原始轮次与 plan_item 顺序保存已记录的 Thinking。\n"]
    for item in snapshots[0][1]:
        time = datetime.fromtimestamp(item["created_at"], JST)
        if item["role"] != "assistant" or time.date().isoformat() != "2026-11-19":
            continue
        plans = [message["plan_item"] for message in json.loads(item["content"])["messages"]]
        usage = json.loads(item["token_usage"])
        context = json.loads(item["context_usage"])
        archived = []
        output_proxy = 0
        generated = set()
        for index, plan in enumerate(plans, 1):
            tool = plan.get("tool_call_info") or {}
            reason = plan.get("reasoning_content") or ""
            thought = plan.get("thought") or ""
            timing = (plan.get("timing") or {}).get("generated_at_ms")
            if timing:
                generated.add(timing)
            if reason:
                archived.append((index, reason))
            output_proxy += count(tokenizer, thought)
            if tool.get("name"):
                output_proxy += count(tokenizer, tool["name"] + json_text(tool.get("params") or {}))
        reasoning_proxy = sum(count(tokenizer, text) for _, text in archived)
        last_recorded = count(tokenizer, archived[-1][1])
        assert last_recorded and usage["reasoning_tokens"]
        scale = usage["reasoning_tokens"] / last_recorded
        estimate_reasoning = round(reasoning_proxy * scale)
        estimate_output = estimate_reasoning + output_proxy
        ending = usage["prompt_tokens"]
        baseline = sum(x["estimate_included_tokens"] for x in context["token_usage_by_display_type"])
        assert 0 < baseline < ending
        slots = len(generated)
        low_history = round((slots - 1) * (baseline + ending) / 2 + ending)
        retained_history = slots * ending
        input_scenario = round((low_history + retained_history) / 2)
        archive.extend([f"## {time:%H:%M:%S} JST\n"])
        archive.extend(f"### Thinking {index}\n\n````text\n{text}\n````\n" for index, text in archived)
        rows.append({
            "message_id": item["message_id"], "time_jst": time.isoformat(), "status": item["status"],
            "native_last_invocation": usage, "indexed_context_estimate": baseline,
            "plan_items": len(plans), "distinct_generated_timestamps": slots,
            "thinking_text_blocks": len(archived),
            "proxy_reasoning_tokens": reasoning_proxy, "proxy_non_reasoning_output": output_proxy,
            "last_reasoning_proxy": last_recorded, "reasoning_calibration": scale,
            "reasoning_estimate": estimate_reasoning, "output_estimate": estimate_output,
            "input_linear_growth_scenario": low_history,
            "input_constant_terminal_scenario": retained_history, "input_midpoint_scenario": input_scenario,
        })
    assert [row["status"] for row in rows] == ["failed", "failed", "completed"]
    assert all(row["native_last_invocation"]["prompt_tokens_total"] == 0 and
               row["native_last_invocation"]["completion_tokens_total"] == 0 for row in rows)
    return path, [number for number, _ in snapshots], rows, "\n".join(archive)


def main():
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    contestants = ledger["contestants"]
    ds, ds_evidence = tokenizer_evidence("deepseek_v41_flash_tokenizer.json", DEEP_TOKENIZER_SOURCE)
    qwen, qwen_evidence = tokenizer_evidence("qwen_public_tokenizer.json", QWEN_TOKENIZER_SOURCE)

    dsh_count, nonempty, dsh_rows = deepseek_usage(contestants["deepseek"], ds)
    qwen_count, qwen_blocks, qwen_records = qwen_usage(qwen)
    trae_path, trae_lines, doubao_rows, archive = doubao_usage(qwen)
    assert qwen_count <= 209529

    dsh = contestants["deepseek"]
    dsh.update(reasoning=dsh_count, reasoning_status="estimated_from_saved_text",
               reasoning_note="官方 V4.1 Flash 分词器逐段重算。216 个响应中 135 个有非空推理正文；正文与流式记录一致。空块和服务端未保存内容不做补写。")

    qwen_entry = contestants["qwen"]
    qwen_entry.update(non_cached_input=1837944, cache_read=20746996, output=209529,
                      reasoning=qwen_count, total=22794469, cache_write=None,
                      status="platform_day_aggregate_used_as_session_proxy",
                      usage_scope="用户提供的千问平台截图，11-20 按天按模型汇总；截图未展示时区、会话 ID 或完整模型名。",
                      field_status={
                          "non_cached_input": "measured_day", "cache_read": "measured_day",
                          "output": "measured_day", "total": "measured_day",
                          "reasoning": "estimated_session_from_saved_text",
                          "cache_write": "not_separately_reported",
                      },
                      ui_status="user_supplied_day_aggregate",
                      ui_evidence="qwen_token_plan_20261120.png",
                      note="采用用户确认的 Qwen 用量截图作为该场代理；可能包含同模型当日其他调用。缓存写入没有单列，已包含或无法从未缓存输入进一步拆分，不填零。")
    assert qwen_entry["non_cached_input"] + qwen_entry["cache_read"] + qwen_entry["output"] == qwen_entry["total"]

    native = [row["native_last_invocation"] for row in doubao_rows]
    exact = {
        "non_cached_input": sum(row["prompt_tokens"] - row["cache_read_input_tokens"] -
                                row["cache_creation_input_tokens"] for row in native),
        "cache_read": sum(row["cache_read_input_tokens"] for row in native),
        "cache_write": sum(row["cache_creation_input_tokens"] for row in native),
        "output": sum(row["completion_tokens"] for row in native),
        "reasoning": sum(row["reasoning_tokens"] for row in native),
        "total": sum(row["total_tokens"] for row in native),
    }
    estimate_input = sum(row["input_midpoint_scenario"] for row in doubao_rows)
    estimate_output = sum(row["output_estimate"] for row in doubao_rows)
    estimate_reason = sum(row["reasoning_estimate"] for row in doubao_rows)
    # The only cache evidence is the three measured invocations. Applying their
    # pooled hit fraction to the estimates is a scenario, not measured usage.
    native_input = exact["non_cached_input"] + exact["cache_read"] + exact["cache_write"]
    assumption_fraction = exact["cache_read"] / native_input
    estimate_read = round(estimate_input * assumption_fraction)
    estimate = dict(non_cached_input=estimate_input - estimate_read, cache_read=estimate_read,
                    cache_write=0, output=estimate_output, reasoning=estimate_reason,
                    total=estimate_input + estimate_output)
    assert 0 < estimate_reason <= estimate_output
    assert exact["total"] == sum(exact[key] for key in FIELDS if key not in ("total", "reasoning"))
    assert estimate["total"] == sum(estimate[key] for key in FIELDS if key not in ("total", "reasoning"))

    doubao = contestants["doubao"]
    doubao.update(
        source=f"{trae_path}:{trae_lines[0]} (duplicate at line {trae_lines[1]})",
        status="measured_last_invocations_and_estimated_session",
        field_status={key: "estimated_session" for key in FIELDS},
        **estimate,
        actual_last_invocations={"count": len(native), **exact},
        planning_scenarios_total=[
            sum(row[key] for row in doubao_rows) + estimate_output
            for key in ("input_linear_growth_scenario", "input_constant_terminal_scenario")
        ],
        ui_status="TRAE history records have per-round last-invocation usage; cumulative fields are zero placeholders",
        thinking_export_status="full recorded plan-item Thinking text available including first interrupted round",
        thinking_raw_export="doubao_trae_logged_thinking.md",
        estimate_note="生成时间戳作为请求次数代理；取上下文从索引估值到实测末笔线性增长与全程持平两种场景的中点。缓存按三笔实测的合计比例推估，缓存写入按该情景设零。输出由原文与工具参数代理分词，推理部分以每轮末笔比率校准。场景差异不代表统计置信区间。",
    )
    ledger["warning"] = (
        "known_totals_only excludes Qwen (day scope) and Doubao (estimated session). "
        "Reasoning estimates are included in output, never added to total. No costs are recorded."
    )
    for entry in (dsh, qwen_entry, doubao):
        entry["supplement_evidence"] = "token_gap_evidence.json"

    evidence = {
        "deepseek": {"tokenizer": ds_evidence, "nonempty_reasoning_responses": nonempty,
                     "reasoning_estimate": dsh_count, "source": dsh["source"], "responses": dsh_rows},
        "qwen": {"tokenizer_proxy": qwen_evidence, "reasoning_estimate": qwen_count,
                 "assistant_records": qwen_records, "deduplicated_thinking_blocks": qwen_blocks,
                 "window_jst": "2026-11-20 01:02–02:47 (inclusive minute)",
                 "screenshot_cache_hit_display_percent": 91.9},
        "doubao": {"tokenizer_proxy": qwen_evidence, "source": str(trae_path),
                   "matching_history_log_lines": trae_lines, "rounds": doubao_rows,
                   "actual_sum": exact, "estimate": estimate,
                   "assumed_cache_read_fraction": assumption_fraction},
    }
    save_json(AUDIT / "token_gap_evidence.json", evidence)
    (AUDIT / "doubao_trae_logged_thinking.md").write_text(archive, encoding="utf-8")
    save_json(LEDGER_PATH, ledger)
    print(json_text({"DSH": (dsh_count, nonempty), "Qwen": (qwen_count, qwen_blocks, qwen_records),
                     "Doubao": (estimate, exact, doubao["planning_scenarios_total"])}))


if __name__ == "__main__":
    main()
