import copy
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridge.graphio import Graph
from bridge import blast_radius as br
from bridge import context_pack as cp
from bridge import drift as dr
from bridge.freshness import check_freshness

FIXTURE = {
    "directed": False,
    "nodes": [
        {"id": "auth.py", "label": "auth.py", "source_file": "src/auth.py",
         "community": 0},
        {"id": "login", "label": "login()", "source_file": "src/auth.py",
         "source_location": "L10", "community": 0},
        {"id": "db.py", "label": "db.py", "source_file": "src/db.py",
         "community": 1},
        {"id": "query", "label": "query()", "source_file": "src/db.py",
         "source_location": "L5", "community": 1},
        {"id": "utils", "label": "utils.py", "source_file": "src/utils.py",
         "community": 2},
    ],
    "links": [
        {"source": "auth.py", "target": "login", "relation": "contains",
         "confidence": "EXTRACTED"},
        {"source": "login", "target": "query", "relation": "calls",
         "confidence": "EXTRACTED"},
        {"source": "db.py", "target": "query", "relation": "contains",
         "confidence": "EXTRACTED"},
        {"source": "login", "target": "utils", "relation": "imports",
         "confidence": "EXTRACTED"},
    ],
}


def graph():
    return Graph.from_node_link(copy.deepcopy(FIXTURE))


def test_load_and_indexes():
    g = graph()
    assert len(g.nodes) == 5
    assert g.label("login") == "login()"
    assert g.location("query") == "src/db.py:L5"
    assert g.degree["login"] == 3
    assert "src/auth.py" in g.by_file
    assert g.nodes_for_files(["src/auth.py"]) == ["auth.py", "login"]
    # suffix matching
    assert "query" in g.nodes_for_files(["db.py"])


def test_blast_radius():
    g = graph()
    rep = br.blast_radius(g, ["src/auth.py"], max_depth=2)
    ids = {h.node_id for h in rep.hits}
    # seeds + calls/imports neighbors (contains is not an impact relation)
    assert {"auth.py", "login", "query", "utils"} <= ids
    assert rep.risk() in {"LOW", "MEDIUM", "HIGH"}
    md = br.render_markdown(g, rep)
    assert "Blast radius" in md and "login()" in md


def test_blast_unmatched_file():
    g = graph()
    rep = br.blast_radius(g, ["src/new_module.py"])
    assert rep.unmatched_files == ["src/new_module.py"]
    assert rep.seeds == []


def test_context_pack_budget():
    g = graph()
    pack = cp.build_pack(g, "fix login auth flow", budget_tokens=400)
    assert "login()" in pack
    assert "Read these files first" in pack
    assert len(pack) // 4 <= 400 + 100  # soft ceiling


def test_drift():
    before = graph()
    after_raw = copy.deepcopy(FIXTURE)
    # new node with many edges -> becomes god node; cross-community edge
    after_raw["nodes"].append({"id": "megahub", "label": "MegaHub",
                               "source_file": "src/hub.py", "community": 0})
    for target in ["auth.py", "login", "db.py", "query", "utils"]:
        after_raw["links"].append({"source": "megahub", "target": target,
                                   "relation": "uses",
                                   "confidence": "EXTRACTED"})
    # orphan utils by removing its only edge
    after_raw["links"] = [l for l in after_raw["links"]
                          if not (l["source"] == "login"
                                  and l["target"] == "utils"
                                  and l["relation"] == "imports")]
    after = Graph.from_node_link(after_raw)
    rep = dr.diff(before, after, god_top_n=1)
    assert "megahub" in rep.added_nodes
    assert "megahub" in rep.new_god_nodes
    assert any(a == "megahub" or b == "megahub"
               for a, b, _ in rep.new_cross_community_edges)
    assert not rep.clean
    md = dr.render_markdown(before, after, rep)
    assert "MegaHub" in md and "drift" in md.lower()


def test_drift_community_relabel_warning():
    """When communities are relabeled, drift warns about false positives."""
    import copy
    before = graph()
    # Swap community IDs on all nodes (simulates relabeling)
    after_raw = copy.deepcopy(FIXTURE)
    for n in after_raw["nodes"]:
        if n.get("community") is not None:
            n["community"] = (n["community"] + 1) % 3
    # Add an edge that looks cross-community only due to relabeling
    after_raw["links"].append({
        "source": "login", "target": "query",
        "relation": "uses", "confidence": "EXTRACTED"
    })
    after = Graph.from_node_link(after_raw)
    rep = dr.diff(before, after)
    assert rep.community_warning != ""
    assert "relabeling" in rep.community_warning.lower()


