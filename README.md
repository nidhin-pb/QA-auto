# CVA QA Testing Automation Platform

A comprehensive automated testing platform for Chat Virtual Agent (CVA) QA testing using AI-driven conversations and browser automation.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                      │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Login    │ │ Live View    │ │ Report Dashboard     │ │
│  │ Config   │ │ (Real-time   │ │ (Pass/Fail, Excel    │ │
│  │ Panel    │ │  chat watch) │ │  download)           │ │
│  └──────────┘ └──────────────┘ └──────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │ WebSocket + REST
┌──────────────────────▼──────────────────────────────────┐
│                  BACKEND (FastAPI + Python)               │
│  ┌──────────────┐ ┌────────────┐ ┌────────────────────┐ │
│  │ Test Engine  │ │ AI Brain   │ │ Report Generator   │ │
│  │ (Orchestrate)│ │ (DeepSeek) │ │ (Excel/openpyxl)   │ │
│  └──────┬───────┘ └─────┬──────┘ └────────────────────┘ │
│         │               │                                │
│  ┌──────▼───────────────▼──────────────────────────────┐ │
│  │         Playwright Browser Automation                │ │
│  │    (Login to Teams, chat with CVA, screenshots)      │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## 🚀 Features

### 🤖 AI-Powered Testing
- **DeepSeek AI Integration**: Generates human-like test messages dynamically
- **Context-Aware Conversations**: AI adapts follow-up questions based on CVA responses
- **Intelligent Analysis**: AI analyzes CVA responses for relevance, helpfulness, and goal achievement

### 🎭 Browser Automation
- **Microsoft Teams Integration**: Automated login and navigation to CVA chat
- **Real-time Screenshots**: Live view of testing process with screenshot capture
- **Message Exchange**: Automated sending and receiving of chat messages

### 📊 Comprehensive Testing
- **20+ Test Scenarios**: Covers basic functionality, ticket management, edge cases, security, and performance
- **Multiple Categories**: Basic Functionality, Ticket Management, Knowledge Base, Edge Cases, Error Handling, Performance, Security
- **Validation Framework**: Automated validation of CVA responses against expected behaviors

### 📈 Real-time Monitoring
- **Live Chat View**: Watch conversations in real-time as they happen
- **Progress Tracking**: Visual progress bar with current test status
- **Log Streaming**: Real-time log messages from the testing engine

### 📋 Reporting & Analytics
- **Excel Reports**: Comprehensive multi-sheet reports with test results, conversations, bugs, and validations
- **Executive Summary**: High-level overview with pass/fail rates and category breakdowns
- **Bug Tracking**: Automated bug identification and reproduction steps
- **Conversation Logs**: Full conversation history for analysis

## 📁 Project Structure

```
cva-qa-automation/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── requirements.txt     # Python dependencies
│   ├── ai_brain.py         # AI integration (DeepSeek)
│   ├── teams_automator.py  # Teams browser automation
│   ├── test_engine.py      # Test orchestration
│   ├── test_scenarios.py   # Test scenario definitions
│   ├── report_generator.py # Excel report generation
│   ├── websocket_manager.py# Real-time communication
│   └── utils.py            # Utility functions
├── frontend/
│   ├── package.json        # Node.js dependencies
│   ├── public/
│   │   └── index.html      # HTML template
│   └── src/
│       ├── index.js        # React entry point
│       ├── index.css       # Global styles
│       ├── App.js          # Main application
│       ├── App.css         # App styles
│       └── components/     # React components
│           ├── LoginConfig.js
│           ├── LiveView.js
│           ├── TestDashboard.js
│           └── ReportView.js
├── reports/                # Generated Excel reports
├── screenshots/           # Test execution screenshots
├── start.bat              # Windows startup script
├── start.sh               # Mac/Linux startup script
└── README.md              # This file
```

## 🛠️ Prerequisites

### Required Software
- **Python 3.9+** - Backend runtime
- **Node.js 16+** - Frontend development
- **Git** - Version control (optional)

### API Keys Required
- **DeepSeek API Key**: For AI-powered message generation
  - Get from: https://platform.deepseek.com/
  - Update in `backend/config.py`

## ⚡ Quick Start

### Option 1: Automated Setup (Recommended)

**Windows:**
```bash
# Double-click or run:
start.bat
```

**Mac/Linux:**
```bash
# Make executable and run:
chmod +x start.sh
./start.sh
```

The setup script will:
1. ✅ Check prerequisites
2. 📦 Install Python dependencies
3. 🌐 Install Playwright browsers
4. 📦 Install frontend dependencies
5. 🏗️ Build frontend (optional)
6. 🚀 Start both backend and frontend servers

### Option 2: Manual Setup

#### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
python -m playwright install chromium
python main.py
```

#### 2. Frontend Setup (New Terminal)
```bash
cd frontend
npm install
npm start
```

## 🌐 Access Points

Once started, access the application at:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📖 Usage Guide

### 1. Initial Setup
1. Open http://localhost:3000 in your browser
2. Go to **Config** tab
3. Enter your Teams credentials:
   - Email/Username
   - Password
   - CVA App Name (default: "IT Servicedesk AI")
4. Click **Connect & Initialize**

### 2. Configure Tests
1. Go to **Tests** tab
2. Review available test scenarios
3. Select/deselect tests using checkboxes
4. Use **All/None** buttons for bulk selection

### 3. Run Tests
1. Click **Run Tests** button in header
2. Watch real-time progress in **Live View**
3. Monitor logs and screenshots
4. Wait for completion

### 4. Review Results
1. Go to **Results** tab for summary
2. Check **Logs & Reports** panel for details
3. Download Excel reports for analysis

## 🧪 Test Scenarios

### Categories
- **Basic Functionality** (3 tests): Password reset, VPN issues, software installation
- **Ticket Management** (4 tests): Create incidents, service requests, check status, update tickets
- **Knowledge Base** (1 test): KB article access and citations
- **Edge Cases** (4 tests): Gibberish input, multiple issues, sensitive data, non-English
- **Error Handling** (2 tests): Invalid tickets, service unavailable
- **Performance** (1 test): Response time testing
- **Security** (1 test): Security question handling

### Example Test Flow
1. **AI generates** initial message based on scenario
2. **Browser sends** message to CVA in Teams
3. **CVA responds** with help/information
4. **AI analyzes** response for relevance and helpfulness
5. **AI generates** follow-up if needed
6. **Process repeats** until goal achieved or max turns reached
7. **Results recorded** with validations and bug reports

## 🔧 Configuration

### Backend Configuration (`backend/config.py`)
```python
class TeamsConfig:
    email: str = ""              # Your Teams email
    password: str = ""           # Your Teams password
    teams_url: str = "https://teams.microsoft.com/v2/"
    cva_app_name: str = "IT Servicedesk AI"

class AIConfig:
    deepseek_api_key: str = "your-api-key-here"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

class AppConfig:
    headless: bool = False                    # Show browser window
    max_wait_for_response: int = 60           # CVA response timeout
    message_check_interval: float = 2.0       # Message polling interval
    browser_slow_mo: int = 100                # Browser slowdown (ms)
```

### Environment Variables
```bash
# Optional: Override config with environment variables
DEEPSEEK_API_KEY=your-key-here
TEAMS_EMAIL=your-email@company.com
TEAMS_PASSWORD=your-password
HEADLESS=true
```

## 📊 Report Format

Generated Excel reports include:

### �� Sheets
1. **Executive Summary**: High-level overview and statistics
2. **Detailed Results**: Complete test results with status and duration
3. **Conversation Logs**: Full chat transcripts with timestamps
4. **Bugs & Issues**: Identified problems with reproduction steps
5. **Validation Details**: Pass/fail status for each validation check

### 📈 Metrics
- **Pass/Fail Rate**: Overall and by category
- **Test Duration**: Individual and total execution time
- **Bug Count**: Number and severity of issues found
- **Response Quality**: AI analysis of CVA helpfulness and relevance

## 🐛 Troubleshooting

### Common Issues

#### "Failed to login to Teams"
- Verify Teams credentials are correct
- Check if MFA is enabled (may require manual intervention)
- Try running with `headless: false` to see login process

#### "Could not open CVA chat"
- Verify CVA app name matches exactly in Teams
- Check if CVA app is available in your Teams instance
- Try manually opening CVA first to establish conversation

#### "CVA did not respond within timeout"
- Increase `max_wait_for_response` in config
- Check if CVA is online and responding
- Verify Teams notifications are enabled

#### "Frontend build failed"
- Ensure Node.js 16+ is installed
- Try `npm install --force`
- Use dev server (npm start) instead of build

#### "Playwright browser issues"
- Run `python -m playwright install chromium`
- Check system dependencies for headless mode
- Try running with `headless: false`

### Debug Mode
Enable detailed logging:
```python
# In backend/config.py
class AppConfig:
    headless: bool = False  # Show browser
    browser_slow_mo: 500   # Slower automation
```

### Logs Location
- **Application logs**: Console output and frontend log panel
- **Screenshots**: `screenshots/` directory
- **Reports**: `reports/` directory
- **Browser logs**: Playwright console (when headless: false)

## 🔒 Security Considerations

### Credentials Management
- **Never commit** credentials to version control
- **Use environment variables** for production deployment
- **Consider** Azure Key Vault or similar for enterprise

### Data Privacy
- **Screenshots** may contain sensitive information
- **Chat logs** are stored in reports and memory
- **Clean up** sensitive data after testing

### Network Security
- **Firewall rules** may be needed for Teams access
- **Proxy settings** for corporate networks
- **VPN requirements** for remote access

## 🚀 Production Deployment

### Docker Deployment
```dockerfile
# Example Dockerfile (not included)
FROM python:3.9-slim
# ... backend setup
FROM node:16-alpine
# ... frontend build
```

### Environment Setup
```bash
# Production environment variables
export DEEPSEEK_API_KEY="prod-key-here"
export TEAMS_EMAIL="service-account@company.com"
export TEAMS_PASSWORD="app-password"
export HEADLESS=true
export NODE_ENV=production
```

### Monitoring
- **Health checks**: `/api/health` endpoint
- **Metrics**: Test execution statistics
- **Logs**: Structured logging with levels
- **Alerts**: Failed test notifications

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd cva-qa-automation

# Setup development environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
cd frontend && npm install

# Run in development mode
cd backend && python main.py &
cd frontend && npm start
```

### Adding Test Scenarios
1. Edit `backend/test_scenarios.py`
2. Add new scenario to `get_all_scenarios()`
3. Include proper validations and expected keywords
4. Test with `python -m pytest` (if implemented)

### Code Style
- **Python**: Follow PEP 8
- **JavaScript**: Use ESLint configuration
- **Comments**: Document complex logic
- **Testing**: Write unit tests for new features

## 📄 License

This project is proprietary software. All rights reserved.

## 📞 Support

For support and questions:
- **Internal**: Contact the QA Automation team
- **Documentation**: This README and inline code comments
- **Issues**: Create tickets in the project tracking system

---

**Version**: 1.0.0  
**Last Updated**: 2026-02-18  
**Compatibility**: Python 3.9+, Node.js 16+, Teams Web App
