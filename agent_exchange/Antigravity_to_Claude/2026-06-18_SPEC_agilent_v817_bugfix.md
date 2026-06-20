# SPECIFICATION: Agilent .ch v817 Time-Scale & Float Offset Bugfix
> Prepared by: Antigravity (Macro Brain) | Date: 2026-06-18
> Task: [TASK → CC] T3: Resolve Agilent v817 parser scaling and double offset issue.

## 1. Goal
Fix the parser bug in Agilent `.ch` v817 binary files where elution time arrays are parsed in raw milliseconds rather than minutes, and intensity double-precision float arrays read from the incorrect binary offset.

## 2. Requirements
*   **Time Scaling:** Convert milliseconds to minutes.
*   **Double Offset:** Locate flat little-endian doubles starting from offset 6144.
*   **Unit Tests:** Add test case validation in `test_software_track.py` and run a full integration test.