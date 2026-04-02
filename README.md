# Football Manager 26 - Accessible Edition

Accessible football management game with a Python/wxPython UI and a progressively migrating native backend.

## Features
- Screen-reader-friendly desktop UI
- Local saves
- Dark mode UI
- Transfer market, squad management, youth, infrastructure, finances
- Native backend bridge for heavy/stateless engine paths
- Multiplayer server prototype for remote quick matches

## Project structure
- `ui.py` - desktop UI
- `game_engine.py` - backend orchestration/game logic
- `match_engine.py` - Python match engine/fallbacks
- `engine_bridge.py` - bridge to native backend DLL
- `backend/` - C++ native backend
- `services/` - application/service façade modules
- `multiplayer_server/` - lightweight multiplayer relay server

## Running locally
```bash
python main.py
```

## Native backend
The native backend can be built on Windows using CMake/MSVC. The Python app will fall back gracefully if the DLL is unavailable.

## Multiplayer server
The `multiplayer_server` directory contains a simple Python room/relay server intended as the first hosted multiplayer step.

## GitHub Actions
This repository is prepared for:
- CI validation on push
- Windows `.exe` release builds on tags
- optional automated tagging via a Python script
