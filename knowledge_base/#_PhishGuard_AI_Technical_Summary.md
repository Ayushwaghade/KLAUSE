---
note_id: 6a455448be9580c09bb4b0a9
project_id: None
tags:
  - phishguard
  - ai
  - security
  - documentation
  - klause-note
  - migrated
created: 2026-07-01 17:54
---

# PhishGuard AI: Technical Summary

**What it is:** A proactive, real-time phishing detection system comprising a Chrome Extension (frontend) and a Python FastAPI server (backend).

**Core Components:**
- **Chrome Extension (Manifest V3):** Monitors navigation, intercepts forms, and provides real-time warnings via a UI isolated in the Shadow DOM.
- **Python Backend:** Uses FastAPI to process URL analysis, feature extraction, ML classification (XGBoost), and external API checks.

**The 7-Step Detection Pipeline:**
1. **Trusted Domain Fast-Path:** Instant pass for a whitelist of over 40 known sites.
2. **Feature Extraction:** Extracts 55 distinct URL features (length, protocols, character ratios, etc.) without network requests.
3. **ML Prediction:** Analyzes features using a pre-trained XGBoost model, with a heuristic fallback.
4. **Domain Similarity:** Uses fuzzy string matching (rapidfuzz) to detect brand impersonation (e.g., 'paypa1.com').
5. **Risk Scoring:** Aggregates signals (SSL validity, keywords, form actions, etc.) to produce a 0–100 risk score (Safe, Suspicious, Dangerous).
6. **SSL Verification:** Performs a real TLS handshake to validate certificates.
7. **Google Safe Browsing API:** A final cross-reference against global threat databases.

**Key Strengths:**
- **Proactive:** Catches zero-day threats that traditional blocklists miss.
- **DOM Awareness:** Unlike URL-only scanners, it inspects page content for password fields, external form actions, and clickjacking elements (iframes).