from phoenix.cobol import ir
from phoenix.cobol.project import parse_project

PROGRAM = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. DEMO.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  REC.
           05  A          PIC S9(5)V99 COMP-3.
           05  B          PIC X(4) VALUE "ABCD".
               88  B-OK   VALUE "ABCD" "WXYZ".
           05  T OCCURS 3 TIMES.
               10  T-CODE PIC X(2).
               10  T-AMT  PIC 9(3)V9.
           05  ALT REDEFINES T PIC X(18).
           05  N          PIC 9(4) COMP.
       77  CNT            PIC 99 VALUE 0.
       PROCEDURE DIVISION.
       MAIN-PARA.
           IF CNT < 1 OR > 5 AND NOT B-OK
              MOVE 1 TO CNT
           ELSE
              COMPUTE A ROUNDED = (A + 1) * 2 / 3
                 ON SIZE ERROR MOVE 0 TO A
              END-COMPUTE
           END-IF
           EVALUATE TRUE ALSO CNT
              WHEN B-OK ALSO 1 THRU 3 PERFORM SUB-PARA
              WHEN OTHER CONTINUE
           END-EVALUATE
           PERFORM VARYING CNT FROM 1 BY 1 UNTIL CNT > 3
              MOVE "XX" TO T-CODE (CNT)
           END-PERFORM
           INSPECT B TALLYING CNT FOR CHARACTERS
           GOBACK.
       SUB-PARA.
           EXIT.
"""


def parse(src=PROGRAM):
    pp = parse_project({"demo.cob": src})
    assert len(pp.programs) == 1
    return pp.programs[0]


def test_data_layout_offsets_sizes_and_usages():
    p = parse().program
    idx = {it.name: it for it in p.iter_items()}
    assert idx["A"].size == 4 and idx["A"].usage == "COMP-3" and idx["A"].picture.scale == 2 and idx["A"].picture.signed
    assert idx["B"].offset == 4 and idx["B"].value.value == "ABCD"
    assert [c.name for c in idx["B"].conditions] == ["B-OK"] and len(idx["B"].conditions[0].values) == 2
    assert idx["T"].occurs == 3 and idx["T"].size == 6 and idx["T-AMT"].dims == [(6, 3)]
    assert idx["ALT"].offset == idx["T"].offset and idx["ALT"].size == 18
    assert idx["N"].size == 2 and idx["N"].offset == 8 + 18
    assert idx["REC"].size == 4 + 4 + 18 + 2


def test_statements_conditions_and_abbreviations():
    p = parse().program
    stmts = p.paragraphs[0].statements
    first = stmts[0]
    assert isinstance(first, ir.If)
    # CNT < 1 OR (CNT > 5 AND NOT B-OK) with abbreviated subject
    cond = first.cond
    assert isinstance(cond, ir.Or)
    assert isinstance(cond.right, ir.And)
    assert isinstance(cond.right.left, ir.Rel) and cond.right.left.left.name == "CNT" and cond.right.left.op == ">"
    comp = first.orelse[0]
    assert isinstance(comp, ir.Compute) and comp.targets[0].rounded and comp.on_size_error
    ev = stmts[1]
    assert isinstance(ev, ir.Evaluate) and ev.subjects[0] == "TRUE" and ev.whens[0].objects[0][1].kind == "range"
    perf = stmts[2]
    assert isinstance(perf, ir.Perform) and perf.varying and perf.body


def test_unsupported_constructs_are_reported_with_location():
    pp = parse()
    unsup = pp.unsupported
    assert any(u["construct"] == "INSPECT" and u["line"] == 31 for u in unsup)
    stmts = list(ir.walk_statements(pp.program.paragraphs[0].statements))
    assert any(isinstance(s, ir.Unsupported) and s.verb == "INSPECT" for s in stmts)


def test_references_are_resolved():
    p = parse().program
    perf = p.paragraphs[0].statements[2]
    move = perf.body[0]
    assert move.targets[0].item.endswith("T-CODE") and move.targets[0].subscripts


def test_sample_project_parses_without_errors(sample_parse):
    ids = {p.program.program_id for p in sample_parse.programs}
    assert ids == {"PREMCALC", "RATEENG", "AUDITLOG"}
    for p in sample_parse.programs:
        assert not [d for d in p.diagnostics if str(d.severity) == "error"], p.diagnostics
    audit = sample_parse.program("AUDITLOG")
    assert {u["construct"] for u in audit.unsupported} >= {"OPEN", "WRITE", "CLOSE"}
    # INSPECT RR-MESSAGE TALLYING WS-SPACE-COUNT FOR ALL SPACES (line 38) is in the supported subset
    assert not any(u["construct"] == "INSPECT" for u in audit.unsupported)
    insp = [s for p in audit.program.paragraphs for s in ir.walk_statements(p.statements) if isinstance(s, ir.Inspect)]
    assert len(insp) == 1 and insp[0].loc.line == 38 and insp[0].pattern.kind == "figurative" and insp[0].pattern.value == "SPACE"


INSPECT_PROGRAM = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. INSP.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  TXT            PIC X(10).
       01  CNT            PIC 9(3).
       PROCEDURE DIVISION.
       MAIN-PARA.
           INSPECT TXT TALLYING CNT FOR ALL "AB"
           INSPECT TXT REPLACING ALL "A" BY "Z"
           INSPECT TXT REPLACING ALL SPACES BY ZERO
           INSPECT TXT (2:3) TALLYING CNT FOR ALL QUOTE
           INSPECT TXT TALLYING CNT FOR CHARACTERS
           INSPECT TXT TALLYING CNT FOR LEADING "A"
           INSPECT TXT REPLACING FIRST "A" BY "B"
           INSPECT TXT TALLYING CNT FOR ALL "A" BEFORE INITIAL "B"
           INSPECT TXT CONVERTING "AB" TO "XY"
           INSPECT TXT TALLYING CNT FOR ALL "A" ALL "B"
           INSPECT TXT TALLYING CNT FOR ALL TXT
           INSPECT TXT REPLACING ALL "AB" BY "X"
           GOBACK.
"""


