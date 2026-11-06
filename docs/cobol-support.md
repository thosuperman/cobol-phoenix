# Supported COBOL subset and semantics

Status meanings: **Verified** — executed by passing differential cases against GnuCOBOL 3.2.0 (sample project
and/or the external insurance corpus). **Unit** — covered by runtime unit tests whose expected values were
confirmed with GnuCOBOL probe programs. **Parsed** — recognised and represented in the IR. **Unsupported** —
detected and reported; generated as `raise UnsupportedConstruct(...)`.

| Construct | Status | Notes |
|---|---|---|
| IDENTIFICATION / ENVIRONMENT / DATA / PROCEDURE DIVISION | Verified | comment entries skipped; SELECT parsed for reporting |
| WORKING-STORAGE, LINKAGE, LOCAL-STORAGE, FILE SECTION | Verified (WS, LINKAGE); Parsed (FILE) | |
| Fixed format (cols 1-6, 7, 8-72), free format, `>>SOURCE`, `*>` | Verified | free format auto-detected |
| COPY, COPY … REPLACING `==a== BY ==b==`, word/literal replacing, `:TAG:` partial words | Verified (COPY), Unit (REPLACING) | REPLACE statement unsupported |
| PIC X / A / 9 / S / V, P scaling | Verified (P reported unsupported) | |
| Numeric-edited Z 9 , . + - $ * B 0 / CR DB, floating insertion, BLANK WHEN ZERO | Verified | includes GnuCOBOL behaviour when high-order digits are truncated |
| USAGE DISPLAY, SIGN LEADING/TRAILING [SEPARATE] | Verified / Unit | trailing overpunch `0x70-0x79` |
| COMP, BINARY, COMP-4, COMP-5, COMP-3/PACKED-DECIMAL, INDEX | Unit | binary-size 1-2-4-8, big-endian COMP, native COMP-5 |
| COMP-1, COMP-2, POINTER | Unsupported | Decimal-only policy |
| VALUE, 88-levels with lists and THRU, SET … TO TRUE | Verified | |
| REDEFINES (item and 01-level), OCCURS (nested), OCCURS DEPENDING ON | Verified / reported | ODO uses maximum size |
| Level 66 RENAMES | Unsupported | |
| MOVE (numeric, alphanumeric, group, figuratives, ALL literal, reference modification) | Verified | |
| COMPUTE ROUNDED / ON SIZE ERROR / NOT ON SIZE ERROR | Verified | 64-digit truncating intermediates; division by zero leaves receiver unchanged |
| ADD / SUBTRACT / MULTIPLY / DIVIDE (TO, FROM, BY, INTO, GIVING, REMAINDER) | Verified (REMAINDER unit) | CORRESPONDING unsupported |
| IF / ELSE / END-IF, NOT, AND, OR, abbreviated combined conditions | Verified | NEXT SENTENCE unsupported |
| Class conditions NUMERIC, ALPHABETIC[-LOWER/-UPPER], POSITIVE, NEGATIVE, ZERO | Verified (NUMERIC) / Unit | |
| EVALUATE subject(s) ALSO, TRUE/FALSE, ANY, THRU, NOT, WHEN OTHER | Verified | |
| PERFORM para [THRU para], TIMES, UNTIL, WITH TEST AFTER, VARYING … AFTER, inline | Verified | |
| GO TO para | Verified | GO TO DEPENDING ON unsupported |
| EXIT, EXIT PARAGRAPH, EXIT PROGRAM, EXIT PERFORM | Verified | EXIT SECTION / PERFORM CYCLE unsupported |
| CALL "literal" / identifier USING BY REFERENCE / CONTENT, ON EXCEPTION | Verified | BY VALUE, RETURNING unsupported |
| GOBACK, STOP RUN | Verified | |
| INITIALIZE | Verified | REPLACING unsupported |
| STRING … DELIMITED BY SIZE / literal, POINTER, ON OVERFLOW | Verified | |
| DISPLAY [UPON], WITH NO ADVANCING | Verified | elementary numerics use GnuCOBOL pretty-display |
| ACCEPT (stdin), FROM DATE [YYYYMMDD] / DAY [YYYYDDD] / TIME / DAY-OF-WEEK | Verified | COMMAND-LINE / ENVIRONMENT unsupported |
| FUNCTION INTEGER-OF-DATE, DATE-OF-INTEGER, TRIM | Verified | |
| FUNCTION UPPER-CASE, LOWER-CASE, LENGTH, MAX, MIN, ABS, MOD, REM, INTEGER, INTEGER-PART, NUMVAL, SUM, MEAN, … | Unit / Parsed | others reported |
| OPEN/CLOSE/READ/WRITE/REWRITE/DELETE/START, SORT/MERGE/RELEASE/RETURN | Unsupported | |
| INSPECT id TALLYING counter FOR ALL literal | Verified | literal = alphanumeric literal or figurative constant (one character); counts non-overlapping occurrences left to right in the item's storage bytes and ADDs them to the counter (never resets it); counter stores follow normal numeric truncation |
| INSPECT id REPLACING ALL literal BY literal | Verified | replacement must have the pattern's length (mismatch = `PRC003` error + Unsupported); a figurative replacement is repeated to the pattern length; reference modification allowed |
| Other INSPECT forms: TALLYING FOR CHARACTERS / LEADING, REPLACING CHARACTERS / LEADING / FIRST, BEFORE / AFTER INITIAL, CONVERTING, several FOR / BY operands or both TALLYING and REPLACING in one statement, identifier or numeric operands | Unsupported | reported with the statement's line range |
| INSPECT on signed numeric DISPLAY or COMP / COMP-3 items | Unsupported | GnuCOBOL strips the sign during INSPECT; the generator emits `UnsupportedConstruct` instead of guessing |
| UNSTRING, SEARCH, ALTER, CANCEL, ENTRY, EXEC SQL/CICS | Unsupported | |
| SCREEN / REPORT / COMMUNICATION SECTION, DECLARATIVES | Unsupported | |

## Numeric semantics (GnuCOBOL 3.2 default dialect)

* Stores truncate low-order digits unless ROUNDED (half away from zero) and truncate high-order digits unless
  ON SIZE ERROR is present (then the receiver is unchanged).
* Unsigned receivers store absolute values; `-0` is stored as `+0`.
* Reading a zoned digit uses `byte & 0x0F` (spaces read as zero), like GnuCOBOL.
* Alphanumeric → numeric DISPLAY moves follow `cob_move_alphanum_to_display` (digits right-aligned on the
  decimal point; leading spaces skipped). Non-numeric *literals* are converted at compile time by cobc and may
  differ (known limitation).
