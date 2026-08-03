# 🤖 KLAUSE — Agentic AI Desktop Engineering Assistant

KLAUSE is a highly integrated, personal engineering companion and autonomous assistant designed for developers. It combines a real-time web-streaming UI, a robust ReAct (Reasoning and Acting) backend loop, local semantic memory mapping, desktop automation capability, and bidirectional Obsidian Vault integration to function as a powerful "second brain" and engineering partner.

---

## 🚀 Key Features

*   **🎙️ Interactive 3D Orb UI**: A React + Three.js dynamic orb that changes states (listening, processing, responding, idle, error) with smooth, cubic ease transitions, and smooth exponential moving average (EMA) voice amplitude visualization.
*   **🧠 Local & Semantic Memory (RAG)**: Leverages MongoDB and a persistent ChromaDB vector store. It automatically segments, indexes, and searches past chats, documents, and research data.
*   **📓 Obsidian Vault Integration**: Real-time bidirectional note synchronization. KLAUSE parses YAML frontmatter and inline `#tags` recursively from a configured vault folder, maps connections between questions and research documents, and builds visual connection flows inside a `KLAUSE_Connections.canvas` map.
*   **💻 OS & Desktop Automation**: Interacts with the local operating system (processes, active windows, clipboard monitoring) using a declarative rules engine and custom schedules.
*   **👁️ OCR Vision Engine**: Uses Tesseract OCR to read, parse, and interact with visual content and browser views.
*   **🔊 Real-time Speech Engine**: Features push-to-talk voice activation, SAPI text-to-speech feedback, and local transcription.

---

## 🛠️ Tech Stack

*   **Backend**: Python 3.10+, FastAPI, WebSockets, Uvicorn, Pydantic, Loguru.
*   **Databases**: MongoDB (local state/sessions/raw notes), ChromaDB (semantic vector embeddings).
*   **Frontend**: Vite, React 19, TypeScript 6, Zustand (State Management), Three.js (3D animation rendering), Lucide Icons.

---

## 📋 Prerequisites

To set up KLAUSE, ensure you have the following installed on your system:
*   **Python 3.10.x** or higher.
*   **Node.js v18.x** or higher (with `npm`).
*   **MongoDB Community Server** running locally on port `27017`.
*   **Tesseract OCR** installed on your system (e.g. `C:\Program Files\Tesseract-OCR\tesseract.exe`).

---

## ⚙️ Project Setup

Follow these steps to configure and run the entire KLAUSE system locally.

### 1. Backend Setup

1.  **Clone the Repository**:
    ```bash
    git clone <repository-url>
    cd KLAUSE
    ```

2.  **Create and Activate Virtual Environment**:
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    GEMINI_API_KEY=your_gemini_api_key_here
    ```

5.  **Configure System Settings**:
    Adjust the default wake word, personality model parameters, voice behavior, and path references in the `config.yaml` file located in the project root.

---

### 2. Frontend Setup

1.  **Navigate to the Frontend Directory**:
    ```bash
    cd frontend
    ```

2.  **Install NPM Packages**:
    ```bash
    npm install
    ```

3.  **Run the Vite Dev Server**:
    ```bash
    npm run dev
    ```
    The frontend will now be active at `http://localhost:5173`.

---

## 🏃 Running the Application

To start the full KLAUSE environment:

1.  Ensure your **local MongoDB** is running:
    ```bash
    mongod
    ```
2.  **Start the Backend API**:
    In the root project folder (with the virtual environment activated), run:
    ```bash
    python main.py
    ```
    This launches the FastAPI server on `http://127.0.0.1:8000` and configures SAPI voice threads.
3.  **Open the Web Dashboard**:
    Navigate to `http://localhost:5173` in your browser. Use the sidebar to switch between **Chat**, **Tasks**, **Rules**, and the **Knowledge Base** panels.

---

## 🧪 Running Tests

To execute backend unit tests for memory connectors and vault parsing, run:
```bash
python -m pytest
```
To run specific tests:
```bash
python -m pytest tests/test_obsidian_connector.py -v
```