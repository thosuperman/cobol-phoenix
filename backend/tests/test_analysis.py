from phoenix.analysis.project_analysis import WEIGHTS, analyze


def test_overview_and_graph(sample_parse):
    a = analyze(sample_parse)
    o = a["overview"]
    assert o["programs"] == 3 and o["copybooks"] == 3
    assert o["call_edges"] == 1 and o["copy_edges"] == 6
    assert o["unsupported_constructs"] == 3  # OPEN / WRITE / CLOSE in AUDITLOG (INSPECT TALLYING is supported)
    ids = {n["id"] for n in a["graph"]["nodes"]}
    assert "program:PREMCALC" in ids and "program:RATEENG" in ids and "copybook:copy/POLICY.cpy" in ids
    call = next(e for e in a["graph"]["edges"] if e["type"] == "call")
    assert call["source"] == "program:PREMCALC" and call["target"] == "program:RATEENG"


def test_complexity_is_the_documented_formula(sample_parse):
    a = analyze(sample_parse)
    for p in a["programs"]:
        m = p["metrics"]
        expected = sum(m[k] * w for k, w in WEIGHTS.items())
        assert m["score"] == round(expected, 1)


def test_rules_cite_real_source_lines(sample_parse):
    a = analyze(sample_parse)
    files = {f.path: f.text.splitlines() for f in sample_parse.files}
    rules = a["rules"]
    assert len(rules) >= 20
    for r in rules:
        assert r["file"] in files
        assert 1 <= r["line_start"] <= r["line_end"] <= len(files[r["file"]])
        for c in r["conditions"] + r["calculations"]:
            assert r["line_start"] <= c["line"] <= r["line_end"]
    pm404 = next(r for r in rules if r["id"] == "RATEENG:PM-404")
    assert "RR-BASE-PREMIUM" in pm404["outputs"] and pm404["description_source"] == "source-comment"
    assert any("ROUNDED" in c["text"] for c in pm404["calculations"])


INSPECT_RULE_PROGRAM = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. INSPRULE.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  MSG            PIC X(10).
       01  CODE-TXT       PIC X(4).
       01  BLANKS         PIC 9(3) VALUE 0.
       PROCEDURE DIVISION.
       CHECK-PARA.
           INSPECT MSG TALLYING BLANKS FOR ALL SPACES
           INSPECT CODE-TXT REPLACING ALL "-" BY "0"
           IF BLANKS > 5
              DISPLAY "SPARSE"
           END-IF
           GOBACK.
"""


def test_inspect_reads_and_writes_reach_dataflow_and_rules():
    from phoenix.analysis.dataflow import stmt_access
    from phoenix.cobol import ir
    from phoenix.cobol.project import parse_project

    pp = parse_project({"insprule.cob": INSPECT_RULE_PROGRAM})
    prog = pp.program("INSPRULE").program
    tally, repl = prog.paragraphs[0].statements[:2]
    assert isinstance(tally, ir.Inspect) and isinstance(repl, ir.Inspect)
    a = stmt_access(tally)
    # TALLYING reads the inspected field and adds to (reads + writes) the counter
    assert a.reads == {"MSG", "BLANKS"} and a.writes == {"BLANKS"}
    b = stmt_access(repl)
    assert b.reads == {"CODE-TXT"} and b.writes == {"CODE-TXT"}
    rule = next(r for r in analyze(pp)["rules"] if r["paragraph"] == "CHECK-PARA")
    assert {"MSG", "BLANKS", "CODE-TXT"} <= set(rule["inputs"])
    assert {"BLANKS", "CODE-TXT"} <= set(rule["outputs"])
