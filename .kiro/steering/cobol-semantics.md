---
inclusion: fileMatch
fileMatchPattern: "backend/phoenix/{cobol,codegen,verify}/**/*.py"
---

# COBOL semantics the generator must preserve

These rules mirror GnuCOBOL 3.2 default dialect behaviour and are enforced by
`phoenix_runtime` and its tests.

- **Storage is byte based.** Each 01/77 record is a `bytearray`; elementary items are views
  (offset, length, PICTURE). Group MOVE, REDEFINES and ACCEPT/DISPLAY of groups are byte
  operations, exactly like COBOL.
- **USAGE DISPLAY numerics** are zoned ASCII digits; a negative trailing sign is an
  overpunch (`0x40` added to the last digit, e.g. `-12` in `S9(3)` → `01r`).
  `SIGN LEADING/TRAILING SEPARATE` stores `+`/`-`.
- **Reading a digit** uses `byte & 0x0F` (so spaces read as 0), matching GnuCOBOL.
- **Stores** (MOVE / arithmetic): decimal-point alignment, low-order truncation, high-order
  truncation (no SIZE ERROR), unsigned receivers store the absolute value.
- **ROUNDED** = round half away from zero (`ROUND_HALF_UP`). Without ROUNDED: truncate.
- **ON SIZE ERROR**: the receiver is left unchanged and the imperative branch runs.
- **Intermediate arithmetic** uses a 64-digit `Decimal` context with `ROUND_DOWN`,
  approximating GnuCOBOL's arbitrary-precision intermediates with truncating division.
- **Alphanumeric MOVE**: left-justify, pad with spaces, truncate on the right.
- **Comparisons**: numeric vs numeric by value; otherwise alphanumeric with the shorter
  operand padded with spaces. Figurative constants adapt to the other operand.
- **88-levels**: VALUE lists and THRU ranges; `SET cond TO TRUE` moves the first value.
- **INITIALIZE**: alphanumeric → spaces, numeric → zero, FILLER untouched.
- **PERFORM** ranges execute paragraphs in source order; `EXIT PARAGRAPH` leaves the current
  paragraph; `GOBACK`/`STOP RUN` end the program.
- **CALL ... USING** passes by reference: the callee's LINKAGE records alias the caller's
  storage. Working storage of a called program persists between calls.
