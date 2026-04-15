#!/usr/bin/env python3
"""Memory maintenance job — run periodically via cron or APScheduler.

Usage:
    python -m kitchen_agent.scripts.memory_maintenance
    # or from project root:
    python -m kitchen_agent.scripts.memory_maintenance --chat-id default

Schedule in crontab (every 6 hours):
    0 */6 * * * cd /path/to/Karl && /path/to/venv/bin/python -m kitchen_agent.scripts.memory_maintenance >> /var/log/kitchen_memory.log 2>&1
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from kitchen_agent.storage.memory import run_memory_maintenance


def main():
    parser = argparse.ArgumentParser(description="Run kitchen agent memory maintenance")
    parser.add_argument("--chat-id", default="default")
    args = parser.parse_args()
    
    print(f"Running memory maintenance for chat_id={args.chat_id}...")
    run_memory_maintenance(args.chat_id)
    print("Done.")


if __name__ == "__main__":
    main()
