# Football Manager 26 - Native Backend Migration Architecture

## Goal
Move high-frequency, computation-heavy operations into a native C++ backend while keeping the accessible UI stable and keeping Python as the single source of truth for mutable game state during this phase.

## Phase strategy: stateless acceleration kernels first, larger kernels next
This phase deliberately avoids long-lived native state.

### Rules for this phase
- Python remains authoritative for **all mutable game state**.
- C++ is used for **stateless acceleration kernels** and carefully scoped heavy compute paths.
- No native game-state handle is persisted across UI actions.
- No native mutation result is applied unless it is computed from the **current Python snapshot** and returned immediately.
- The UI remains separate from the backend.

## Scope currently active in native code
Native C++ is used for:
- squad validation
- stadium upgrade cost preview
- club-record summarization
- youth-list summarization
- transfer-window status calculation

## Near-term native migration targets
Next heavy kernels to migrate safely:
- match simulation hardening and re-enablement
- contract negotiation evaluation
- youth evaluation helpers
- infrastructure cost-benefit calculations
- league table/stat summarization helpers

## Out of scope in this phase
The following remain Python-owned in this phase:
- week advancement as authoritative state mutation
- season progression as authoritative state mutation
- persistent native ownership of game state
- save/load ownership
- multiplayer state sync / server authority
- transfer completion / state mutation
- infrastructure mutation
- youth promotion mutation

## Why this strategy
This prevents split-brain state and keeps the migration safe:
- one source of truth for all live state
- native code accelerates repeatable hot paths only
- no stale native handle across UI operations
- easy parity testing between Python and native implementations

## Accessibility-first UI decision
The frontend remains separate and accessible.

### Framework review
I reviewed the practical choices for a Windows-first, NVDA-friendly management game UI:

- **wxPython / wxWidgets**
  - Pros:
    - Uses native controls on Windows.
    - Strong keyboard-first interaction model.
    - Good compatibility with screen readers when standard controls are used.
    - Already integrated in the project, so accessibility improvements can ship immediately.
  - Cons:
    - Styling is more limited than modern UI stacks.
    - Complex custom widgets can become awkward.

- **Qt for Python (PySide6)**
  - Pros:
    - More flexible layouts and styling.
    - Strong cross-platform maturity.
  - Cons:
    - Accessibility can be good, but real-world NVDA behavior varies more depending on custom widget usage.
    - Migration cost is meaningful.

- **WPF / WinUI (.NET)**
  - Pros:
    - Best Windows-native accessibility story in many cases.
    - Strong UI Automation support.
    - Rich styling and modern layout options.
  - Cons:
    - Requires a major stack migration.
    - Would split the project across Python/C++ and .NET unless the whole client is rethought.

- **Electron / Tauri / browser-shell UI**
  - Pros:
    - Fast iteration for visuals.
  - Cons:
    - Accessibility quality depends heavily on the exact implementation.
    - Keyboard/screen-reader experience can degrade quickly if not engineered very carefully.
    - Not my first recommendation for this project.

### Recommendation
- **Keep wxPython now** for the current accessible desktop client.
- Continue improving:
  - focus order,
  - heading hierarchy,
  - grouped navigation,
  - speech behavior,
  - contrast and spacing.
- Prepare a **future optional client migration path** to a Windows-native stack such as WPF/WinUI only if you later want a major UI rewrite with richer visuals and are willing to accept a bigger engineering change.

For this project today, the best balance is:
- **wxPython frontend** for accessibility and immediate productivity,
- **C++ backend** for heavy logic,
- clean bridge boundary between them.

## Architecture for this phase

### 1. UI layer
- `ui.py`
- Python / wxPython
- accessibility-focused
- no native state ownership

### 2. Bridge layer
- `engine_bridge.py`
- serializes Python snapshots per request
- calls native DLL if available
- parses results immediately
- frees native buffers centrally
- falls back to Python logic if native DLL is unavailable

### 3. Native backend layer
- `backend/CMakeLists.txt`
- `backend/include/fm_engine_api.h`
- `backend/src/match_engine.cpp`
- `backend/src/club_systems.cpp`
- `backend/src/persistence.cpp`
- `backend/src/api.cpp`
- stateless JSON-in / JSON-out kernels
- direct hot-path array-based XI validation API

## JSON dependency
This phase uses **header-only `nlohmann/json`**.

Vendored dependency path:
- `backend/third_party/nlohmann/json.hpp`

CMake includes:
- `backend/include`
- `backend/third_party`

## Native API in this phase
Stateful APIs are intentionally deferred.

### Exposed C API
- `FM_ResultBuffer fm_simulate_match_json(const char* match_json);`
- `FM_ResultBuffer fm_validate_squad_json(const char* squad_json);`
- `FM_ResultBuffer fm_validate_selected_xi(const int* player_ids, int count, const char* roster_json);`
- `FM_ResultBuffer fm_preview_stadium_upgrade_json(const char* stadium_json);`
- `FM_ResultBuffer fm_summarize_club_records_json(const char* records_json);`
- `FM_ResultBuffer fm_summarize_youth_players_json(const char* youth_json);`
- `FM_ResultBuffer fm_get_transfer_window_status_json(const char* date_json);`
- `FM_ResultBuffer fm_evaluate_contract_offer_json(const char* contract_json);`
- `const char* fm_backend_version(void);`
- `void fm_free_buffer(FM_ResultBuffer buffer);`

## Build scope in this phase
Only these sources are compiled in this phase:
- `backend/src/api.cpp`
- `backend/src/match_engine.cpp`
- `backend/src/club_systems.cpp`
- `backend/src/persistence.cpp`

These files are explicitly reserved for a future full-state migration and are **not** part of the current build target:
- `backend/src/game_state.cpp`
- `backend/src/season_engine.cpp`

## Validation approach
Validation must prove parity between Python and native for the active kernels:
- squad validation parity
- stadium preview parity
- transfer-window parity
- club-record summary parity
- youth summary parity
- contract evaluation parity
- toolchain/build presence and native DLL detection

## Future phase: full native state ownership
A future full-native phase must happen at a **single migration boundary**.

That future phase must migrate together:
- season advancement
- finance mutations
- player fitness/injury changes
- squad persistence
- save/load ownership

It must **not** be mixed with Python-owned mutable state.
