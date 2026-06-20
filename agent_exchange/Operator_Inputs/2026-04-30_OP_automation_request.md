# OPERATOR DIRECTION: Designing a Zero-Touch Lab Automation Workflow
> From: Devendra Kataria (Operator / Research Director) | Date: 2026-04-30
> To: Dual-Agent System (Antigravity & Claude Code)

I want to demonstrate a "Lab 4.0" automation concept. I should be able to drop a raw chromatography file into a directory, and the system should automatically trigger the ingestion, baseline correction, and peak integration, returning a clean summary table.

**My Requirements:**
1. Design a folder watcher that triggers our pipeline automatically. Set up an n8n webhook workflow on port 5678 and connect it to a FastAPI server backend on port 8001.
2. Establish a double-loop check. Antigravity must validate script compilation and package imports in a separate Ghost Runtime first (Loop 1), and then Claude Code must verify the logic and commit the changes (Loop 2). This ensures no broken code enters our repository.