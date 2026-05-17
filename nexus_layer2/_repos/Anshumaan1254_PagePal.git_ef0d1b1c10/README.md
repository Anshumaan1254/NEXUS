# PagePal 📄

<p align="center">
  <img src="public/icons/icon128.png" alt="PagePal Logo" width="128" height="128">
</p>

<p align="center">
  <strong>Your AI-powered reading companion for Chrome</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#tech-stack">Tech Stack</a> •
  <a href="#development">Development</a>
</p>

---

## ✨ Features

### 📸 Page Snapshot
Instantly capture and summarize any webpage into digestible key points. Powered by Chrome's built-in AI Summarizer API, PagePal extracts the most important information so you don't have to read through lengthy articles.

### 🔍 Quick Define
Simply highlight any word or phrase on a webpage to get an instant, AI-powered explanation. Perfect for understanding technical jargon, unfamiliar terms, or complex concepts without leaving the page.

## 🚀 Installation

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/pagepal.git
   cd pagepal
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Build the extension:
   ```bash
   npm run build
   ```

4. Load in Chrome:
   - Open `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `dist` folder

### Requirements

- **Chrome Canary** or **Chrome Dev** (version 128+)
- Enable AI features:
  - Navigate to `chrome://flags/#summarization-api-for-gemini-nano`
  - Enable "Summarization API for Gemini Nano"
  - Navigate to `chrome://flags/#language-model-api`
  - Enable "Prompt API for Gemini Nano"
  - Restart Chrome

## 📖 Usage

1. **Click the PagePal icon** in your Chrome toolbar to open the side panel
2. **Page Snapshot**: Click the "Page Snapshot" button to generate a summary of the current page
3. **Quick Define**: Highlight any text (2-100 characters) on any webpage to see an instant definition popup

## 🛠️ Tech Stack

- **React 19** - UI framework
- **Vite** - Build tool and development server
- **Three.js** - 3D particle animation background
- **React Three Fiber** - React renderer for Three.js
- **Chrome Extension Manifest V3** - Extension platform
- **Chrome Built-in AI APIs** - Summarizer & Language Model APIs

## 💻 Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint
```

## 📁 Project Structure

```
cognitive-flow/
├── public/
│   ├── manifest.json      # Extension manifest
│   └── icons/             # Extension icons
├── src/
│   ├── content-script.js  # Text selection & tooltip handling
│   ├── service-worker.js  # Background AI processing
│   └── sidepanel/         # React sidepanel app
│       ├── App.jsx        # Main application component
│       ├── Antigravity.jsx# 3D particle background
│       ├── index.css      # Styles
│       ├── index.html     # HTML entry
│       └── main.jsx       # React entry point
└── package.json
```

## 🎨 UI/UX

PagePal features a modern, dark-themed interface with:
- **Glassmorphism design** with backdrop blur effects
- **Interactive 3D particle animation** powered by Three.js
- **Smooth animations** and micro-interactions
- **Teal/cyan color palette** for a premium feel

## ⚠️ Limitations

- Requires Chrome Canary/Dev with AI flags enabled
- AI features depend on Chrome's built-in Gemini Nano model
- Page Snapshot works best on text-heavy content
- Quick Define supports text selections between 2-100 characters

## 📄 License

MIT License - feel free to use this project for personal or commercial purposes.

---

<p align="center">
  Made with ❤️ and powered by Chrome AI
</p>
