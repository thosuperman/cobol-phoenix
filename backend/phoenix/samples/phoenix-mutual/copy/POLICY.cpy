      *================================================================*
      * POLICY.cpy - Auto policy rating request (45 bytes)             *
      * Phoenix Mutual sample - Copyright 2026 COBOL Phoenix authors   *
      * SPDX-License-Identifier: Apache-2.0                            *
      *================================================================*
       01  POLICY-REC.
           05  PR-POLICY-ID            PIC X(10).
           05  PR-STATE                PIC X(02).
           05  PR-DRIVER-AGE           PIC 9(03).
           05  PR-YEARS-LICENSED       PIC 9(02).
           05  PR-VEHICLE-CLASS        PIC X(01).
               88  PR-VEH-SEDAN        VALUE "S".
               88  PR-VEH-SUV          VALUE "U".
               88  PR-VEH-TRUCK        VALUE "T".
               88  PR-VEH-SPORTS       VALUE "P".
               88  PR-VEH-VALID        VALUE "S" "U" "T" "P".
           05  PR-VEHICLE-VALUE        PIC 9(07)V99.
           05  PR-COVERAGE             PIC X(01).
               88  PR-COV-LIABILITY    VALUE "L".
               88  PR-COV-STANDARD     VALUE "S".
               88  PR-COV-FULL         VALUE "F".
           05  PR-DEDUCTIBLE           PIC 9(05).
           05  PR-CLAIMS-3YR           PIC 9(02).
           05  PR-VIOLATIONS-3YR       PIC 9(02).
           05  PR-MULTI-POLICY         PIC X(01).
               88  PR-HAS-MULTI-POLICY VALUE "Y".
           05  PR-ANNUAL-MILEAGE       PIC 9(06).
           05  PR-PAY-PLAN             PIC X(01).
               88  PR-PAY-ANNUAL       VALUE "A".
               88  PR-PAY-MONTHLY      VALUE "M".
