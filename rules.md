# Last modified: 2026-07-03 18:46:58

## [File] Rule 1: Session Data Folder
- Store all session output files (downloads, generated text files, screenshots) within the active session folder.
- If no active session folder is set, stop and ask Ayush to specify one before writing any files.
- If you must write files outside the session folder, ask Ayush for permission first.

## [General] Rule 2: Notes & Context Scanning
- Before starting any task that explicitly references a project by name, read the notes file for that project if it exists.
- Do not scan notes for simple one-off tasks (calculations, web searches, file conversions).

- Fallback Strategy: If HTML/DOM interaction fails to locate an element, use OCR/Vision-based detection (browser_vision_read or vision_ocr_region) to identify and interact with the UI component.