def test_blast_json_output():
    """blast --format json produces valid, parseable JSON."""
    import json
    g = graph()
    rep = br.blast_radius(g, ["src/auth.py"], max_depth=2)
    d = rep.to_dict(g)
    # Roundtrip through JSON
    text = json.dumps(d)
    parsed = json.loads(text)
    assert parsed["risk"] in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(parsed["hits"], list)
    assert all("node_id" in h for h in parsed["hits"])


def test_drift_json_output():
    """drift to_dict produces valid JSON with all key fields."""
    import json, copy
    before = graph()
    after_raw = copy.deepcopy(FIXTURE)
    after_raw["nodes"].append({"id": "new", "label": "new", "source_file": "new.py", "community": 0})
    after_raw["links"].append({"source": "new", "target": "login", "relation": "calls", "confidence": "EXTRACTED"})
    after = Graph.from_node_link(after_raw)
    rep = dr.diff(before, after)
    d = rep.to_dict(before, after)
    text = json.dumps(d)
    parsed = json.loads(text)
    assert "clean" in parsed
    assert "verdict" in parsed
    assert isinstance(parsed["added_nodes"], list)


def test_freshness(tmp_path):
    root = tmp_path
    (root / "graphify-out").mkdir()
    gp = root / "graphify-out" / "graph.json"
    gp.write_text(json.dumps(FIXTURE))
    old = time.time() - 100
    import os
    os.utime(gp, (old, old))
    src = root / "app.py"
    src.write_text("print('hi')")  # newer than graph
    rep = check_freshness(root)
    assert not rep.fresh
    assert "app.py" in rep.stale_files
    # rebuild graph -> fresh again
    os.utime(gp, None)
    rep2 = check_freshness(root)
    assert rep2.fresh


def test_who_uses():
    from bridge import lookup
    g = graph()
    rep = lookup.who_uses(g, "query")
    assert rep.matched_node == "query"
    rels = set(rep.consumers)
    assert "calls" in rels and "contains" in rels
    md = lookup.render_markdown(g, rep)
    assert "Who uses" in md and "login()" in md


def test_who_uses_no_match():
    from bridge import lookup
    g = graph()
    rep = lookup.who_uses(g, "does_not_exist_xyz")
    assert rep.matched_node is None
    assert "No node matching" in lookup.render_markdown(g, rep)


def test_schema_guard_rejects_garbage(tmp_path):
    from bridge.graphio import GraphSchemaError, validate_node_link
    for bad in ([1, 2, 3], {"foo": "bar"}, {"nodes": "not-a-list"},
                {"nodes": [], "wrong": []},
                {"nodes": [{"no_id": 1}], "links": []},
                {"nodes": [{"id": "a"}], "links": [{"source": "a"}]}):
        try:
            validate_node_link(bad)
            assert False, f"should have rejected: {bad!r}"
        except GraphSchemaError as e:
            assert "graphify" in str(e)  # actionable message
    # corrupted file path
    p = tmp_path / "graph.json"
    p.write_text("{ not json")
    try:
        Graph.load(p)
        assert False, "should have raised on invalid JSON"
    except GraphSchemaError as e:
        assert "rebuild" in str(e)


def test_schema_guard_rejects_dangling_edges(tmp_path):
    from bridge.graphio import GraphSchemaError, validate_node_link
    # Edge pointing to nonexistent node
    bad = {
        "nodes": [{"id": "a"}, {"id": "b"}],
        "links": [{"source": "a", "target": "GHOST"}]
    }
    try:
        validate_node_link(bad)
        assert False, "should have rejected dangling edge"
    except GraphSchemaError as e:
        assert "non-existent" in str(e)
        assert "GHOST" in str(e)


def test_schema_guard_accepts_valid():
    from bridge.graphio import validate_node_link
    validate_node_link(FIXTURE)                 # links key
    alt = dict(FIXTURE); alt["edges"] = alt.pop("links")
    validate_node_link(alt)                     # edges key variant


def test_upstream_check(tmp_path):
    from bridge import upstream
    repo_root = Path(__file__).resolve().parents[1]
    rep = upstream.collect_references(repo_root / "skills",
                                      extra_paths=[repo_root / "ci"])
    assert "writing-plans" in rep.skill_refs
    assert "query" in rep.graphify_subcommands
    assert "--update" in rep.graphify_flags
    assert "--no-viz" in rep.graphify_flags        # picked up from ci/
    assert "for" not in rep.graphify_subcommands   # stopword filtered

    # fake upstream missing one referenced skill -> BROKEN verdict, exit 2 path
    sp = tmp_path / "superpowers"
    for name in sorted(rep.skill_refs)[:-1]:       # omit one
        d = sp / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: x\n---\n")
    (sp / "hooks").mkdir()
    (sp / "hooks" / "session-start").write_text('echo additionalContext')
    upstream.check_superpowers(rep, sp)
    assert len(rep.missing_skills) == 1 and rep.broken
    assert "BROKEN" in upstream.render(rep)

    # graphify help missing a flag we use
    rep2 = upstream.collect_references(repo_root / "skills")
    upstream.check_graphify_help(rep2, "usage: graphify query path explain")
    assert "--update" in rep2.missing_graphify


