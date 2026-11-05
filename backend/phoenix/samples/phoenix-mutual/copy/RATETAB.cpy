      *================================================================*
      * RATETAB.cpy - State base rates (REDEFINES + OCCURS table)      *
      * SPDX-License-Identifier: Apache-2.0                            *
      *================================================================*
       01  STATE-RATE-VALUES.
           05  FILLER  PIC X(09) VALUE "CA0118500".
           05  FILLER  PIC X(09) VALUE "NY0132050".
           05  FILLER  PIC X(09) VALUE "TX0098000".
           05  FILLER  PIC X(09) VALUE "FL0141075".
           05  FILLER  PIC X(09) VALUE "WA0089025".
           05  FILLER  PIC X(09) VALUE "IL0101000".
           05  FILLER  PIC X(09) VALUE "OH0076040".
           05  FILLER  PIC X(09) VALUE "AZ0099510".
       01  STATE-RATE-TABLE REDEFINES STATE-RATE-VALUES.
           05  STATE-ENTRY OCCURS 8 TIMES.
               10  ST-CODE             PIC X(02).
               10  ST-BASE-RATE        PIC 9(05)V99.
