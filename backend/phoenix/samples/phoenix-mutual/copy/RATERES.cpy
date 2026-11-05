      *================================================================*
      * RATERES.cpy - Rating result returned by RATEENG (107 bytes)    *
      * SPDX-License-Identifier: Apache-2.0                            *
      *================================================================*
       01  RATE-RESULT.
           05  RR-POLICY-ID            PIC X(10).
           05  RR-STATUS               PIC X(02).
               88  RR-OK               VALUE "OK".
               88  RR-DECLINED         VALUE "DC".
               88  RR-INVALID          VALUE "IV".
           05  RR-REASON-CODE          PIC 9(03).
           05  RR-BASE-PREMIUM         PIC 9(07)V99.
           05  RR-AGE-FACTOR           PIC 9V999.
           05  RR-RISK-POINTS          PIC 9(03).
           05  RR-SURCHARGE            PIC 9(07)V99.
           05  RR-DISCOUNT             PIC 9(07)V99.
           05  RR-ANNUAL-PREMIUM       PIC 9(07)V99.
           05  RR-INSTALLMENT          PIC 9(07)V99.
           05  RR-MESSAGE              PIC X(40).