def test_pack_feedback_roundtrip(tmp_path):
    from bridge import pack_feedback as pf
    fb = pf.PackFeedback(
        task_id="task-1",
        timestamp="2026-07-16T10:00:00Z",
        pack_node_ids=["login", "auth.py"],
        pack_was_sufficient=True,
        extra_reads=[],
        unused_nodes=["utils"],
    )
    pf.log_feedback(fb, data_dir=tmp_path)
    pf.log_feedback(fb, data_dir=tmp_path)  # second entry
    history = pf.load_history(data_dir=tmp_path)
    assert len(history) == 2
    assert history[0].task_id == "task-1"
    assert history[0].pack_was_sufficient is True
    assert history[0].unused_nodes == ["utils"]


def test_pack_feedback_weights(tmp_path):
    from bridge import pack_feedback as pf
    # 4 insufficient packs with extra reads -> should increase seed_boost
    for i in range(4):
        pf.log_feedback(pf.PackFeedback(
            task_id=f"task-{i}", timestamp=f"2026-07-16T1{i}:00:00Z",
            pack_node_ids=["login", "auth.py"],
            pack_was_sufficient=False,
            extra_reads=["src/missing.py"],
            unused_nodes=[],
        ), data_dir=tmp_path)
    # 1 sufficient pack with unused hub node
    pf.log_feedback(pf.PackFeedback(
        task_id="task-ok", timestamp="2026-07-16T15:00:00Z",
        pack_node_ids=["login", "auth.py", "megahub"],
        pack_was_sufficient=True,
        extra_reads=[],
        unused_nodes=["megahub"],
    ), data_dir=tmp_path)
    history = pf.load_history(data_dir=tmp_path)
    weights = pf.compute_weights(history)
    # >30% insufficient -> seed_boost should be above default 3.0
    assert weights.seed_boost > 3.0
    # default weights object should have sane defaults
    default = pf.ScoringWeights()
    assert default.seed_boost == 3.0
    assert default.degree_tiebreaker == 0.5


def test_pack_feedback_stats(tmp_path):
    from bridge import pack_feedback as pf
    pf.log_feedback(pf.PackFeedback(
        task_id="t1", timestamp="2026-07-16T10:00:00Z",
        pack_node_ids=["a"], pack_was_sufficient=True,
        extra_reads=[], unused_nodes=[],
    ), data_dir=tmp_path)
    history = pf.load_history(data_dir=tmp_path)
    md = pf.render_stats(history)
    assert "Pack quality" in md or "pack" in md.lower()
    assert "1" in md  # at least shows count


def test_pack_feedback_empty():
    from bridge import pack_feedback as pf
    import tempfile, pathlib
    d = pathlib.Path(tempfile.mkdtemp())
    history = pf.load_history(data_dir=d)
    assert history == []
    weights = pf.compute_weights(history)
    assert weights.seed_boost == 3.0  # defaults when no history


def test_guard_no_creep():
    from bridge import guard
    g = graph()
    rep = guard.implementation_guard(g,
        planned_files=["src/auth.py"],
        touched_files=["src/auth.py"])
    assert not rep.scope_creep
    assert rep.surprise_nodes == []
    md = guard.render_markdown(g, rep)
    assert "No scope creep" in md or "scope" in md.lower()


def test_guard_scope_creep():
    from bridge import guard
    g = graph()
    # Planned to touch only auth, but also touched db
    rep = guard.implementation_guard(g,
        planned_files=["src/auth.py"],
        touched_files=["src/auth.py", "src/db.py"])
    assert rep.scope_creep
    assert len(rep.surprise_nodes) > 0
    md = guard.render_markdown(g, rep)
    assert "scope creep" in md.lower() or "Surprise" in md or "surprise" in md.lower()


def test_narrate_community():
    from bridge import narrate
    g = graph()
    # Community 0 has auth.py and login
    profile = narrate.profile_community(g, 0)
    assert profile.community_id == 0
    assert profile.node_count >= 2
    assert profile.hub_label in ("auth.py", "login()")
    assert len(profile.narrative) > 0
    assert profile.hub_label in profile.narrative


def test_narrate_all():
    from bridge import narrate
    g = graph()
    profiles = narrate.all_communities(g)
    # Fixture has communities 0, 1, 2
    ids = {p.community_id for p in profiles}
    assert {0, 1, 2} <= ids
    md = narrate.render_markdown(g, profiles)
    assert "Community" in md or "community" in md


def test_narrate_empty_community():
    from bridge import narrate
    g = graph()
    # Community 99 doesn't exist
    profile = narrate.profile_community(g, 99)
    assert profile.node_count == 0
    assert profile.narrative != ""  # should still produce a message


