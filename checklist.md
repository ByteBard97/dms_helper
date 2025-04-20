# Phase 2 Checklist: LLM Context Preparation

**Goal:** Prepare and structure background context for the LLM to act as a knowledgeable DM assistant.

- [ ] **Setup Context Directory Structure:**
  - [ ] Create base `context/` directory.
  - [ ] Create subdirectories: `context/adventures/`, `context/pcs/`, `context/rules/` (optional), `context/misc/` (optional).
- [ ] **PDF Adventure Conversion (using Marker):**
  - [ ] Add `marker-pdf` to `requirements.txt`.
  - [ ] Install `marker-pdf` and its dependencies (including PyTorch if not already sufficient).
  - [ ] Create script `src/convert_adventure_pdf.py`.
  - [ ] Implement logic in script to take input PDF path(s) and output Markdown to `context/adventures/`.
  - [ ] Process core adventure PDF(s).
- [ ] **Prepare Player Character (PC) Context:**
  - [ ] Define format for PC context files (e.g., `context/pcs/pc_name.md`).
  - [ ] Create/populate context files for each PC (Name, Race, Class, Backstory Summary, Key Relationships, Important Items, Goals/Motivations).
  - *Note: User will provide this information (e.g., from Google Docs).* 
- [ ] **Prepare Current Adventure State Context:**
  - [ ] Define format for `context/current_state.md`.
  - [ ] Create/populate the file with current location, recent events, active quests, key NPCs, immediate threats/goals.
  - *Note: User will provide this information. Needs manual updates during campaign.* 
- [ ] **Prepare Additional Context (Optional):**
  - [ ] Convert/add core rulebook sections (e.g., specific mechanics, spell lists) to `context/rules/` if needed.
  - [ ] Convert/add other relevant documents (world lore, house rules) to `context/misc/`.
  - *Note: User will provide source files (e.g., Google Docs).* 

# Phase 3 Checklist: Integration & Interaction (Outline)

- [ ] Integrate transcription output with LLM input.
- [ ] Develop prompt strategies for DM assistance (summarization, NPC roleplaying, rule lookups).
- [ ] Implement mechanism to load/use context files in LLM prompts.
- [ ] Potentially swap live mic input for file playback for testing/dev.
- [ ] *Future: GUI?* 