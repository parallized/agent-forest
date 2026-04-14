#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


GLOBAL_MIN_AGENTS = 4
GLOBAL_MAX_AGENTS = 32

DEFAULT_CONFIG: dict[str, Any] = {
    "api": {
        "base_url": "",
        "api_key": None,
        "api_key_env": "AGENT_FOREST_API_KEY",
        "model": "grok-4.20-expert",
        "timeout_seconds": 120,
        "request_defaults": {},
    },
    "forest": {
        "min_agents": 4,
        "max_agents": 32,
        "default_agent_count": 4,
        "max_parallel_requests": 8,
    },
    "reporting": {
        "default_output_format": "markdown",
        "default_sections": [
            "Executive Summary",
            "Evidence",
            "Risks",
            "Recommendations",
            "Open Questions",
        ],
    },
    "prompts": {
        "system_prefix": (
            "You are one specialized member of a parallel agent forest. "
            "Work independently, stay within your assigned perspective, "
            "and produce a self-contained report."
        ),
        "report_contract": (
            "Return a concrete report with clear assumptions, direct conclusions, "
            "and supporting reasoning. Do not pretend to be the final synthesizer "
            "for the user."
        ),
    },
    "persona_library": {},
    "presets": {},
}


class ConfigError(ValueError):
    pass


class ApiError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a top-level JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "agent"


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    raw = load_json(config_path)
    config = deep_merge(DEFAULT_CONFIG, raw)
    validate_config(config)
    return config


def load_writable_config(path: str | Path) -> tuple[Path, dict[str, Any]]:
    config_path = Path(path)
    if config_path.exists():
        raw = load_json(config_path)
        return config_path, deep_merge(DEFAULT_CONFIG, raw)

    example_name = config_path.name.replace(".json", ".example.json")
    example_path = config_path.with_name(example_name)
    if example_path.exists():
        raw = load_json(example_path)
        return config_path, deep_merge(DEFAULT_CONFIG, raw)

    return config_path, copy.deepcopy(DEFAULT_CONFIG)


def validate_config(config: dict[str, Any]) -> None:
    api = config.get("api", {})
    forest = config.get("forest", {})
    reporting = config.get("reporting", {})

    if not api.get("base_url"):
        raise ConfigError("api.base_url is required")
    if not api.get("model"):
        raise ConfigError("api.model is required")
    if not isinstance(api.get("timeout_seconds"), int) or api["timeout_seconds"] <= 0:
        raise ConfigError("api.timeout_seconds must be a positive integer")
    if not isinstance(api.get("request_defaults"), dict):
        raise ConfigError("api.request_defaults must be an object")

    min_agents = forest.get("min_agents")
    max_agents = forest.get("max_agents")
    max_parallel_requests = forest.get("max_parallel_requests")

    if not isinstance(min_agents, int) or not isinstance(max_agents, int):
        raise ConfigError("forest.min_agents and forest.max_agents must be integers")
    if min_agents < GLOBAL_MIN_AGENTS or max_agents > GLOBAL_MAX_AGENTS or min_agents > max_agents:
        raise ConfigError("forest limits must stay within 4-32 agents")
    if not isinstance(max_parallel_requests, int) or max_parallel_requests <= 0:
        raise ConfigError("forest.max_parallel_requests must be a positive integer")

    sections = reporting.get("default_sections")
    if not isinstance(sections, list) or not sections or not all(isinstance(item, str) for item in sections):
        raise ConfigError("reporting.default_sections must be a non-empty array of strings")

    if not isinstance(config.get("persona_library"), dict):
        raise ConfigError("persona_library must be an object")
    if not isinstance(config.get("presets"), dict):
        raise ConfigError("presets must be an object")


def resolve_api_key(config: dict[str, Any]) -> str:
    api = config["api"]
    api_key = api.get("api_key")
    if api_key:
        return str(api_key)

    env_name = api.get("api_key_env")
    if env_name:
        env_value = os.environ.get(str(env_name))
        if env_value:
            return env_value

    raise ConfigError(
        "No API key configured. Set api.api_key or export the environment variable "
        f"{env_name!r}."
    )


def mask_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}...{secret[-4:]}"


