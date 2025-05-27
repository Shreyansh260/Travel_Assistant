# 🚀 AI-Powered Smart Travel Assistant

An intelligent desktop travel assistant built using **PyQt5**, **Google Maps API**, and **Gemini AI (Google LLM)**. Designed to help working professionals in ASEAN metropolitan cities efficiently plan their daily commute with live traffic updates, personalized suggestions, and a modern user interface.

---

## 🌟 Features

- 🔐 **Google OAuth Login** — Secure and seamless user authentication.
- 🗺️ **Live Directions** — Get real-time routes between source and destination using Google Maps.
- 🧠 **AI Chatbot (Gemini)** — Ask travel-related queries and get contextual smart replies.
- 🕓 **Journey History Tracking** — Save and view past travel plans.
- 📊 **Personalized Travel Insights** — AI learns and recommends smarter routes over time.
- 💡 **Modern UI** — Custom glowing buttons, scrollable chat, animated transitions.
- 📍 **Traffic-aware Planning** — Integrated live traffic status for smarter decisions.
- 🔄 **Dynamic Routing** — Update routes on-the-fly without restarting the app.

---

## 📸 Screenshots

> _Coming soon: Include screenshots here showing login page, chatbot, and map with directions._

---

## 🧰 Tech Stack

| Layer | Technology |
|------|------------|
| 🖼️ UI Framework | PyQt5 |
| 🗺️ Maps API | Google Maps Directions API |
| 🔐 Authentication | Google OAuth 2.0 |
| 🧠 AI Chatbot | Gemini (Google LLM) API |
| 💾 Local Storage | SQLite (via JSON) |
| 🌐 Networking | `requests` |
| ⚙️ Styling & Animation | PyQt CSS, custom glow effects, animations |

---

## 📥 Installation

> Make sure you have **Python 3.8+** installed.

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/smart-travel-assistant.git
cd smart-travel-assistant
```
---
### 2. 2. Install Dependencies
```bash
PyQt5>=5.15.9
requests>=2.31.0
google-auth>=2.28.0
google-auth-oauthlib>=1.2.0
google-api-python-client>=2.126.0
python-dotenv>=1.0.1
httpx>=0.27.0
```

---

```bash
pip install Dependencies
```

---
## 🔐 Authentication Setup

This app uses **Google OAuth 2.0** to securely authenticate users and personalize their travel experience.

### Steps to Set Up:

1. **Create OAuth Credentials**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one.
   - Navigate to **APIs & Services → Credentials**
   - Click **“Create Credentials” → OAuth Client ID**
   - Choose **Desktop App**
   - Download the `credentials.json` and place it in the project root.

2. **Token Handling**:
   - On first run, the app will prompt Google Sign-In via browser.
   - The access/refresh tokens will be securely stored in `token.json`.


---

## 🌐 Environment Variables

Create a `.env` file in your project root with the following content:

```env
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_AI_API_KEY=your_gemini_api_key_here
```
## 🤖 Example Queries for AI
```"Plan my trip from Andheri to Churchgate avoiding traffic"
"How long will it take to reach work today?"
"Suggest the fastest route with public transport"
"Is it safe to travel at 10 PM in Gurgaon?"
"What’s my travel history for last Monday?"
```

---
## ✨ To‑Do / Upcoming Features

- 📱 **Kivy Mobile Port** — Android APK & iOS build

- 🗣 **Voice Input & TTS** — hands‑free planning

- 🚌 **Multimodal Transport Mix** — ride‑share + transit combos

- 🌐 **Offline Caching** — last‑mile routing without internet

- 🏆 **Rewards / Gamification** — earn points for eco‑friendly routes

- 🔔 **Push Notifications** — live delay alerts & re‑routing


---
## 🙏 Acknowledgments

- **[Google Maps API](https://developers.google.com/maps/documentation)**

- **[Google Gemeni API](https://ai.google.dev/)**

- **[Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)**

- **[PyQt5](https://pypi.org/project/PyQt5/)**
