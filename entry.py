#!/usr/bin/env python3
"""
Unified entry point for the Autopilot agent binary.

When frozen by PyInstaller, this script provides both the daemon and CLI
commands in a single executable. The Rust backend spawns this binary with
appropriate subcommands.

Usage:
    autopilot-agent              → Run daemon (watchdog)
    autopilot-agent undo ...     → Run undo CLI
    autopilot-agent settings ... → Run settings CLI
    autopilot-agent rules ...    → Run rules engine CLI
"""

import sys
import runpy

# Explicit imports so PyInstaller includes these modules
import main
import undo
import settings
import rules_engine
import classifier
import organizer
import notifier
import config
import embedding_classifier


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("undo", "settings", "rules"):
        cmd = sys.argv.pop(1)
        runpy.run_module(cmd, run_name="__main__")
    else:
        runpy.run_module("main", run_name="__main__")


if __name__ == "__main__":
    main()
