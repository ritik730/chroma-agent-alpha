# AGENT EXCHANGE
> Shared communication and context directory for CHROMA-AGENT-ALPHA.

This folder serves as the central hub for the dual-agent architecture (Antigravity & Claude Code) and the Operator (Devendra Kataria).

## Folder Structure

- **`Antigravity_to_Claude/`** 
  - **Purpose:** Antigravity (Macro Brain) drops task briefs, architecture plans, and Loop 1 PASS/FAIL reports here for Claude Code to execute.
  - **Ownership:** Only Antigravity creates files here; Claude Code reads them.

- **`Claude_to_Antigravity/`** 
  - **Purpose:** Claude Code (Micro Engine) drops Loop 2 PASS/FAIL logs, execution delta reports, data files for the manuscript, and requests for validation here for Antigravity.
  - **Ownership:** Only Claude Code creates files here; Antigravity reads them.

- **`Operator_Inputs/`** 
  - **Purpose:** The Operator (Devendra Kataria) drops external context, internet updates, new skills, academic feedback, or manual instructions here for both agents.
  - **Ownership:** Managed by the Operator. Both agents monitor this folder for new instructions.
