#!/usr/bin/env python3
"""CLI entry point for running the Combined Lights simulation server."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from simulation.server import run_server
from simulation.sim_coordinator import SimConfig


def main():
    parser = argparse.ArgumentParser(description="Combined Lights Simulation Server")
    
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8091, help="Port to bind to")
    parser.add_argument("--breakpoints", default="30,60,90", help="Comma-separated breakpoints")
    
    args = parser.parse_args()
    
    breakpoints = [int(x.strip()) for x in args.breakpoints.split(",")]
    config = SimConfig(breakpoints=breakpoints)
    
    print(f"""
╔════════════════════════════════════════════════╗
║      Combined Lights Simulation Server         ║
╠════════════════════════════════════════════════╣
║  URL: http://{args.host}:{args.port:<5}                     ║
║  Breakpoints: {str(breakpoints):<30} ║
╚════════════════════════════════════════════════╝
""")
    
    run_server(host=args.host, port=args.port, config=config)


if __name__ == "__main__":
    main()
