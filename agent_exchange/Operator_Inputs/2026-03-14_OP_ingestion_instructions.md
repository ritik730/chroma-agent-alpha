# OPERATOR DIRECTION: Conception of Vendor-Independent Ingestion
> From: Devendra Kataria (Operator / Research Director) | Date: 2026-03-14
> To: Dual-Agent System (Antigravity & Claude Code)

I want to build a vendor-independent chromatography ETL pipeline. I have raw chromatogram files from Varian (.xms/.sms) and Agilent (.ch) systems. I do not want to rely on their expensive proprietary desktop software or GUI wrappers. 

As a researcher, I want our workflow to be open and automated. I don't write low-level code, so I need you to build custom binary parsers in Python that can read these raw byte streams directly.

**My Requirements:**
1. Extract the time and intensity data cleanly so we can feed them into standard arrays.
2. The code must run efficiently on our Dell Latitude 5300 (16GB RAM). Keep the local system clean; route all model inference through the cloud via OpenRouter.
3. Validate your output against open NetCDF (.cdf) formats to ensure we aren't losing data resolution during ingestion.