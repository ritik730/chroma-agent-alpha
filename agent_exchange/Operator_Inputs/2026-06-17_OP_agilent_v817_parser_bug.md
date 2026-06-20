# OPERATOR DIRECTION: Debugging Agilent .ch v817 Time-Scale and Intensity Offset
> From: Devendra Kataria (Operator / Research Director) | Date: 2026-06-17
> To: Dual-Agent System (Antigravity & Claude Code)

I noticed a major scaling issue in our parsed chromatograms from Agilent `.ch` v817 files. 
1. The elution times are stretched—it looks like the times are being extracted in raw milliseconds instead of minutes.
2. The peak heights do not match our reference standards, which indicates an intensity byte offset alignment issue in the Agilent v817 binary structure.

**My Requirements:**
1. I don't write binary parsers, but you need to check the Agilent v817 binary offset and time conversion multiplier. Convert raw ms to minutes and locate the double-precision float intensities (check the byte offset around 6144).
2. Write unit tests in `test_software_track.py` using our v817 sample files to verify the fix.
3. Run the full integration test `test_real_data_pipeline.py` to ensure everything is stable and bug-free.