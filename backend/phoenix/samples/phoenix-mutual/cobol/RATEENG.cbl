      *================================================================*
      * RATEENG - Phoenix Mutual auto insurance rating engine          *
      *                                                                *
      * Called by PREMCALC with one policy request and returns the     *
      * rated premium. Original sample written for COBOL Phoenix.      *
      * Copyright 2026 COBOL Phoenix authors                           *
      * SPDX-License-Identifier: Apache-2.0                            *
      *================================================================*
       IDENTIFICATION DIVISION.
       PROGRAM-ID. RATEENG.
       AUTHOR. COBOL PHOENIX SAMPLE.
       DATE-WRITTEN. 2026-10-31.

       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-ZSERIES.
       OBJECT-COMPUTER. IBM-ZSERIES.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY RATETAB.
       01  WS-WORK-AREAS.
           05  WS-ST-SUB               PIC 9(02) VALUE 0.
           05  WS-STATE-FOUND-SW       PIC X(01) VALUE "N".
               88  WS-STATE-FOUND      VALUE "Y".
           05  WS-BASE-RATE            PIC 9(05)V99 VALUE 0.
           05  WS-VEH-FACTOR           PIC 9V999 VALUE 0.
           05  WS-COV-FACTOR           PIC 9V999 VALUE 0.
           05  WS-DED-FACTOR           PIC 9V999 VALUE 0.
           05  WS-VALUE-LOAD           PIC 9(07)V99 VALUE 0.
           05  WS-DISC-PCT             PIC S9(03)V99 COMP-3 VALUE 0.
           05  WS-MONTHLY-BASE         PIC 9(07)V9999 VALUE 0.
           05  WS-PREM-EDIT            PIC $$$,$$9.99.
       77  WS-POLICY-FEE               PIC 9(03)V99 VALUE 35.00.
       77  WS-MIN-PREMIUM              PIC 9(05)V99 VALUE 450.00.
       77  WS-MAX-RISK-POINTS          PIC 9(03) VALUE 12.

       LINKAGE SECTION.
       COPY POLICY.
       COPY RATERES.

       PROCEDURE DIVISION USING POLICY-REC RATE-RESULT.

       0000-MAIN.
           PERFORM 1000-INITIALIZE
           PERFORM 2000-VALIDATE THRU 2000-EXIT
           IF RR-INVALID
              GOBACK
           END-IF
           PERFORM 3000-LOOKUP-STATE
           IF NOT WS-STATE-FOUND
              SET RR-INVALID TO TRUE
              MOVE 105 TO RR-REASON-CODE
              MOVE "STATE NOT SERVED" TO RR-MESSAGE
              GOBACK
           END-IF
           PERFORM 4000-AGE-FACTOR
           PERFORM 4500-BASE-PREMIUM
           IF RR-INVALID
              GOBACK
           END-IF
           PERFORM 5000-RISK-ASSESSMENT
           IF RR-DECLINED
              GOBACK
           END-IF
           PERFORM 6000-DISCOUNTS
           PERFORM 7000-TOTALS
           PERFORM 8000-MESSAGE
           GOBACK.

       1000-INITIALIZE.
           INITIALIZE RATE-RESULT
           MOVE PR-POLICY-ID TO RR-POLICY-ID
           MOVE "N" TO WS-STATE-FOUND-SW
           MOVE ZERO TO WS-BASE-RATE WS-VALUE-LOAD WS-DISC-PCT
           MOVE 1 TO WS-VEH-FACTOR WS-COV-FACTOR WS-DED-FACTOR.

       2000-VALIDATE.
      * PM-101: A policy identifier is mandatory.
           IF PR-POLICY-ID = SPACES
              SET RR-INVALID TO TRUE
              MOVE 101 TO RR-REASON-CODE
              MOVE "POLICY ID REQUIRED" TO RR-MESSAGE
              GO TO 2000-EXIT
           END-IF
      * PM-102: Numeric fields must contain digits only.
           IF PR-DRIVER-AGE NOT NUMERIC
              OR PR-VEHICLE-VALUE NOT NUMERIC
              OR PR-ANNUAL-MILEAGE NOT NUMERIC
              SET RR-INVALID TO TRUE
              MOVE 102 TO RR-REASON-CODE
              MOVE "NON-NUMERIC INPUT" TO RR-MESSAGE
              GO TO 2000-EXIT
           END-IF
      * PM-103: Drivers must be between 16 and 99 years old.
           IF PR-DRIVER-AGE < 16 OR > 99
              SET RR-INVALID TO TRUE
              MOVE 103 TO RR-REASON-CODE
              MOVE "DRIVER AGE OUT OF RANGE" TO RR-MESSAGE
              GO TO 2000-EXIT
           END-IF
      * PM-104: Only sedan, SUV, truck and sports classes are rated.
           IF NOT PR-VEH-VALID
              SET RR-INVALID TO TRUE
              MOVE 104 TO RR-REASON-CODE
              MOVE "UNKNOWN VEHICLE CLASS" TO RR-MESSAGE
              GO TO 2000-EXIT
           END-IF
      * PM-106: Coverage must be liability, standard or full.
           IF NOT (PR-COV-LIABILITY OR PR-COV-STANDARD OR PR-COV-FULL)
              SET RR-INVALID TO TRUE
              MOVE 106 TO RR-REASON-CODE
              MOVE "UNKNOWN COVERAGE" TO RR-MESSAGE
              GO TO 2000-EXIT
           END-IF
      * PM-107: Years licensed cannot exceed age minus 16.
           IF PR-YEARS-LICENSED > PR-DRIVER-AGE - 16
              SET RR-INVALID TO TRUE
              MOVE 107 TO RR-REASON-CODE
              MOVE "YEARS LICENSED INCONSISTENT" TO RR-MESSAGE
           END-IF.
       2000-EXIT.
           EXIT.

       3000-LOOKUP-STATE.
      * PM-201: Base rate comes from the state rate table.
           PERFORM VARYING WS-ST-SUB FROM 1 BY 1
                   UNTIL WS-ST-SUB > 8 OR WS-STATE-FOUND
              IF ST-CODE (WS-ST-SUB) = PR-STATE
                 SET WS-STATE-FOUND TO TRUE
                 MOVE ST-BASE-RATE (WS-ST-SUB) TO WS-BASE-RATE
              END-IF
           END-PERFORM.

       4000-AGE-FACTOR.
      * PM-301: Driver age band factor.
           EVALUATE TRUE
              WHEN PR-DRIVER-AGE < 21
                 MOVE 1.850 TO RR-AGE-FACTOR
              WHEN PR-DRIVER-AGE < 25
                 MOVE 1.450 TO RR-AGE-FACTOR
              WHEN PR-DRIVER-AGE < 30
                 MOVE 1.150 TO RR-AGE-FACTOR
              WHEN PR-DRIVER-AGE < 60
                 MOVE 1.000 TO RR-AGE-FACTOR
              WHEN PR-DRIVER-AGE < 70
                 MOVE 1.080 TO RR-AGE-FACTOR
              WHEN OTHER
                 MOVE 1.250 TO RR-AGE-FACTOR
           END-EVALUATE
      * PM-302: Inexperienced drivers pay a 10 percent loading.
           IF PR-YEARS-LICENSED < 3
              COMPUTE RR-AGE-FACTOR ROUNDED = RR-AGE-FACTOR * 1.100
           END-IF.

       4500-BASE-PREMIUM.
      * PM-401: Vehicle class and coverage interaction factor.
           EVALUATE PR-VEHICLE-CLASS ALSO PR-COVERAGE
              WHEN "P" ALSO "F"
                 MOVE 1.600 TO WS-VEH-FACTOR
              WHEN "P" ALSO ANY
                 MOVE 1.350 TO WS-VEH-FACTOR
              WHEN "U" ALSO ANY
                 MOVE 1.120 TO WS-VEH-FACTOR
              WHEN "T" ALSO "L"
                 MOVE 0.950 TO WS-VEH-FACTOR
              WHEN "T" ALSO ANY
                 MOVE 1.050 TO WS-VEH-FACTOR
              WHEN OTHER
                 MOVE 1.000 TO WS-VEH-FACTOR
           END-EVALUATE
      * PM-402: Coverage factor; full coverage adds 1.25 percent of
      *         the insured vehicle value.
           EVALUATE TRUE
              WHEN PR-COV-LIABILITY
                 MOVE 0.650 TO WS-COV-FACTOR
              WHEN PR-COV-STANDARD
                 MOVE 1.000 TO WS-COV-FACTOR
              WHEN PR-COV-FULL
                 MOVE 1.000 TO WS-COV-FACTOR
                 COMPUTE WS-VALUE-LOAD ROUNDED =
                         PR-VEHICLE-VALUE * 0.0125
           END-EVALUATE
      * PM-403: Deductible credit (not applicable to liability).
           IF NOT PR-COV-LIABILITY
              EVALUATE PR-DEDUCTIBLE
                 WHEN 0 THRU 249
                    MOVE 1.100 TO WS-DED-FACTOR
                 WHEN 250 THRU 499
                    MOVE 1.000 TO WS-DED-FACTOR
                 WHEN 500 THRU 999
                    MOVE 0.920 TO WS-DED-FACTOR
                 WHEN OTHER
                    MOVE 0.850 TO WS-DED-FACTOR
              END-EVALUATE
           END-IF
      * PM-404: Base premium.
           COMPUTE RR-BASE-PREMIUM ROUNDED =
                   WS-BASE-RATE * RR-AGE-FACTOR * WS-VEH-FACTOR
                 * WS-COV-FACTOR * WS-DED-FACTOR + WS-VALUE-LOAD
              ON SIZE ERROR
                 SET RR-INVALID TO TRUE
                 MOVE 190 TO RR-REASON-CODE
                 MOVE "PREMIUM OVERFLOW" TO RR-MESSAGE
           END-COMPUTE.

       5000-RISK-ASSESSMENT.
      * PM-501: Claims count 3 points, violations 2 points.
           COMPUTE RR-RISK-POINTS =
                   PR-CLAIMS-3YR * 3 + PR-VIOLATIONS-3YR * 2
      * PM-502: Too many risk points means the risk is declined.
           IF RR-RISK-POINTS > WS-MAX-RISK-POINTS
              SET RR-DECLINED TO TRUE
              MOVE 201 TO RR-REASON-CODE
              MOVE "RISK POINTS EXCEED UNDERWRITING LIMIT"
                TO RR-MESSAGE
           ELSE
      * PM-503: High annual mileage adds two risk points.
              IF PR-ANNUAL-MILEAGE > 20000
                 ADD 2 TO RR-RISK-POINTS
              END-IF
      * PM-504: Surcharge is 4 percent of base premium per point.
              COMPUTE RR-SURCHARGE ROUNDED =
                      RR-BASE-PREMIUM * RR-RISK-POINTS * 0.04
           END-IF.

       6000-DISCOUNTS.
      * PM-601: Clean record with 5+ years licensed earns 10 percent.
           IF RR-RISK-POINTS = 0 AND PR-YEARS-LICENSED >= 5
              ADD 10.00 TO WS-DISC-PCT
           END-IF
      * PM-602: Multi-policy households earn 7.5 percent.
           IF PR-HAS-MULTI-POLICY
              ADD 7.50 TO WS-DISC-PCT
           END-IF
      * PM-603: Low mileage earns 5 percent.
           IF PR-ANNUAL-MILEAGE < 7500
              ADD 5 TO WS-DISC-PCT
           END-IF
      * PM-604: Total discount is capped at 20 percent.
           IF WS-DISC-PCT > 20
              MOVE 20 TO WS-DISC-PCT
           END-IF
           COMPUTE RR-DISCOUNT ROUNDED =
                   (RR-BASE-PREMIUM + RR-SURCHARGE) * WS-DISC-PCT / 100.

       7000-TOTALS.
      * PM-701: Annual premium includes the policy fee and a minimum.
           COMPUTE RR-ANNUAL-PREMIUM ROUNDED =
                   RR-BASE-PREMIUM + RR-SURCHARGE - RR-DISCOUNT
                 + WS-POLICY-FEE
           IF RR-ANNUAL-PREMIUM < WS-MIN-PREMIUM
              MOVE WS-MIN-PREMIUM TO RR-ANNUAL-PREMIUM
           END-IF
      * PM-702: Monthly plans carry a 3.5 percent installment load.
           IF PR-PAY-MONTHLY
              COMPUTE WS-MONTHLY-BASE = RR-ANNUAL-PREMIUM * 1.035
              DIVIDE WS-MONTHLY-BASE BY 12
                 GIVING RR-INSTALLMENT ROUNDED
           ELSE
              MOVE RR-ANNUAL-PREMIUM TO RR-INSTALLMENT
           END-IF
           SET RR-OK TO TRUE
           MOVE ZERO TO RR-REASON-CODE.

       8000-MESSAGE.
           MOVE RR-ANNUAL-PREMIUM TO WS-PREM-EDIT
           MOVE SPACES TO RR-MESSAGE
           STRING "RATED " DELIMITED BY SIZE
                  PR-STATE DELIMITED BY SIZE
                  " " DELIMITED BY SIZE
                  PR-VEHICLE-CLASS DELIMITED BY SIZE
                  "/" DELIMITED BY SIZE
                  PR-COVERAGE DELIMITED BY SIZE
                  " " DELIMITED BY SIZE
                  WS-PREM-EDIT DELIMITED BY SIZE
                  INTO RR-MESSAGE
           END-STRING.

       END PROGRAM RATEENG.
