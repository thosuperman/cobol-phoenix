import json
import py_compile
import subprocess
import sys

from phoenix.cobol.project import parse_project
from phoenix.codegen.program_gen import mutation_candidates, py_ident
from phoenix.codegen.project_gen import generate_project, write_project


def test_generation_is_deterministic(sample_parse):
    a = generate_project(sample_parse, "RATEENG", "rate-svc")
    b = generate_project(parse_project({k: v for k, v in __import__("tests.conftest", fromlist=["x"]).sample_sources().items()}), "RATEENG", "rate-svc")
    assert a.files == b.files


def test_generated_project_compiles_and_traces_to_real_lines(sample_parse, tmp_path):
    gp = generate_project(sample_parse, "PREMCALC", "premcalc-svc")
    assert gp.call_tree == ["PREMCALC", "RATEENG"] and not gp.unsupported
    write_project(gp, tmp_path)
    for rel in gp.files:
        if rel.endswith(".py"):
            py_compile.compile(str(tmp_path / rel), doraise=True)
    sources = {f.path: f.text.splitlines() for f in sample_parse.files}
    for t in gp.traceability:
        assert t["cobol_file"] in sources
        assert 1 <= t["cobol_start"] <= t["cobol_end"] <= len(sources[t["cobol_file"]])
        py_lines = gp.files[t["python_file"]].splitlines()
        assert 1 <= t["python_start"] <= len(py_lines)


def test_no_float_in_generated_business_logic(sample_parse):
    gp = generate_project(sample_parse, "RATEENG", "r")
    src = gp.files["app/programs/rateeng.py"]
    assert "float(" not in src and "D(" in src


def test_generated_tests_pass(sample_parse, tmp_path):
    gp = generate_project(sample_parse, "RATEENG", "rate-svc")
    write_project(gp, tmp_path)
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=tmp_path, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr


def test_main_program_runs_and_matches_gnucobol_expected_output(sample_parse, tmp_path):
    from tests.conftest import SAMPLE

    gp = generate_project(sample_parse, "PREMCALC", "p")
    write_project(gp, tmp_path)
    stdin = (SAMPLE / "fixtures" / "policies.txt").read_text()
    r = subprocess.run(
        [sys.executable, "-m", "app.cli", "--entry", "PREMCALC", "--mode", "main", "--date", "20260101093000"],
        input=json.dumps([{"id": "x", "stdin": stdin}]), cwd=tmp_path, capture_output=True, text=True, timeout=60,
    )  # fmt: skip
    out = json.loads(r.stdout)[0]
    assert out["status"] == "ok"
    # expected-output.txt was captured from GnuCOBOL 3.2
    assert out["stdout"] == (SAMPLE / "fixtures" / "expected-output.txt").read_text()


def test_mutation_changes_exactly_one_site(sample_parse):
    prog = sample_parse.program("RATEENG").program
    cands = mutation_candidates(prog)
    assert {"rounding", "relop", "literal"} <= {c.kind for c in cands}
    m = next(c for c in cands if c.kind == "rounding")
    base = generate_project(sample_parse, "RATEENG", "r").files["app/programs/rateeng.py"].splitlines()
    mut = generate_project(sample_parse, "RATEENG", "r", mutation=m).files["app/programs/rateeng.py"].splitlines()
    changed = [i for i, (a, b) in enumerate(zip(base, mut, strict=True)) if a != b]
    assert len(changed) == 1 and "rounded=True" in base[changed[0]] and "rounded=True" not in mut[changed[0]]


def test_identifiers_are_sanitised():
    assert py_ident("PASS") == "pass_"
    assert py_ident("1000-INIT") == "n1000_init"
    assert py_ident("CTX") == "ctx_"


def test_literals_are_escaped(tmp_path):
    src = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. ESC.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  X PIC X(30).
       PROCEDURE DIVISION.
           MOVE 'A"); __import__(''os'') #\\' TO X
           DISPLAY 'IT''S' X
           STOP RUN.
"""
    pp = parse_project({"esc.cob": src})
    gp = generate_project(pp, "ESC", "esc")
    write_project(gp, tmp_path)
    r = subprocess.run(
        [sys.executable, "-m", "app.cli", "--entry", "ESC", "--mode", "main"],
        input='[{"id":"a","stdin":""}]',
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    out = json.loads(r.stdout)[0]
    assert out["status"] == "ok", out
    assert out["stdout"].startswith("IT'SA\"); __import__('os') #\\")
