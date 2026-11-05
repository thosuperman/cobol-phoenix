from phoenix.cobol.lexer import TK, SourceFormat, detect_format, tokenize


def fixed(*lines: str) -> str:
    return "\n".join(lines) + "\n"


def test_fixed_format_ignores_sequence_and_identification_areas():
    src = fixed("000100 IDENTIFICATION DIVISION.".ljust(72) + "IGNORED1", "000200*COMMENT LINE", "000300 PROGRAM-ID. DEMO.")
    toks, diags, fmt = tokenize("a.cob", src)
    assert fmt == SourceFormat.FIXED
    words = [t.value for t in toks if t.kind == TK.WORD]
    assert words == ["IDENTIFICATION", "DIVISION", "PROGRAM-ID", "DEMO"]
    assert toks[0].line == 1 and toks[-2].line == 3
    assert not diags


def test_continuation_of_alphanumeric_literal():
    src = fixed(
        '       01  X PIC X(60) VALUE "HELLO THIS LITERAL CONTINUES ON THE NEXT',
        '      -    "LINE NOW".',
    )
    toks, _, _ = tokenize("a.cob", src)
    lit = next(t for t in toks if t.kind == TK.STRING)
    assert lit.value.startswith("HELLO THIS LITERAL CONTINUES ON THE NEXT")
    assert lit.value.endswith("LINE NOW")
    assert lit.line == 1


def test_numbers_periods_and_signed_literals():
    toks, _, _ = tokenize("a.cob", fixed("           MOVE -12.50 TO A.", "           COMPUTE B = C - 1.", "           MOVE 1 TO D."))
    kinds = [(t.kind, t.value) for t in toks]
    assert (TK.NUMBER, "-12.50") in kinds
    assert (TK.OP, "-") in kinds and (TK.NUMBER, "1") in kinds
    assert sum(1 for k, _ in kinds if k == TK.PERIOD) == 3


def test_picture_strings_are_single_tokens():
    toks, _, _ = tokenize("a.cob", fixed("       01  A PIC ZZZ,ZZ9.99-.", "       01  B PICTURE IS $$$,$$9.99."))
    pics = [t.value for t in toks if t.kind == TK.PICTURE]
    assert pics == ["ZZZ,ZZ9.99-", "$$$,$$9.99"]


def test_free_format_and_floating_comments():
    src = 'IDENTIFICATION DIVISION. *> comment\nPROGRAM-ID. FREEDEMO.\n       MOVE "A *> not a comment" TO X.\n'
    assert detect_format(src) == SourceFormat.FREE
    toks, _, _ = tokenize("f.cob", src, SourceFormat.FREE)
    assert any(t.kind == TK.STRING and t.value == "A *> not a comment" for t in toks)
    assert "comment" not in [t.value for t in toks]


def test_hex_literal_and_pseudo_text():
    toks, _, _ = tokenize("a.cob", fixed("           MOVE X'4142' TO A.", "           COPY ABC REPLACING ==:P:== BY ==WS==."))
    assert any(t.kind == TK.STRING and t.value == "AB" and t.hex for t in toks)
    pseudo = [t for t in toks if t.kind == TK.PSEUDO]
    assert [p.inner[0].value for p in pseudo] == [":P:", "WS"]
