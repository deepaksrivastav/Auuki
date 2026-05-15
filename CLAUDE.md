# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pnpm install          # Install dependencies
pnpm start            # Dev server with hot reload (Parcel)
pnpm run starttls     # Dev server with TLS (needed for Web Bluetooth in some cases)
pnpm run build        # Production build
pnpm test             # Run Jest tests
pnpm test -- --testPathPattern=functions  # Run a single test file
```

## Architecture

**Auuki** is a browser-only PWA for structured indoor cycling on smart trainers. No backend — all data lives in IndexedDB/LocalStorage. Built with vanilla JS + Web Components, bundled by Parcel 2.

### Core Data Flow

Reactive Flux pattern: `db.js` defines global app state, `src/models/models.js` registers models with validation/storage, and `xf` (the dispatcher) propagates events. Components subscribe to state via the `DataView` base class in `src/views/data-views.js`.

### Major Subsystems

**Device Connectivity** (`src/ble/`, `src/ant/`)
- `src/ble/devices.js` — factory that maps Bluetooth GATT services to protocol handlers
- Each `src/ble/<service>/` folder implements a specific BLE profile (FTMS, CPS, CSCS, HRS, Moxy, etc.)
- `src/ant/` handles ANT+ via Web Serial; `src/ant/fec.js` is the trainer control protocol
- `reactive-connectable.js` wraps BLE connections with reactive state

**Workout Engine** (`src/workouts/`, `watch.js`, `timer.js`)
- `src/workouts/zwo.js` parses Zwift `.zwo` XML files
- `watch.js` runs the workout state machine (interval progression, ERG/slope targets)
- `timer.js` is a Web Worker for precise 1-second tick timing

**Activity Recording** (`src/fit/`)
- `src/fit/fit.js` / `fitjs.js` generate FIT files (industry-standard format used by Garmin, Strava, etc.)
- `src/fit/profiles/` define FIT message types and field encodings

**Physics** (`physics.js`)
- Power-to-speed and grade simulation math
- Used by the workout engine for slope-based ERG targeting

**UI** (`src/views/`)
- Web Components (custom elements); `DataView` is the reactive base class
- `src/views/workout-graph.js` — SVG graph for workout visualization
- `src/views/editor.js` — in-browser workout editor

**Storage** (`src/storage/`)
- `idb.js` — IndexedDB wrapper for activities and workouts
- `local-storage.js` — user settings and preferences

**Integrations** (`src/models/api.js`)
- Intervals.icu and Strava upload via fetch; no server proxy

### Key Files

| File | Purpose |
|---|---|
| `src/index.js` | App bootstrap; wires models, views, and BLE initialization |
| `db.js` | Single source of truth — all state keys defined here |
| `src/models/models.js` | Model factory: validation, persistence, default values |
| `src/models/enums.js` | App-wide constants |
| `functions.js` | Functional utilities (pure functions, tested) |
| `utils.js` | DOM/browser utilities |
| `src/sw.js` | Service Worker (cache version `Flux-v008`; registration currently commented out in `index.js`) |

## Testing

Jest 27 + Babel (CommonJS transform for tests only via `.babelrc`). Test files live in `/test`. `fake-indexeddb` mocks IndexedDB.

## Browser Requirements

Chrome/Edge/Opera/Brave only — Web Bluetooth API is required and not available in Firefox or Safari.
