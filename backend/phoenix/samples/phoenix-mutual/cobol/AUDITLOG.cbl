      *================================================================*
      * AUDITLOG - Appends rating results to the audit trail file.     *
      *                                                                *
      * Included to show how COBOL Phoenix reports constructs that are *
      * outside the supported subset (file I/O). INSPECT TALLYING is   *
      * supported; the file I/O statements are reported unsupported.   *
      * Copyright 2026 COBOL Phoenix authors                           *
      * SPDX-License-Identifier: Apache-2.0                            *
      *================================================================*
       IDENTIFICATION DIVISION.
       PROGRAM-ID. AUDITLOG.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT AUDIT-FILE ASSIGN TO "AUDITLOG.DAT"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS WS-AUDIT-STATUS.

       DATA DIVISION.
       FILE SECTION.
       FD  AUDIT-FILE.
       01  AUDIT-RECORD                PIC X(120).

       WORKING-STORAGE SECTION.
       01  WS-AUDIT-STATUS             PIC X(02).
       01  WS-SPACE-COUNT              PIC 9(03) VALUE 0.

       LINKAGE SECTION.
       COPY RATERES.

       PROCEDURE DIVISION USING RATE-RESULT.
       0000-MAIN.
           OPEN EXTEND AUDIT-FILE
           IF WS-AUDIT-STATUS NOT = "00"
              GOBACK
           END-IF
           INSPECT RR-MESSAGE TALLYING WS-SPACE-COUNT FOR ALL SPACES
           MOVE RATE-RESULT TO AUDIT-RECORD
           WRITE AUDIT-RECORD
           CLOSE AUDIT-FILE
           GOBACK.

       END PROGRAM AUDITLOG.