def test_parallel_no_conflict():
    from bridge import parallel as par
    g = graph()
    # Use truly disjoint files: only utils (community 2) vs only db (community 1)
    tasks = [
        par.TaskSpec(id="task-db", files=["src/db.py"]),
        par.TaskSpec(id="task-utils", files=["src/utils.py"]),
    ]
    plan = par.parallel_safety(g, tasks, max_depth=1)
    assert len(plan.parallel_groups) >= 1
    md = par.render_markdown(g, plan)
    assert "Parallel" in md or "parallel" in md


def test_parallel_conflict():
    from bridge import parallel as par
    g = graph()
    # Both tasks touch auth.py -> overlapping blast radii
    tasks = [
        par.TaskSpec(id="task-a", files=["src/auth.py"]),
        par.TaskSpec(id="task-b", files=["src/auth.py", "src/db.py"]),
    ]
    plan = par.parallel_safety(g, tasks)
    assert len(plan.conflicts) > 0
    assert any(c.task_a == "task-a" and c.task_b == "task-b"
               for c in plan.conflicts)


def test_parallel_parse_tasks():
    from bridge import parallel as par
    text = '[{"id": "t1", "files": ["a.py"]}, {"id": "t2", "files": ["b.py"]}]'
    tasks = par.parse_tasks(text)
    assert len(tasks) == 2
    assert tasks[0].id == "t1"
    assert tasks[1].files == ["b.py"]


def test_explain_found():
    from bridge import explain
    g = graph()
    rep = explain.explain(g, "login", budget=800)
    assert rep.matched_node == "login"
    md = explain.render_markdown(g, rep)
    assert "login" in md.lower()
    assert "Blast radius" in md or "blast" in md.lower()
    assert "Context pack" in md or "pack" in md.lower()


def test_explain_not_found():
    from bridge import explain
    g = graph()
    rep = explain.explain(g, "nonexistent_xyz_abc")
    assert rep.matched_node is None
    md = explain.render_markdown(g, rep)
    assert "No node matching" in md or "not found" in md.lower()


def test_context_pack_with_weights():
    from bridge import context_pack as cp
    from bridge.pack_feedback import ScoringWeights
    g = graph()
    # With a high hub_penalty, hub nodes should rank lower
    w = ScoringWeights(seed_boost=5.0, degree_tiebreaker=0.1,
                       community_bonus=0.0, hub_penalty=0.8)
    ranked = cp.score_nodes(g, "login auth", weights=w)
    assert len(ranked) > 0
    # With default weights, score_nodes should still work
    ranked_default = cp.score_nodes(g, "login auth")
    assert len(ranked_default) > 0


def test_doctor_basics(tmp_path):
    from bridge import doctor
    # No graph -> not ready
    rep = doctor.check(root=tmp_path)
    assert not rep.ready
    assert rep.python_ok
    assert any("graph" in r.lower() for r in rep.recommendations)
    md = doctor.render_markdown(rep)
    assert "NOT READY" in md or "not found" in md.lower()

    # With graph -> ready
    (tmp_path / "graphify-out").mkdir()
    gp = tmp_path / "graphify-out" / "graph.json"
    gp.write_text(json.dumps(FIXTURE))
    rep2 = doctor.check(root=tmp_path)
    assert rep2.ready
    assert rep2.graph_exists
    md2 = doctor.render_markdown(rep2)
    assert "READY" in md2


def test_cli_exit_codes(tmp_path):
    from bridge.cli import main
    import json
    import os
    
    (tmp_path / "graphify-out").mkdir()
    gp = tmp_path / "graphify-out" / "graph.json"
    gp.write_text(json.dumps(FIXTURE))
    
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # blast (no files) -> 0
        assert main(["blast", "--graph", str(gp)]) == 0

        # freshness (fresh) -> 0
        os.utime(gp, None)
        assert main(["freshness", "--graph", str(gp)]) == 0
        
        # freshness (stale) -> 2
        src = tmp_path / "app.py"
        src.write_text("print('hi')")
        assert main(["freshness", "--graph", str(gp)]) == 2

        # guard (no creep) -> 0
        assert main(["guard", "--planned", "src/auth.py", "--touched", "src/auth.py", "--graph", str(gp)]) == 0
        
        # guard (creep) -> 2
        assert main(["guard", "--planned", "src/auth.py", "--touched", "src/auth.py", "src/db.py", "--graph", str(gp)]) == 2

        # drift (clean) -> 0
        assert main(["drift", str(gp), str(gp)]) == 0
        
        # test --explain-exit-code parsing
        assert main(["--explain-exit-code", "freshness", "--graph", str(gp)]) == 2
    finally:
        os.chdir(old_cwd)
