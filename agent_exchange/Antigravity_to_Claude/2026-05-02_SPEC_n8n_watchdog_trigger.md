# SPECIFICATION: n8n Folder Watcher & Server Ingestion Trigger
> Prepared by: Antigravity (Macro Brain) | Date: 2026-05-02
> Task: [TASK → CC] T1: Build watchdog folder watcher and n8n webhook API server triggers.

## 1. Goal
Automate the data ingestion pipeline so that raw instrument data dropped into a directory triggers the ETL pipeline without manual operator intervention.

## 2. Requirements
*   **Watchdog Script:** Monitor `raw_data/` for new files ending in `.ch`, `.xms`, `.cdf`, or `.mzML`.
*   **FastAPI backend:** Expose a POST endpoint `/process_sample` on port `8001`.
*   **n8n Webhook:** Create a local n8n workflow on port `5678` that triggers the FastAPI server webhook on new folder drops.