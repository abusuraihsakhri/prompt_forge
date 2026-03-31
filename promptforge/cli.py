"""
CLI interface for PromptForge.

Usage:
    promptforge optimize <file_or_text> --model claude --aggression moderate
    promptforge compare <file_or_text>
    promptforge stats <file_or_text>
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from promptforge.core.pipeline import optimize


# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_DARK = "\033[48;5;236m"


LOGO = f"""
{Colors.CYAN}{Colors.BOLD}
  ╔═══════════════════════════════════════════╗
  ║   ⚡ PromptForge — Token Optimizer ⚡     ║
  ║   Semantic compression for LLMs           ║
  ╚═══════════════════════════════════════════╝
{Colors.RESET}"""

MODELS = ["chatgpt", "claude", "gemini"]


def _read_input(source: Optional[str] = None) -> str:
    """Read prompt from file, argument, or stdin."""
    if source:
        path = Path(source)
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
        return source

    if not sys.stdin.isatty():
        return sys.stdin.read()

    print(f"{Colors.YELLOW}Enter prompt (Ctrl+D / Ctrl+Z to finish):{Colors.RESET}")
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    return "\n".join(lines)


def _print_result(result, show_original: bool = False):
    """Pretty-print an optimization result."""
    c = Colors

    if show_original:
        print(f"\n{c.DIM}{'─' * 50}")
        print(f"  ORIGINAL ({result.original_tokens} tokens)")
        print(f"{'─' * 50}{c.RESET}")
        print(result.original)

    print(f"\n{c.GREEN}{c.BOLD}{'─' * 50}")
    print(f"  OPTIMIZED — {result.model.upper()} ({result.optimized_tokens} tokens)")
    print(f"{'─' * 50}{c.RESET}")
    print(result.optimized)

    # Metrics bar
    print(f"\n{c.CYAN}{'─' * 50}")
    print("  📊 Metrics")
    print(f"{'─' * 50}{c.RESET}")
    print(f"  Tokens:   {result.original_tokens} → {result.optimized_tokens} "
          f"({c.GREEN}-{result.tokens_saved}{c.RESET})")
    print(f"  Savings:  {c.GREEN}{c.BOLD}{result.savings_percent:.1f}%{c.RESET}")
    print(f"  Ratio:    {result.compression_ratio:.2f}x")
    print(f"  Cost:     ${result.original_cost_estimate:.6f} → "
          f"${result.optimized_cost_estimate:.6f} "
          f"({c.GREEN}-${result.cost_saved:.6f}{c.RESET})")
    print(f"  Time:     {result.processing_time_ms:.1f}ms")

    if result.warnings:
        print(f"\n  {c.YELLOW}⚠ Warnings:{c.RESET}")
        for w in result.warnings:
            print(f"    {c.YELLOW}• {w}{c.RESET}")


def cmd_optimize(args):
    """Handle the 'optimize' subcommand."""
    text = _read_input(args.input)

    if not text.strip():
        print(f"{Colors.RED}Error: No input provided.{Colors.RESET}")
        sys.exit(1)

    result = optimize(
        text,
        model=args.model,
        aggressiveness=args.aggression,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_result(result, show_original=not args.quiet)

    if args.output:
        Path(args.output).write_text(result.optimized, encoding="utf-8")
        print(f"\n{Colors.GREEN}✓ Saved to {args.output}{Colors.RESET}")


def cmd_compare(args):
    """Handle the 'compare' subcommand — optimize for all 3 models."""
    text = _read_input(args.input)

    if not text.strip():
        print(f"{Colors.RED}Error: No input provided.{Colors.RESET}")
        sys.exit(1)

    print(LOGO)
    print(f"{Colors.DIM}Original prompt ({len(text)} chars):{Colors.RESET}")
    preview = text[:200] + ("..." if len(text) > 200 else "")
    print(f"  {preview}\n")

    results = {}
    for model in MODELS:
        result = optimize(text, model=model)
        results[model] = result

    # Comparison table
    c = Colors
    print(f"\n{c.BOLD}{'═' * 60}")
    print("  📊 Cross-Platform Comparison")
    print(f"{'═' * 60}{c.RESET}")
    print(f"  {'Model':<12} {'Original':>10} {'Optimized':>10} "
          f"{'Saved':>8} {'Savings':>10} {'Cost Saved':>12}")
    print(f"  {'─' * 58}")

    for model in MODELS:
        r = results[model]
        color = {
            "chatgpt": Colors.GREEN,
            "claude": Colors.MAGENTA,
            "gemini": Colors.BLUE,
        }.get(model, Colors.WHITE)
        print(f"  {color}{model:<12}{c.RESET} "
              f"{r.original_tokens:>10,} "
              f"{r.optimized_tokens:>10,} "
              f"{r.tokens_saved:>8,} "
              f"{c.GREEN}{r.savings_percent:>9.1f}%{c.RESET} "
              f"{c.GREEN}${r.cost_saved:>10.6f}{c.RESET}")

    # Print each result
    for model in MODELS:
        print(f"\n{'━' * 60}")
        _print_result(results[model])


def cmd_stats(args):
    """Handle the 'stats' subcommand — token counts without optimization."""
    text = _read_input(args.input)

    if not text.strip():
        print(f"{Colors.RED}Error: No input provided.{Colors.RESET}")
        sys.exit(1)

    print(LOGO)

    c = Colors
    print(f"{c.BOLD}  Token Count Analysis{c.RESET}")
    print(f"  {'─' * 40}")
    print(f"  Text length:  {len(text):,} characters")
    print(f"  Word count:   {len(text.split()):,} words")
    print()

    for model in MODELS:
        result = optimize(text, model=model)
        color = {
            "chatgpt": Colors.GREEN,
            "claude": Colors.MAGENTA,
            "gemini": Colors.BLUE,
        }.get(model, Colors.WHITE)
        print(f"  {color}{model.upper():<12}{c.RESET} "
              f"{result.original_tokens:>8,} tokens  "
              f"→ est. ${result.original_cost_estimate:.6f} input cost")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="promptforge",
        description="⚡ PromptForge — Semantic Prompt Optimizer for LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  promptforge optimize "Your prompt here" --model claude
  promptforge optimize input.txt --model chatgpt --aggression aggressive
  promptforge compare "Your prompt here"
  promptforge stats prompt.txt
  cat prompt.txt | promptforge optimize --model gemini
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- optimize ---
    opt_parser = subparsers.add_parser(
        "optimize", help="Optimize a prompt for a specific model"
    )
    opt_parser.add_argument(
        "input", nargs="?", default=None,
        help="Prompt text or path to a .txt file (reads stdin if omitted)"
    )
    opt_parser.add_argument(
        "-m", "--model", default="claude", choices=MODELS,
        help="Target LLM platform (default: claude)"
    )
    opt_parser.add_argument(
        "-a", "--aggression", default=None,
        choices=["conservative", "moderate", "aggressive"],
        help="Compression aggressiveness (default: model-specific)"
    )
    opt_parser.add_argument(
        "-o", "--output", default=None,
        help="Save optimized prompt to file"
    )
    opt_parser.add_argument(
        "--json", action="store_true",
        help="Output result as JSON"
    )
    opt_parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="Only show optimized output (no original)"
    )

    # --- compare ---
    cmp_parser = subparsers.add_parser(
        "compare", help="Compare optimization across all platforms"
    )
    cmp_parser.add_argument(
        "input", nargs="?", default=None,
        help="Prompt text or path to a .txt file"
    )

    # --- stats ---
    stats_parser = subparsers.add_parser(
        "stats", help="Show token counts per platform (no optimization)"
    )
    stats_parser.add_argument(
        "input", nargs="?", default=None,
        help="Prompt text or path to a .txt file"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "optimize": cmd_optimize,
        "compare": cmd_compare,
        "stats": cmd_stats,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
