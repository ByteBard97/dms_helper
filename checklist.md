# Phase 2 Checklist: LLM Context Preparation

**Goal:** Prepare and gather background context files for the LLM.

- [x] **PDF Adventure Conversion (using Marker):**
  - [x] Test `marker-pdf` installation.
  - [x] Create script `src/convert_adventure_pdf.py`.
  - [x] Implement logic to convert all PDFs in `source_materials/` to Markdown.
  - [x] Process core adventure PDF(s).
- [x] **Gather Player Character (PC) Context:**
  - [x] Ensure PC descriptions are available in a text/Markdown file (e.g., `source_materials/ceres_group/PC_descriptions.txt`).
  - *Note: User confirmed file exists and is sufficient for now.* 
- [x] **Gather Current Adventure State Context:**
  - [x] Create a text/Markdown file summarizing the current state (location, quests, NPCs, goals, etc.) (e.g., `source_materials/ceres_group/ceres_adventure_summary.md`).
  - *Note: User confirmed file exists and is up-to-date.* 
- [x] **Gather Additional Context (Optional):**
  - [x] Add any other relevant lore, rules, house rules etc. as text/Markdown files in `source_materials/`.
  - *Note: User confirmed no additional files needed for now.* 

**Approach Note:** Context will be loaded by reading all relevant `.md`/`.txt` files using campaign config files (e.g., `source_materials/ceres_group/ceres_odyssey.json`), rather than requiring specific structured files.

# Phase 3 Checklist: Integration & Interaction

**Goal:** Create the main application loop connecting transcription, context, and LLM.

- [x] **Create Core Application Script (`src/dms_assistant.py`):**
  - [x] Implement argument parsing for campaign config file.
- [x] **Integrate Context Loading:**
  - [x] Call `context_loader.load_and_combine_context` using the provided campaign config path in `dms_assistant.py`.
- [x] **Initialize LLM:**
  - [x] Load API key from `.env`.
  - [x] Initialize `genai.GenerativeModel` in `dms_assistant.py`.
  - [x] Start `ChatSession` using the loaded context from the previous step.
- [x] **Integrate Transcription Input (using File Playback first):**
  - [ ] Add argument parsing for input audio file path (e.g., FLAC). *Note: Currently hardcoded.* 
  - [x] Modify/create transcription client initialization to use `play_file()` method.
  - [x] Determine mechanism for receiving transcript segments when using file playback. *(Used output_queue)*
  - [x] Handle client connection/disconnection gracefully. *(Basic handling via sentinel/shutdown)*
- [x] **Implement Main Processing Loop:**
  - [x] Receive transcript segments from the file playback process.
  - [x] Clean transcript data (e.g., remove timestamps if present). *(Not currently needed)*
  - [x] Implement transcript accumulation logic (buffer segments based on pauses, sentence ends, time, etc.). *(Using NLTK)*
  - [x] Develop prompt templates/strategies for different tasks (e.g., "Summarize:", "Lookup rule:", "Roleplay NPC:"). *(Loaded base template)*
  - [x] Send formatted prompt (instruction + accumulated transcript) to the LLM `ChatSession`. *(Implemented conditionally based on gatekeeper)*
  - [x] Display the LLM's response to the user (console output). *(Implemented)*
  - [x] Handle end-of-file / graceful shutdown. *(Basic handling via sentinel/shutdown)*
- [x] **Refine and Test:**
  - [x] Test the end-to-end flow using the FLAC file. *(Completed)*
  - [x] Adjust transcript accumulation and prompting strategies based on results. *(Basic gatekeeper prompt tested, further refinement possible)*

- [ ] ***Future Enhancements (Phase 4+):***
  - [ ] Add live microphone input as an alternative mode.
  - [ ] **Develop a native GUI (Next Step):**
    - [ ] Choose library: **PyQt6** (Decision made).
    - [ ] Set up basic window structure.
    - [ ] Implement core display: Use **QTextBrowser** for scrollable, appendable LLM output.
    - [ ] Implement **Markdown-to-HTML** conversion (e.g., using `Markdown` library) before appending to `QTextBrowser`.
    - [ ] Apply basic **D&D-like styling** via CSS (fonts, colors).
    - [ ] Add text input field (Lower priority).
  - [ ] Investigate Gemini API context caching.
  - [ ] More sophisticated prompting and state management.
  - [ ] Implement local LLM/classifier pre-filter for transcript chunks to reduce cloud API calls (cost optimization).
  - [ ] Implement forced chunk flushing via keyword/button (manual "send now").
  - [ ] Add selective transcription controls for live mode (Push-to-talk, Wake Word).
  - [ ] Allow manual text input for direct LLM queries/commands.
  - [ ] Enhance console output rendering (e.g., better Markdown display).
  - [ ] Implement suggestion management features (copy, save, rate).
  - [ ] Explore dynamic prompting based on transcript content/intent.
  - [ ] Improve handling of `ASSISTANT_NEEDS_MORE_CONTEXT` responses.
  - [ ] Allow follow-up questions based on LLM responses.
  - [ ] Add commands for in-session context updates.
  - [ ] Investigate speaker diarization.
  - [ ] Explore transcription improvements (custom vocab, fine-tuning).
  - [ ] Error handling improvements (where allowed/appropriate). 