def test_inspect_supported_forms_parse_into_ir():
    pp = parse(INSPECT_PROGRAM)
    stmts = pp.program.paragraphs[0].statements
    tally, repl, fig, refmod = stmts[:4]
    assert isinstance(tally, ir.Inspect) and tally.mode == "TALLYING" and tally.loc.line == 9
    assert tally.target.item == "TXT" and tally.counter.item == "CNT" and tally.pattern.value == "AB"
    assert isinstance(repl, ir.Inspect) and repl.mode == "REPLACING" and repl.pattern.value == "A" and repl.replacement.value == "Z"
    assert fig.pattern.kind == "figurative" and fig.pattern.value == "SPACE" and fig.replacement.value == "ZERO"
    assert refmod.target.refmod is not None and refmod.pattern.value == "QUOTE"
    assert isinstance(stmts[-1], ir.Goback)
    # the IR stays JSON serialisable
    assert ir.to_jsonable(tally)["_t"] == "Inspect"


def test_other_inspect_forms_are_reported_unsupported_with_location():
    pp = parse(INSPECT_PROGRAM)
    stmts = pp.program.paragraphs[0].statements
    unsupported = [s for s in stmts if isinstance(s, ir.Unsupported)]
    assert [s.loc.line for s in unsupported] == list(range(13, 21))
    assert all(s.verb == "INSPECT" and s.reason for s in unsupported)
    assert {u["line"] for u in pp.unsupported if u["construct"] == "INSPECT"} == set(range(13, 21))
    # mismatched REPLACING lengths are an error diagnostic as well
    assert any(d.code == "PRC003" and d.line == 20 for d in pp.diagnostics)
    # nothing after an unsupported INSPECT is swallowed
    assert isinstance(stmts[-1], ir.Goback) and len(stmts) == 13
