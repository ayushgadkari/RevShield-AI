# 🚀 RevShield AI - Quick Start & Running Guide

Welcome to **RevShield AI**, an autonomous payment failure recovery and risk-management microservice powered by FastAPI and Google Gemini Flash (`gemini-3.6-flash`).

---

## 📋 Prerequisites

Before running the project, ensure you have:
1. Python (3.9 or higher) installed.
2. A free Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/).

---

## 🛠️ Step-by-Step Setup & Execution

### 1. Clone the Repository & Navigate to Folder
```bash
git clone https://github.com/ayushgadkari/RevShield-AI.git
cd RevShield-AI
```

### 2. Configure Your Environment Variables
Create a file named `.env` in the root directory of your project folder and add your Gemini API key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 3. Install Dependencies
Install the required packages using pip:
```bash
pip install fastapi uvicorn google-genai requests python-dotenv
```

### 4. Start the FastAPI Server
Launch the application server locally using Uvicorn:
```bash
python -m uvicorn main:app --reload
```
*The app will automatically initialize your SQLite database (`revshield.db`) on startup.*

### 5. Access the Interactive Dashboard
Open your web browser and navigate to:
👉 **`http://127.0.0.1:8000/`**

You will see the live Tailwind CSS dashboard with real-time analytics, metrics, and security status badges.

---

### 🧪 Running Automated Tests

To test the AI recovery engine and see real-time classification (both **Recoverable** smart retries and **Permanent** secure blocks):

1. Ensure your test file (`test_webhook.py`) is in your project folder.
2. Open a second terminal window and run:
   ```bash
   python test_webhook.py
   ```
3. Refresh your browser dashboard to view the newly logged transactions instantly!
