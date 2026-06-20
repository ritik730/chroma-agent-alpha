# CLAUDE EXCHANGE INSTRUCTIONS
> Context File for Claude Code (Micro Engine) regarding the AGENT_EXCHANGE Directory
> Read this to understand how to interact with Antigravity and the Operator.

---

## 1. WHAT IS THE AGENT_EXCHANGE FOLDER?

The `AGENT_EXCHANGE` directory is the central communication and synchronization hub for the CHROMA-AGENT-ALPHA dual-agent architecture. Since you (Claude Code) and Antigravity (Macro Brain) operate in separate sessions, this folder is the **only** way you communicate, exchange files, and hand off tasks.

**Location:** `C:\Users\yaduv\Desktop\AGENT_EXCHANGE`

---

## 2. FOLDER STRUCTURE & YOUR RESPONSIBILITIES

### A. `Antigravity_to_Claude/` (Your INBOX)
- **Purpose:** Antigravity drops task briefs, architecture specifications, and Loop 1 validation results here for you to execute.
- **Your Action:** **READ ONLY.** Check this folder at the start of your session or when instructed. Implement the code exactly as specified in the markdown briefs found here. Do not alter the files in this directory.
- **Current Pending Files:** `TASK_BRIEF_FOR_CLAUDE_CODE.md` is waiting for you here.

### B. `Claude_to_Antigravity/` (Your OUTBOX)
- **Purpose:** This is where you drop your outputs for Antigravity to review and integrate into the master project or manuscript.
- **Your Action:** **WRITE ONLY.** Drop the following items here:
  - Loop 2 PASS/FAIL audit logs.
  - Execution delta reports.
  - Data outputs (like JSON arrays, SHAP/UMAP plots).
  - Any requests for validation from Antigravity.
- **Constraint:** Ensure files are clearly named (e.g., `loop2_audit_YYYYMMDD.txt` or `chroma_report_YYYYMMDD.json`) so Antigravity can easily parse them.

### C. `Operator_Inputs/` (Global INBOX)
- **Purpose:** The Operator (Devendra Kataria) will drop external context, internet updates, new skills, academic feedback, or manual overrides here.
- **Your Action:** **MONITOR.** Both you and Antigravity must check this folder for new instructions or shifts in the project scope. Incorporate these updates into your context immediately upon reading.

---

## 3. YOUR WORKFLOW WITH AGENT_EXCHANGE

1. **Start of Session:** 
   - Check `Operator_Inputs/` for any manual overrides.
   - Check `Antigravity_to_Claude/` for new task briefs.
2. **Execution:** 
   - Write/edit the required Python scripts (`gnn_deconv.py`, `spectral_match.py`, etc.) in the project directory based on Antigravity's specifications.
3. **Loop 2 Audit:** 
   - Run your Loop 2 Audit on the implemented code.
4. **Handoff:** 
   - Generate the audit report and any required data files.
   - Save these outputs directly into the `Claude_to_Antigravity/` folder.
   - Notify the Operator that your tasks are complete and outputs are ready for Antigravity.

---

## 4. STRICT RULES
- **DO NOT** delete files from `Antigravity_to_Claude/`.
- **DO NOT** place your output files randomly in the root folder; always route them through `Claude_to_Antigravity/`.
- **DO NOT** rewrite architecture plans. If an implementation fails Loop 2 and cannot be fixed, write a failure report and place it in `Claude_to_Antigravity/` for Antigravity to handle.

---

## 5. GSD METHODOLOGY (MISSION CONTROL RULES)

When operating within or interacting with the `AGENT_EXCHANGE` folder, you MUST adhere to the following protocols based on the **Get Shit Done (GSD)** methodology:

1. **Plan Before You Build**: Do not execute code changes without a finalized specification. Always check the exchange folder for spec updates (`TASK_BRIEF_FOR_CLAUDE_CODE.md`) first.
2. **State Is Sacred**: Every completed task or significant action must be recorded in persistent memory. Update `STATE.md` or the corresponding status log in the `Claude_to_Antigravity/` folder after each major task.
3. **Context Is Limited**: Prevent degradation through context hygiene. Do not pollute the exchange folder with temporary files, scratch pads, or intermediate debug logs. Only place finalized, spec-driven outputs in this directory.
4. **Verify Empirically**: Before marking a task as "Done", empirical proof of validation must be captured and documented in the exchange space. No "trust me, it works"—provide the failing/passing test output or execution delta reports.
5. **Separation of Duties**: You (Micro Engine) handle targeted coding, refactoring, and localized problem-solving. Antigravity (Macro Brain) handles the planning and architecture. Stick to your role.

### Integration Protocol Recap
Actively read from and write to the `AGENT_EXCHANGE` directory to maintain alignment with the latest project context, architecture, and validation requirements set by Antigravity. Always update the state persistence after each task.
