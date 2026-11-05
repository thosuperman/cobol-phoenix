from phoenix.cobol.diagnostics import Severity
from phoenix.cobol.lexer import tokenize
from phoenix.cobol.preprocessor import expand_copies


def resolver(books):
    def r(name):
        key = name.strip("'\"").upper().replace(".CPY", "")
        if key in books:
            return f"copy/{key}.cpy", books[key], None
        return None

    return r


def test_copy_expansion_keeps_copybook_line_numbers():
    books = {"REC": "       01  REC.\n           05  A PIC X(3).\n"}
    toks, _, _ = tokenize("m.cob", "       WORKING-STORAGE SECTION.\n       COPY REC.\n       01  B PIC X.\n")
    res = expand_copies("m.cob", toks, resolver(books))
    a = next(t for t in res.tokens if t.value == "A")
    assert a.file == "copy/REC.cpy" and a.line == 2
    assert a.copied_from == "m.cob:2"
    assert res.copies[0].resolved == "copy/REC.cpy"


def test_copy_replacing_pseudo_text():
    books = {"TPL": "       01  :P:-REC.\n           05  :P:-ID PIC 9.\n"}
    toks, _, _ = tokenize("m.cob", "       COPY TPL REPLACING ==:P:== BY ==CUST==.\n")
    res = expand_copies("m.cob", toks, resolver(books))
    words = [t.value for t in res.tokens]
    assert "CUST-REC" in words and "CUST-ID" in words


def test_missing_and_recursive_copybooks_are_reported():
    books = {"SELF": "       COPY SELF.\n"}
    toks, _, _ = tokenize("m.cob", "       COPY NOPE.\n       COPY SELF.\n")
    res = expand_copies("m.cob", toks, resolver(books))
    codes = {d.code for d in res.diagnostics if d.severity == Severity.ERROR}
    assert {"PP001", "PP002"} <= codes
