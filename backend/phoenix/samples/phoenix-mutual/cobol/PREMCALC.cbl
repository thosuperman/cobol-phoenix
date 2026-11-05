      *================================================================*
      * PREMCALC - Phoenix Mutual nightly auto premium rating batch    *
      *                                                                *
      * Reads policy requests (one 45-byte record per line) from       *
      * SYSIN until a blank line or END, calls RATEENG for each one    *
      * and prints a rating report with run totals.                    *
      * Copyright 2026 COBOL Phoenix authors                           *
      * SPDX-License-Identifier: Apache-2.0                            *
      *================================================================*
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PREMCALC.
       AUTHOR. COBOL PHOENIX SAMPLE.

       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY POLICY.
       COPY RATERES.
       01  WS-INPUT-LINE               PIC X(80).
       01  WS-EOF-SW                   PIC X(01) VALUE "N".
           88  WS-EOF                  VALUE "Y".
       01  WS-COUNTERS.
           05  WS-READ-COUNT           PIC 9(05) VALUE 0.
           05  WS-OK-COUNT             PIC 9(05) VALUE 0.
           05  WS-DECLINED-COUNT       PIC 9(05) VALUE 0.
           05  WS-INVALID-COUNT        PIC 9(05) VALUE 0.
       01  WS-TOTAL-PREMIUM            PIC 9(09)V99 VALUE 0.
       01  WS-TOTAL-EDIT               PIC $$$,$$$,$$9.99.
       01  WS-REPORT-LINE.
           05  RL-POLICY-ID            PIC X(10).
           05  FILLER                  PIC X(01) VALUE SPACE.
           05  RL-STATUS               PIC X(02).
           05  FILLER                  PIC X(01) VALUE SPACE.
           05  RL-REASON               PIC 9(03).
           05  FILLER                  PIC X(01) VALUE SPACE.
           05  RL-ANNUAL               PIC ZZZ,ZZ9.99.
           05  FILLER                  PIC X(01) VALUE SPACE.
           05  RL-INSTALLMENT          PIC ZZZ,ZZ9.99.
           05  FILLER                  PIC X(01) VALUE SPACE.
           05  RL-MESSAGE              PIC X(40).

       PROCEDURE DIVISION.
       0000-MAIN.
           DISPLAY "PHOENIX MUTUAL - AUTO PREMIUM RATING RUN"
           PERFORM 1000-READ-POLICY
           PERFORM 2000-RATE-POLICY UNTIL WS-EOF
           PERFORM 9000-SUMMARY
           STOP RUN.

       1000-READ-POLICY.
           ACCEPT WS-INPUT-LINE
           IF WS-INPUT-LINE = SPACES OR WS-INPUT-LINE (1:3) = "END"
              SET WS-EOF TO TRUE
           ELSE
              ADD 1 TO WS-READ-COUNT
              MOVE WS-INPUT-LINE TO POLICY-REC
           END-IF.

       2000-RATE-POLICY.
           CALL "RATEENG" USING POLICY-REC RATE-RESULT
           EVALUATE TRUE
              WHEN RR-OK
                 ADD 1 TO WS-OK-COUNT
                 ADD RR-ANNUAL-PREMIUM TO WS-TOTAL-PREMIUM
              WHEN RR-DECLINED
                 ADD 1 TO WS-DECLINED-COUNT
              WHEN OTHER
                 ADD 1 TO WS-INVALID-COUNT
           END-EVALUATE
           MOVE RR-POLICY-ID TO RL-POLICY-ID
           MOVE RR-STATUS TO RL-STATUS
           MOVE RR-REASON-CODE TO RL-REASON
           MOVE RR-ANNUAL-PREMIUM TO RL-ANNUAL
           MOVE RR-INSTALLMENT TO RL-INSTALLMENT
           MOVE RR-MESSAGE TO RL-MESSAGE
           DISPLAY WS-REPORT-LINE
           PERFORM 1000-READ-POLICY.

       9000-SUMMARY.
           MOVE WS-TOTAL-PREMIUM TO WS-TOTAL-EDIT
           DISPLAY "POLICIES READ     : " WS-READ-COUNT
           DISPLAY "RATED             : " WS-OK-COUNT
           DISPLAY "DECLINED          : " WS-DECLINED-COUNT
           DISPLAY "INVALID           : " WS-INVALID-COUNT
           DISPLAY "TOTAL PREMIUM     : " WS-TOTAL-EDIT.

       END PROGRAM PREMCALC.