def load_payload(args: argparse.Namespace) -> dict[str, Any]:
    sources = [bool(args.payload_file), bool(args.payload_json)]
    if sum(sources) != 1:
        raise ConfigError("Provide exactly one of --payload-file or --payload-json")

    if args.payload_file:
        payload = load_json(Path(args.payload_file))
    else:
        payload = json.loads(args.payload_json)

    if not isinstance(payload, dict):
        raise ConfigError("Payload must be a JSON object")
    return payload


def normalize_agent_entry(entry: Any) -> dict[str, Any]:
    if isinstance(entry, str):
        return {"persona_ref": entry}
    if not isinstance(entry, dict):
        raise ConfigError("Each agent entry must be an object or persona_ref string")
    return copy.deepcopy(entry)


def resolve_persona(config: dict[str, Any], persona_ref: str) -> dict[str, Any]:
    persona = config["persona_library"].get(persona_ref)
    if not persona:
        raise ConfigError(f"Unknown persona_ref: {persona_ref}")
    if not isinstance(persona, dict):
        raise ConfigError(f"persona_library.{persona_ref} must be an object")
    return copy.deepcopy(persona)


def resolve_agents(
    config: dict[str, Any], payload: dict[str, Any], preset_name: str | None
) -> list[dict[str, Any]]:
    raw_agents = payload.get("agents")

    if raw_agents is None:
        if not preset_name:
            raise ConfigError("Payload must include agents or specify a preset")
        preset = config["presets"].get(preset_name)
        if not preset:
            raise ConfigError(f"Unknown preset: {preset_name}")
        raw_agents = preset.get("agents", [])

    if not isinstance(raw_agents, list):
        raise ConfigError("Payload agents must be an array")

    resolved: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for item in raw_agents:
        entry = normalize_agent_entry(item)
        persona_ref = entry.pop("persona_ref", None)
        if persona_ref:
            agent = deep_merge(resolve_persona(config, str(persona_ref)), entry)
        else:
            agent = entry

        name = agent.get("name")
        role = agent.get("role")
        if not name or not role:
            raise ConfigError("Every resolved agent needs at least name and role")

        agent_id = agent.get("id") or slugify(str(name))
        if agent_id in seen_ids:
            raise ConfigError(f"Duplicate agent id/name detected: {agent_id}")
        seen_ids.add(agent_id)
        agent["id"] = agent_id

        resolved.append(agent)

    min_agents = config["forest"]["min_agents"]
    max_agents = config["forest"]["max_agents"]
    if not (min_agents <= len(resolved) <= max_agents):
        raise ConfigError(
            f"Resolved forest size must be between {min_agents} and {max_agents}; "
            f"got {len(resolved)}"
        )

    return resolved


def build_messages(
    config: dict[str, Any],
    payload: dict[str, Any],
    agent: dict[str, Any],
    agent_index: int,
    total_agents: int,
) -> list[dict[str, str]]:
    prompts = config["prompts"]
    report_sections = payload.get("report_sections") or config["reporting"]["default_sections"]
    output_format = payload.get("output_format") or config["reporting"]["default_output_format"]
    constraints = payload.get("constraints") or []
    context = payload.get("context")

    if not isinstance(report_sections, list) or not all(isinstance(item, str) for item in report_sections):
        raise ConfigError("report_sections must be an array of strings")
    if constraints and (not isinstance(constraints, list) or not all(isinstance(item, str) for item in constraints)):
        raise ConfigError("constraints must be an array of strings")
    if context is not None and not isinstance(context, str):
        raise ConfigError("context must be a string")

    system_chunks = [prompts.get("system_prefix", ""), prompts.get("report_contract", ""), agent.get("system_prompt", "")]
    system_content = "\n\n".join(chunk.strip() for chunk in system_chunks if chunk and chunk.strip())

    lines = [
        f"You are agent {agent_index} of {total_agents}.",
        "",
        "Agent profile:",
        f"- Name: {agent['name']}",
        f"- Role: {agent['role']}",
    ]

    if agent.get("persona"):
        lines.append(f"- Persona: {agent['persona']}")
    if agent.get("goal"):
        lines.append(f"- Goal: {agent['goal']}")

    lines.extend(
        [
            "",
            "Task:",
            payload["task"],
        ]
    )

    if context:
        lines.extend(["", "Shared context:", context])

    if constraints:
        lines.extend(["", "Constraints:"])
        lines.extend(f"- {item}" for item in constraints)

    lines.extend(["", f"Expected output format: {output_format}", "Required sections:"])
    lines.extend(f"- {section}" for section in report_sections)
    lines.extend(
        [
            "",
            "Write only your own report from your assigned perspective.",
            "Do not attempt to synthesize the entire forest.",
        ]
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "\n".join(lines).strip()},
    ]


