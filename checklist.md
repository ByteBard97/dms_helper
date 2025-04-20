# Phase 2 Checklist: LLM Context Preparation

**Goal:** Prepare and gather background context files for the LLM.

- [x] **PDF Adventure Conversion (using Marker):**
  - [x] Test `marker-pdf` installation.
  - [x] Create script `src/convert_adventure_pdf.py`.
  - [x] Implement logic to convert all PDFs in `source_materials/` to Markdown.
  - [x] Process core adventure PDF(s).
- [ ] **Gather Player Character (PC) Context:**
  - [ ] Ensure PC descriptions are available in a text/Markdown file (e.g., `source_materials/PC_descriptions.txt`).
  - *Note: User to provide/confirm this file.* 
- [ ] **Gather Current Adventure State Context:**
  - [ ] Create a text/Markdown file summarizing the current state (location, quests, NPCs, goals, etc.) (e.g., `source_materials/current_state.md`).
  - *Note: User to create and maintain this file.* 
- [ ] **Gather Additional Context (Optional):**
  - [ ] Add any other relevant lore, rules, house rules etc. as text/Markdown files in `source_materials/`.
  - *Note: User to provide source files (e.g., from Google Docs).* 

**Approach Note:** Context will be loaded by reading all relevant `.md`/`.txt` files from `source_materials/` and combined into the initial LLM prompt/history, rather than requiring specific structured files.

# Phase 3 Checklist: Integration & Interaction (Outline)

- [ ] Create main interaction loop script.
- [ ] Implement loading/combining of all context files from `source_materials/`.
- [ ] Initialize LLM (Gemini) chat session with combined context.
- [ ] Integrate real-time transcription (from `WhisperLive` client or file playback).
- [ ] Develop prompt strategy: Send accumulated transcript segments + specific query/task to LLM.
- [ ] Display LLM responses.
- [ ] *Future: GUI, File Playback Input Option, Context Caching, More Sophisticated Prompting/Summarization.* 