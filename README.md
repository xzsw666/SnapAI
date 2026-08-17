# SnapAI

SnapAI is a Windows desktop AI tool for extracting text from selected screen regions and writing the recognized text to the system clipboard.

Current version: v0.1

## Current Phase

Phase 1 only initializes the project structure. It does not implement global shortcuts, screen selection, screenshots, Vision AI calls, GUI behavior, or clipboard writing.

## Architecture

```text
Shortcut
   ↓
App
   ↓
Selector
   ↓
Screenshot
   ↓
Recognition
   ↓
Clipboard
```

## Phase 1 Scope

The initial project structure contains:

```text
SnapAI/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── docs/
│   └── PRD.md
├── .gitignore
└── .env.example
```

See `docs/PRD.md` for the product requirements.
