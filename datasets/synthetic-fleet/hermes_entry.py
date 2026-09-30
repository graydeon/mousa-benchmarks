"""Invoke native Hermes with isolated MCP/memory settings and tool receipts."""

import argparse
import json
from pathlib import Path
import sys
import threading


def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("--mousa", required=True)
    parser.add_argument("--store", required=True)
    parser.add_argument("--mcp-log", type=Path, required=True)
    args, cli_args = parser.parse_known_args()
    from hermes_cli.main import main as native_main
    import hermes_cli.config as config
    original_load = config.load_config

    def load_for_benchmark():
        values = original_load()
        values["mcp_servers"] = {"mousa": {"command": args.mousa, "args": ["-store", args.store, "mcp", "--caller", "cli", "--source", "fleet"]}}
        values["memory"] = dict(values.get("memory") or {}, memory_enabled=False, user_profile_enabled=False)
        values["agent"] = dict(values.get("agent") or {}, max_turns=12)
        return values

    config.load_config = load_for_benchmark
    config.load_config_readonly = load_for_benchmark
    from tools import mcp_tool_handlers
    original_factory = mcp_tool_handlers._make_tool_handler
    lock = threading.Lock()

    def recording_factory(server_name, tool_name, timeout):
        handler = original_factory(server_name, tool_name, timeout)
        def invoke(arguments, **kwargs):
            result = handler(arguments, **kwargs)
            with lock, args.mcp_log.open("a", encoding="utf-8") as receipt:
                receipt.write(json.dumps({"server": server_name, "tool": tool_name, "arguments": arguments, "result": result}) + "\n")
            return result
        return invoke

    mcp_tool_handlers._make_tool_handler = recording_factory
    from tools.mcp_tool_discovery import discover_mcp_tools
    if not discover_mcp_tools(["mousa"]):
        raise RuntimeError("Mousa MCP discovery failed before inference")
    sys.argv = ["hermes"] + cli_args
    native_main()


if __name__ == "__main__":
    main()