def prepare_run(
    config: dict[str, Any], payload: dict[str, Any], preset_name: str | None
) -> dict[str, Any]:
    task = payload.get("task")
    if not isinstance(task, str) or not task.strip():
        raise ConfigError("Payload task must be a non-empty string")

    agents = resolve_agents(config, payload, preset_name)
    shared_model = payload.get("model") or config["api"]["model"]

    compiled_agents: list[dict[str, Any]] = []
    for index, agent in enumerate(agents, start=1):
        request_body = copy.deepcopy(config["api"]["request_defaults"])
        request_body["model"] = agent.get("model") or shared_model
        request_body["messages"] = build_messages(config, payload, agent, index, len(agents))

        if agent.get("temperature") is not None:
            request_body["temperature"] = agent["temperature"]

        compiled_agents.append(
            {
                "index": index,
                "id": agent["id"],
                "name": agent["name"],
                "role": agent["role"],
                "persona": agent.get("persona"),
                "goal": agent.get("goal"),
                "model": request_body["model"],
                "request_body": request_body,
            }
        )

    return {
        "preset": preset_name,
        "task": task,
        "forest_size": len(compiled_agents),
        "agents": compiled_agents,
    }


def decode_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
        return "\n".join(part.strip() for part in parts if part.strip()).strip()
    return json.dumps(content, ensure_ascii=False)


def parse_sse_response(raw: str) -> dict[str, Any]:
    content_parts: list[str] = []
    finish_reason = None
    usage = None

    for line in raw.splitlines():
        if not line.startswith("data:"):
            continue

        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue

        try:
            chunk = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ApiError("API returned invalid SSE JSON chunk") from exc

        usage = chunk.get("usage") or usage
        choices = chunk.get("choices") or []
        if not choices:
            continue

        first_choice = choices[0] or {}
        delta = first_choice.get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str) and content:
            content_parts.append(content)

        finish_reason = first_choice.get("finish_reason") or finish_reason

    joined_content = "".join(content_parts).strip()
    if not joined_content:
        raise ApiError("API SSE response did not contain message content")

    return {
        "content": joined_content,
        "raw_response": raw,
        "usage": usage,
        "finish_reason": finish_reason,
    }


def chat_completion_request(
    config: dict[str, Any], api_key: str, request_body: dict[str, Any]
) -> dict[str, Any]:
    api = config["api"]
    encoded_body = json.dumps(request_body).encode("utf-8")
    request = urllib.request.Request(
        api["base_url"],
        data=encoded_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=api["timeout_seconds"]) as response:
            content_type = response.headers.get("Content-Type", "")
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(str(exc.reason)) from exc

    if "text/event-stream" in content_type or raw.lstrip().startswith("data:"):
        return parse_sse_response(raw)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiError("API returned invalid JSON") from exc

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ApiError("API response did not contain choices")

    first_choice = choices[0] or {}
    message = first_choice.get("message") or {}
    content = decode_message_content(message.get("content", ""))

    if not content:
        raise ApiError("API response did not contain message content")

    return {
        "content": content,
        "raw_response": payload,
        "usage": payload.get("usage"),
        "finish_reason": first_choice.get("finish_reason"),
    }


