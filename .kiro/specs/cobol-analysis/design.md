# Design — COBOL analysis engine

## Pipeline
1. `source.py` — reads files, detects format, produces `SourceLine(file, number, text)`.
2. `lexer.py` — tokenises lines into `Token(kind, value, file, line, col)`; handles continuation
   and pseudo-text `==...==`.
3. `preprocessor.py` — expands COPY (with REPLACING) recursively (depth ≤ 10, cycle detection),
   keeping each token's origin.
4. `parser.py` — recursive-descent parser over tokens → AST, then `ir.py` dataclasses.
   Statement parsing is verb driven; an unknown verb consumes tokens until the next known verb
   or period and yields `Unsupported`.
5. `layout.py` — computes storage offsets (USAGE sizes, OCCURS, REDEFINES, SYNC ignored with warning).
6. `analysis/` — dependency graph, data flow, complexity, rule extraction.

## Complexity heuristic (documented, deterministic)
`score = statements*1 + decision_points*3 + paragraphs*2 + calls*4 + unsupported*10 + data_items*0.25`
Bands: `< 150` Low, `< 400` Medium, `< 900` High, else Very High.
Decision points: each IF, each EVALUATE WHEN, each PERFORM UNTIL/VARYING, each AND/OR.

## Rule extraction
- A *rule* is a paragraph that contains at least one decision (IF/EVALUATE) or computation
  (COMPUTE/ADD/SUBTRACT/MULTIPLY/DIVIDE) or assigns a literal to a field later used in output.
- Comment blocks directly above or inside a paragraph of the form `ID: text` (e.g. `NB-202:`)
  are captured as rule annotations with their own line ranges.
- Inputs = fields read before being written in the paragraph; outputs = fields written.
- Status semantics: `NOT_RUN` (no verification yet), `VERIFIED` (executed by at least one passing
  differential case and not blamed by a failing one), `FAILED` (executed by a failing case whose differing
  fields include one of the rule's outputs, or whose difference cannot be attributed), `NOT_EXERCISED`
  (no compared case executed it), `UNSUPPORTED` (contains an unsupported construct). Coverage % is reported.
