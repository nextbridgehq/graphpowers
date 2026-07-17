"""graphpowers CLI — the glue commands the skills call.

Usage:
  python -m bridge freshness [--root .] [--graph PATH]
  python -m bridge blast [FILE ...] [--depth 2] [--graph PATH]
  python -m bridge pack "task description" [--file F ...] [--budget 1200]
  python -m bridge drift BEFORE.json AFTER.json
  python -m bridge who-uses "NodeLabel" [--graph PATH]
  python -m bridge snapshot [--graph PATH] [--out PATH]

Exit codes: 0 ok/fresh/clean, 1 error, 2 stale graph / drift needs review /
high-risk blast — so shell scripts and hooks can branch on the result.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from . import blast_radius as br
from . import context_pack as cp
from . import drift as dr
from .freshness import check_freshness
from .graphio import DEFAULT_GRAPH_PATH, Graph, GraphSchemaError


def _load(graph_arg: str | None) -> Graph:
    return Graph.load(graph_arg or DEFAULT_GRAPH_PATH)


def cmd_freshness(args) -> int:
    try:
        rep = check_freshness(args.root, args.graph)
    except FileNotFoundError as e:
        if args.format == "json":
            import json
            print(json.dumps({"error": str(e), "fresh": None}))
        else:
            print(str(e))
        return 1

    if args.format == "json":
        import json
        print(json.dumps({
            "fresh": rep.fresh,
            "graph_path": str(rep.graph_path),
            "checked": rep.checked,
            "stale_files": rep.stale_files,
        }, indent=2))
    else:
        print(rep.summary())
    return 0 if rep.fresh else 2


def cmd_blast(args) -> int:
    g = _load(args.graph)
    files = args.files or br.git_changed_files()
    if not files:
        if args.format == "json":
            import json
            print(json.dumps({"risk": "NONE", "hits": [], "message": "no changed files"}))
        else:
            print("No changed files found (working tree clean and none given).")
        return 0
    rep = br.blast_radius(g, files, max_depth=args.depth)
    if args.format == "json":
        import json
        print(json.dumps(rep.to_dict(g), indent=2))
    else:
        print(br.render_markdown(g, rep))
    return 2 if rep.risk() == "HIGH" else 0


def cmd_pack(args) -> int:
    g = _load(args.graph)
    print(cp.build_pack(g, args.task, seed_files=args.file,
                        budget_tokens=args.budget))
    return 0


def cmd_drift(args) -> int:
    before = Graph.load(args.before)
    after = Graph.load(args.after)
    rep = dr.diff(before, after)
    if args.format == "json":
        import json
        print(json.dumps(rep.to_dict(before, after), indent=2))
    else:
        print(dr.render_markdown(before, after, rep))
    return 0 if rep.clean else 2


def cmd_whouses(args) -> int:
    from . import lookup
    g = _load(args.graph)
    rep = lookup.who_uses(g, args.node)
    print(lookup.render_markdown(g, rep))
    return 1 if rep.matched_node is None else 0


def cmd_upstream(args) -> int:
    from . import upstream
    rep = upstream.run_check(args.skills, args.superpowers,
                             args.graphify_help, extra_paths=args.also)
    print(upstream.render(rep))
    if rep.errors and not (rep.missing_skills or rep.missing_graphify):
        return 1
    return 2 if rep.broken else 0


def cmd_snapshot(args) -> int:
    src = Path(args.graph or DEFAULT_GRAPH_PATH)
    if src.is_dir():
        src = src / "graph.json"
    if not src.exists():
        print(f"No graph at {src}")
        return 1
    out = Path(args.out) if args.out else src.with_name(
        f"graph.snapshot-{time.strftime('%Y%m%d-%H%M%S')}.json")
    shutil.copyfile(src, out)
    print(f"Snapshot written: {out}")
    return 0


def cmd_guard(args) -> int:
    from . import guard
    g = _load(args.graph)
    touched = args.touched or br.git_changed_files()
    rep = guard.implementation_guard(g, args.planned, touched,
                                     max_depth=args.depth)
    if args.format == "json":
        import json
        print(json.dumps(rep.to_dict(g), indent=2))
    else:
        print(guard.render_markdown(g, rep))
    return 2 if rep.scope_creep else 0


def cmd_narrate(args) -> int:
    from . import narrate
    g = _load(args.graph)
    if args.community is not None:
        profiles = [narrate.profile_community(g, args.community)]
    else:
        profiles = narrate.all_communities(g)
    print(narrate.render_markdown(g, profiles))
    return 0


def cmd_parallel(args) -> int:
    from . import parallel as par
    import json as _json
    g = _load(args.graph)
    text = sys.stdin.read()
    try:
        tasks = par.parse_tasks(text)
    except (_json.JSONDecodeError, ValueError) as e:
        print(f"error: invalid task JSON from stdin: {e}", file=sys.stderr)
        return 1
    plan = par.parallel_safety(g, tasks, max_depth=args.depth)
    print(par.render_markdown(g, plan))
    return 2 if plan.conflicts else 0


def cmd_explain(args) -> int:
    from . import explain
    g = _load(args.graph)
    rep = explain.explain(g, args.term, budget=args.budget)
    print(explain.render_markdown(g, rep))
    return 0 if rep.matched_node else 1


def cmd_pack_feedback(args) -> int:
    from . import pack_feedback as pf
    data_dir = Path(args.data_dir) if args.data_dir else pf.DEFAULT_DATA_DIR

    if args.subcmd == "log":
        fb = pf.PackFeedback(
            task_id=args.task_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            pack_node_ids=args.pack_node or [],
            pack_was_sufficient=args.sufficient,
            extra_reads=args.extra_read or [],
            unused_nodes=args.unused_node or [],
        )
        pf.log_feedback(fb, data_dir=data_dir)
        print(f"Feedback logged for {args.task_id}.")
        return 0

    history = pf.load_history(data_dir=data_dir)
    if args.subcmd == "stats":
        print(pf.render_stats(history))
        return 0

    if args.subcmd == "weights":
        import json as _json
        from dataclasses import asdict
        w = pf.compute_weights(history)
        print(_json.dumps(asdict(w), indent=2))
        return 0

    return 1


def cmd_doctor(args) -> int:
    from . import doctor
    import platform
    import time
    
    rep = doctor.check(root=Path(args.root),
                       graph_path=Path(args.graph) if args.graph else None)
    
    # Calculate exit code exactly as the CLI would return it
    exit_code = 0 if rep.fully_ready or rep.ready else 2

    if args.json:
        import json
        from dataclasses import asdict
        
        # Build the final output dictionary
        d = {
            "schema_version": 1,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "exit_code": exit_code,
            "platform": platform.platform(),
            "python_executable": sys.executable,
        }
        # Merge in the report attributes
        d.update(asdict(rep))
        d["ready"] = rep.ready
        d["fully_ready"] = rep.fully_ready
        
        print(json.dumps(d, indent=2))
    else:
        print(doctor.render_markdown(rep))
        
    return exit_code


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="graphpowers",
        epilog="Exit codes: 0=ok, 1=error, 2=needs attention")
    p.add_argument("--explain-exit-code", action="store_true",
                   help="append a human-readable exit code explanation to output")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("freshness", help="is the graph up to date?")
    f.add_argument("--root", default=".")
    f.add_argument("--graph", default=None)
    f.add_argument("--format", choices=["markdown", "json"], default="markdown", help="output format")
    f.set_defaults(fn=cmd_freshness)

    b = sub.add_parser("blast", help="blast radius of changed files (bidirectional BFS along impact relations)")
    b.add_argument("files", nargs="*")
    b.add_argument("--depth", type=int, default=2)
    b.add_argument("--graph", default=None)
    b.add_argument("--format", choices=["markdown", "json"], default="markdown", help="output format")
    b.set_defaults(fn=cmd_blast)

    k = sub.add_parser("pack", help="context pack for a task")
    k.add_argument("task")
    k.add_argument("--file", action="append", default=[])
    k.add_argument("--budget", type=int, default=1200)
    k.add_argument("--graph", default=None)
    k.set_defaults(fn=cmd_pack)

    d = sub.add_parser("drift", help="diff two graph snapshots")
    d.add_argument("before")
    d.add_argument("after")
    d.add_argument("--format", choices=["markdown", "json"], default="markdown", help="output format")
    d.set_defaults(fn=cmd_drift)

    w = sub.add_parser("who-uses", help="reverse-dependency lookup for a node")
    w.add_argument("node", help="node label, e.g. 'Button' or 'login()'")
    w.add_argument("--graph", default=None)
    w.set_defaults(fn=cmd_whouses)

    u = sub.add_parser("upstream-check",
                       help="verify upstream contracts (skills, CLI flags)")
    u.add_argument("--skills", default="skills",
                   help="our skills directory to scan for references")
    u.add_argument("--superpowers", default=None,
                   help="path to a checkout of the superpowers repo")
    u.add_argument("--graphify-help", default=None,
                   help="file containing `graphify --help` output")
    u.add_argument("--also", action="append", default=[],
                   help="extra file/dir to scan for references (e.g. ci/)")
    u.set_defaults(fn=cmd_upstream)

    s = sub.add_parser("snapshot", help="save a timestamped copy of the graph")
    s.add_argument("--graph", default=None)
    s.add_argument("--out", default=None)
    s.set_defaults(fn=cmd_snapshot)

    gd = sub.add_parser("guard", help="check for scope creep during implementation")
    gd.add_argument("--planned", nargs="+", required=True,
                     help="files in the original plan")
    gd.add_argument("--touched", nargs="+", default=None,
                     help="files actually touched (default: git changed files)")
    gd.add_argument("--depth", type=int, default=2)
    gd.add_argument("--graph", default=None)
    gd.add_argument("--format", choices=["markdown", "json"], default="markdown", help="output format")
    gd.set_defaults(fn=cmd_guard)

    # --- narrate ---
    nr = sub.add_parser("narrate", help="community narratives (onboarding)")
    nr.add_argument("--community", type=int, default=None,
                     help="specific community ID (default: all)")
    nr.add_argument("--graph", default=None)
    nr.set_defaults(fn=cmd_narrate)

    # --- parallel ---
    pl = sub.add_parser("parallel",
                         help="parallel safety analysis (reads task JSON from stdin)")
    pl.add_argument("--depth", type=int, default=2)
    pl.add_argument("--graph", default=None)
    pl.set_defaults(fn=cmd_parallel)

    # --- explain ---
    ex = sub.add_parser("explain", help="unified concept explanation")
    ex.add_argument("term", help="concept to explain, e.g. 'login' or 'rate limiting'")
    ex.add_argument("--budget", type=int, default=800,
                     help="token budget for the context pack section")
    ex.add_argument("--graph", default=None)
    ex.set_defaults(fn=cmd_explain)

    # --- pack-feedback ---
    pf = sub.add_parser("pack-feedback", help="context pack quality feedback")
    pf_sub = pf.add_subparsers(dest="subcmd", required=True)

    pf_log = pf_sub.add_parser("log", help="log feedback for a pack")
    pf_log.add_argument("--task-id", required=True, dest="task_id")
    pf_log.add_argument("--sufficient", action="store_true", default=False)
    pf_log.add_argument("--insufficient", dest="sufficient",
                         action="store_false")
    pf_log.add_argument("--extra-read", action="append", default=[],
                         dest="extra_read")
    pf_log.add_argument("--unused-node", action="append", default=[],
                         dest="unused_node")
    pf_log.add_argument("--pack-node", action="append", default=[],
                         dest="pack_node")
    pf_log.add_argument("--data-dir", default=None, dest="data_dir")

    pf_stats = pf_sub.add_parser("stats", help="pack quality statistics")
    pf_stats.add_argument("--data-dir", default=None, dest="data_dir")

    pf_weights = pf_sub.add_parser("weights", help="current learned weights")
    pf_weights.add_argument("--data-dir", default=None, dest="data_dir")

    pf.set_defaults(fn=cmd_pack_feedback)

    # --- doctor ---
    doc = sub.add_parser("doctor", help="check prerequisites and project readiness")
    doc.add_argument("--root", default=".")
    doc.add_argument("--graph", default=None)
    doc.add_argument("--json", action="store_true", help="output raw JSON report")
    doc.set_defaults(fn=cmd_doctor)

    args = p.parse_args(argv)
    try:
        code = args.fn(args)
    except GraphSchemaError as e:
        print(f"error: {e}", file=sys.stderr)
        code = 1
    except FileNotFoundError as e:
        print(f"error: {e} - run `graphify .` to build the graph first.",
              file=sys.stderr)
        code = 1
    except BrokenPipeError:
        return 0  # output piped to head/less that closed early

    if getattr(args, 'explain_exit_code', False):
        explanations = {
            0: "Exit 0: OK — no issues found.",
            1: "Exit 1: ERROR — command could not complete (missing file, bad input, node not found).",
            2: "Exit 2: NEEDS ATTENTION — stale graph / drift detected / high risk / scope creep / conflicts.",
        }
        print(f"\n---\n{explanations.get(code, f'Exit {code}: unknown')}", file=sys.stderr)

    return code


if __name__ == "__main__":
    sys.exit(main())
