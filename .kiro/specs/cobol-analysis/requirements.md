# Requirements — COBOL analysis engine

1. WHEN source is fixed format THE LEXER SHALL ignore columns 1–6 and 73+, treat `*` and `/` in column 7 as comments and join `-` continuation lines.
2. WHEN source contains `>>SOURCE FORMAT FREE` or the project is configured as free format THE LEXER SHALL accept free-format lines and `*>` comments.
3. THE LEXER SHALL attach file name and line number to every token, including tokens that came from copybooks.
4. WHEN a `COPY name [REPLACING ==a== BY ==b==]` statement is found THE PREPROCESSOR SHALL inline the copybook and preserve the copybook's own line numbers.
5. WHEN a copybook cannot be resolved THE PREPROCESSOR SHALL emit an error diagnostic and continue.
6. THE PARSER SHALL build data items with level, name, PICTURE, USAGE (DISPLAY, COMP, COMP-3, COMP-5, BINARY, PACKED-DECIMAL), VALUE, OCCURS, REDEFINES, SIGN SEPARATE and 88-level conditions.
7. THE PARSER SHALL compute byte offsets and sizes for every data item.
8. THE PARSER SHALL parse procedure statements: MOVE, COMPUTE, ADD, SUBTRACT, MULTIPLY, DIVIDE, IF, EVALUATE, PERFORM (simple, THRU, TIMES, UNTIL, VARYING, inline), CALL, STOP RUN, GOBACK, EXIT [PARAGRAPH], CONTINUE, DISPLAY, ACCEPT, INITIALIZE, SET, STRING (DELIMITED BY SIZE / literal).
9. WHEN the parser meets a statement outside the supported subset THE PARSER SHALL produce an `Unsupported` node with its source range and a warning, never dropping it silently.
10. THE ANALYZER SHALL produce dependencies (COPY, CALL, PERFORM), per-paragraph data reads/writes, and complexity metrics.
11. THE RULE EXTRACTOR SHALL produce business rules from paragraphs and decision blocks with inputs, outputs, conditions, calculations and source ranges.
