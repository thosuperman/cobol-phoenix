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


def _run_main(project_dir, entry, stdin):
    r = subprocess.run(
        [sys.executable, "-m", "app.cli", "--entry", entry, "--mode", "main"],
        input=json.dumps([{"id": "a", "stdin": stdin}]), cwd=project_dir, capture_output=True, text=True, timeout=60,
    )  # fmt: skip
    return json.loads(r.stdout)[0]


def test_inspect_is_translated_and_generated_suite_passes(tmp_path):
    from tests.conftest import INSPECT_DEMO_SOURCE

    pp = parse_project({"inspdemo.cob": INSPECT_DEMO_SOURCE})
    gp = generate_project(pp, "INSPDEMO", "insp")
    assert not gp.unsupported
    src = gp.files["app/programs/inspdemo.py"]
    assert "rt.inspect_tally(" in src and "rt.inspect_replace(" in src and "float(" not in src
    # TALLYING adds to the counter, it never overwrites it
    assert "self.ws_spaces.store(self.ws_spaces.value + rt.inspect_tally(" in src
    write_project(gp, tmp_path)
    out = _run_main(tmp_path, "INSPDEMO", "ABAB  AB\n")
    assert out["status"] == "ok", out
    assert out["stdout"] == 'SPACES=019 AB=006 A=3\nTEXT="Y"Y**XY************\nCODE=19293\n'
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=tmp_path, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr


def test_unsupported_inspect_forms_raise_unsupported_construct(tmp_path):
    src = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. INSPBAD.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  T PIC X(5) VALUE "AAAAA".
       01  S PIC S9(3) VALUE -12.
       01  C PIC 9(3) VALUE 0.
       PROCEDURE DIVISION.
           INSPECT T TALLYING C FOR CHARACTERS BEFORE INITIAL "A"
           INSPECT S TALLYING C FOR ALL "1"
           DISPLAY C
           STOP RUN.
"""
    pp = parse_project({"inspbad.cob": src})
    gp = generate_project(pp, "INSPBAD", "bad")
    lines = {u["line"] for u in gp.unsupported if u["construct"] == "INSPECT"}
    assert lines == {9, 10}  # unsupported form (parser) and signed numeric target (generator)
    py = gp.files["app/programs/inspbad.py"]
    assert py.count("raise rt.UnsupportedConstruct('INSPECT'") == 2
    write_project(gp, tmp_path)
    out = _run_main(tmp_path, "INSPBAD", "")
    assert out["status"] == "unsupported", out


# ------------------------------------------------- OpenAPI request examples (task 7)


def _sample_fixtures(entry):
    from tests.conftest import SAMPLE

    return json.loads((SAMPLE / "phoenix-fixtures.json").read_text())[entry]


def test_request_examples_come_from_fixtures(sample_parse):
    fixtures = _sample_fixtures("RATEENG")
    gp = generate_project(sample_parse, "RATEENG", "rate-svc", fixtures=fixtures)
    schemas = gp.files["app/schemas.py"]
    assert "json_schema_extra={'examples': REQUEST_EXAMPLES}" in schemas
    # every fixture with PICTURE-valid inputs becomes an example, in fixture order
    valid = [f["id"] for f in fixtures if f["id"] != "non-numeric-age"]
    for fid in valid:
        assert f"    {fid!r}," in schemas
    assert "'non-numeric-age'" not in schemas
    readme = gp.files["README.md"]
    assert "| non-numeric-age | PR-DRIVER-AGE: 'raw:4A0' is not a decimal number |" in readme
    assert "float" not in schemas


def test_no_fixtures_means_no_examples(sample_parse):
    gp = generate_project(sample_parse, "RATEENG", "rate-svc")
    schemas = gp.files["app/schemas.py"]
    assert "REQUEST_EXAMPLES: list[dict] = []" in schemas and "json_schema_extra" not in schemas
    assert "pytest.mark.skip(reason=" in gp.files["tests/test_api.py"]


def test_request_examples_are_deterministic(sample_parse):
    fixtures = _sample_fixtures("RATEENG")
    a = generate_project(sample_parse, "RATEENG", "rate-svc", fixtures=fixtures)
    # reversing the key order inside each fixture must not change the output
    shuffled = [{**f, "inputs": {r: dict(reversed(list(v.items()))) for r, v in f["inputs"].items()}} for f in fixtures]
    b = generate_project(sample_parse, "RATEENG", "rate-svc", fixtures=shuffled)
    assert a.files == b.files


def test_generated_suite_posts_every_example(sample_parse, tmp_path):
    for entry, expected in (("RATEENG", ["standard-ca-full", "max-vehicle-value"]), ("PREMCALC", ["nightly-batch"])):
        gp = generate_project(sample_parse, entry, f"{entry.lower()}-svc", fixtures=_sample_fixtures(entry))
        write_project(gp, tmp_path / entry)
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", "tests"],
            cwd=tmp_path / entry, capture_output=True, text=True, timeout=180,
        )  # fmt: skip
        assert r.returncode == 0, r.stdout + r.stderr
        assert "test_openapi_examples_match_fixtures PASSED" in r.stdout
        for fid in expected:
            assert f"test_execute_openapi_example[{fid}] PASSED" in r.stdout, r.stdout
        assert "no-examples" not in r.stdout


def _decimal_text():
    from hypothesis import strategies as st

    return st.builds(
        lambda sign, lead, whole, frac: sign + "0" * lead + whole + (("." + frac) if frac is not None else ""),
        st.sampled_from(["", "+", "-"]),
        st.integers(0, 2),
        st.text("0123456789", min_size=1, max_size=10),
        st.none() | st.text("0123456789", min_size=1, max_size=5),
    )


def test_accepted_numeric_examples_pass_pydantic_validation():
    """**Validates: Requirements 6** — an example value the generator accepts always passes
    the Pydantic constraints it emits for the same PICTURE (max_digits, decimal_places, ge=0)."""
    from decimal import Decimal

    from hypothesis import given, settings
    from hypothesis import strategies as st
    from pydantic import Field, ValidationError, create_model

    from phoenix.codegen.project_gen import InterfaceLeaf, _numeric_example

    @settings(max_examples=300, derandomize=True, deadline=None)
    @given(st.integers(1, 9), st.integers(0, 4), st.booleans(), _decimal_text())
    def check(digits, scale, signed, text):
        scale = min(scale, digits)
        lf = InterfaceLeaf("X", "x", "x", "numeric", digits, digits, scale, signed, f"S9({digits})")
        accepted, _why = _numeric_example(lf, text)
        if accepted is None:
            return
        cons = {"max_digits": digits, "decimal_places": scale} | ({} if signed else {"ge": 0})
        model = create_model("M", x=(Decimal, Field(default=Decimal(0), **cons)))
        try:
            model.model_validate({"x": accepted})
        except ValidationError as exc:  # pragma: no cover - reported by Hypothesis
            raise AssertionError(f"{accepted!r} accepted for {lf} but rejected by Pydantic: {exc}") from exc

    check()