def run_forest(config: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    api_key = resolve_api_key(config)
    started_at = time.time()
    max_workers = min(config["forest"]["max_parallel_requests"], len(plan["agents"]))
    results: list[dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(chat_completion_request, config, api_key, agent["request_body"]): agent
            for agent in plan["agents"]
        }

        for future in concurrent.futures.as_completed(future_map):
            agent = future_map[future]
            result = {
                "index": agent["index"],
                "id": agent["id"],
                "name": agent["name"],
                "role": agent["role"],
                "goal": agent.get("goal"),
                "model": agent["model"],
            }
            try:
                response = future.result()
                result.update(
                    {
                        "status": "succeeded",
                        "content": response["content"],
                        "finish_reason": response.get("finish_reason"),
                        "usage": response.get("usage"),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                result.update({"status": "failed", "error": str(exc)})
            results.append(result)

    results.sort(key=lambda item: item["index"])
    succeeded = sum(1 for item in results if item["status"] == "succeeded")
    failed = len(results) - succeeded

    return {
        "summary": {
            "preset": plan.get("preset"),
            "forest_size": plan["forest_size"],
            "succeeded_agents": succeeded,
            "failed_agents": failed,
            "duration_seconds": round(time.time() - started_at, 3),
        },
        "agents": results,
    }


def command_validate_config(args: argparse.Namespace) -> int:
    load_config(args.config)
    print(json.dumps({"status": "ok", "config": args.config}, ensure_ascii=False))
    return 0


def command_configure(args: argparse.Namespace) -> int:
    config_path, config = load_writable_config(args.config)
    changed = False

    if args.api_base:
        config["api"]["base_url"] = args.api_base
        changed = True
    if args.model:
        config["api"]["model"] = args.model
        changed = True
    if args.api_key is not None:
        config["api"]["api_key"] = args.api_key
        changed = True
    if args.clear_api_key:
        config["api"]["api_key"] = None
        changed = True
    if args.api_key_env:
        config["api"]["api_key_env"] = args.api_key_env
        changed = True

    if not changed:
        raise ConfigError("No config changes requested")

    validate_config(config)
    write_json(config_path, config)

    summary = {
        "status": "ok",
        "config": str(config_path),
        "api": {
            "base_url": config["api"]["base_url"],
            "model": config["api"]["model"],
            "api_key": mask_secret(config["api"].get("api_key")),
            "api_key_env": config["api"].get("api_key_env"),
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def command_list_presets(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    presets = []
    for name, preset in sorted(config["presets"].items()):
        presets.append(
            {
                "name": name,
                "description": preset.get("description", ""),
                "agent_count": len(preset.get("agents", [])),
            }
        )
    print(json.dumps({"presets": presets}, ensure_ascii=False, indent=2))
    return 0


def command_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    payload = load_payload(args)
    preset_name = args.preset or payload.get("preset")
    plan = prepare_run(config, payload, preset_name)

    if args.dry_run:
        output = {
            "summary": {
                "preset": plan.get("preset"),
                "forest_size": plan["forest_size"],
                "dry_run": True,
            },
            "agents": plan["agents"],
        }
    else:
        output = run_forest(config, plan)

    rendered = json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None)

    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)

    failed_agents = output.get("summary", {}).get("failed_agents", 0)
    succeeded_agents = output.get("summary", {}).get("succeeded_agents", plan["forest_size"])
    if not args.dry_run and succeeded_agents == 0 and failed_agents > 0:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent Forest executor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-config", help="Validate a config file")
    validate_parser.add_argument("--config", required=True, help="Path to the JSON config file")
    validate_parser.set_defaults(func=command_validate_config)

    configure_parser = subparsers.add_parser("configure", help="Persist provider settings into a config file")
    configure_parser.add_argument("--config", required=True, help="Path to the writable JSON config file")
    configure_parser.add_argument(
        "--api-base",
        "--base-url",
        "--api-base-route",
        dest="api_base",
        help="Chat completions endpoint URL",
    )
    configure_parser.add_argument(
        "--model",
        "--model-name",
        dest="model",
        help="Model name for the external agents",
    )
    api_key_group = configure_parser.add_mutually_exclusive_group()
    api_key_group.add_argument("--api-key", help="Persist a literal API key into the config file")
    api_key_group.add_argument(
        "--clear-api-key",
        action="store_true",
        help="Remove any literal API key from the config file",
    )
    configure_parser.add_argument(
        "--api-key-env",
        help="Environment variable name to prefer for the API key",
    )
    configure_parser.set_defaults(func=command_configure)

    presets_parser = subparsers.add_parser("list-presets", help="List configured presets")
    presets_parser.add_argument("--config", required=True, help="Path to the JSON config file")
    presets_parser.set_defaults(func=command_list_presets)

    run_parser = subparsers.add_parser("run", help="Execute a forest plan")
    run_parser.add_argument("--config", required=True, help="Path to the JSON config file")
    run_parser.add_argument("--payload-file", help="Path to a JSON payload file")
    run_parser.add_argument("--payload-json", help="Inline JSON payload")
    run_parser.add_argument("--preset", help="Preset name to use when payload omits agents")
    run_parser.add_argument("--output", help="Optional output file for the JSON result")
    run_parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON result")
    run_parser.add_argument("--dry-run", action="store_true", help="Compile requests without calling the API")
    run_parser.set_defaults(func=command_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, ApiError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
