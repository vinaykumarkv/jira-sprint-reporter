# Quick Start Guide

Get JIRA Sprint Reporter running in **5 minutes**! ⚡

---

## 🎯 Prerequisites Checklist

Before you begin, make sure you have:

- [ ] Python 3.8+ installed (`python --version`)
- [ ] JIRA account with API access
- [ ] 10 minutes of time

---

## ⚡ Installation (2 minutes)

### Step 1: Download & Setup

```bash
# Download the project
git clone https://github.com/yourcompany/jira-sprint-reporter.git
cd jira-sprint-reporter

# OR download ZIP and extract

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## 🔑 Configuration (2 minutes)

### Step 1: Get Your JIRA Info

1. **Find Board ID**
   - Go to your JIRA board
   - Look at URL: `...rapidView=123` ← That's your Board ID

2. **Find Sprint ID**
   - Click on your active sprint
   - Look at URL or use this: `https://yourcompany.atlassian.net/rest/agile/1.0/board/YOUR_BOARD_ID/sprint`
   - Find your sprint and copy its `id`

3. **Generate API Token**
   - Go to: https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Copy the token

### Step 2: Create .env File

```bash
# Copy template
cp .env_template .env

# Edit .env (use notepad/nano/vim)
notepad .env  # Windows
nano .env     # Mac/Linux
```

**Minimal .env Configuration:**
```env
# REQUIRED - Fill these in!
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_API_KEY=your_api_token_from_step_3
JIRA_USERNAME=your.email@company.com
JIRA_BOARD_ID=123
JIRA_SPRINT_ID=456
JIRA_PROJECT=YOURPROJECT
SPRINT_NAME=Sprint 24

# OPTIONAL - Leave empty for now
EMAIL_RECIPIENTS=
```

**Save the file!**

---

## 🚀 Run (1 minute)

```bash
# Make sure virtual environment is active
python jira_sprint_reporter.py
```

**Expected Output:**
```
============================================================
JIRA Sprint Reporter - Enhanced Email Version
============================================================
Loading configuration...
Sprint: Sprint 24
Fetching sprint issues...
Fetched 45/45 issues
✓ HTML report: sprint_report.html
============================================================
```

**Open the report:**
```bash
# Windows
start sprint_report.html

# Mac
open sprint_report.html

# Linux
xdg-open sprint_report.html
```

---

## ✅ Success!

You should now see:
- 📊 Interactive HTML report in your browser
- 📁 `sprint_stories.csv` file
- 📁 `sprint_defects.csv` file

---

## 📧 Enable Email (Optional +2 minutes)

### Option 1: Outlook (Windows)

```bash
# Install Outlook support
pip install pywin32

# Edit .env
EMAIL_RECIPIENTS=manager@company.com,team@company.com
```

**Run again:**
```bash
python jira_sprint_reporter.py
```

Email will open in Outlook ready to send!

### Option 2: Gmail

**Generate App Password:**
1. Enable 2FA: https://myaccount.google.com/security
2. Get app password: https://myaccount.google.com/apppasswords

**Update .env:**
```env
EMAIL_RECIPIENTS=manager@company.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your.gmail@gmail.com
EMAIL_PASSWORD=your_app_password_here
```

**Run:**
```bash
python jira_sprint_reporter.py
```

---

## 🔧 Common Issues & Quick Fixes

### Issue: "Module not found"
**Fix:**
```bash
pip install -r requirements.txt
```

### Issue: "401 Unauthorized"
**Fix:**
- Check JIRA_API_KEY is correct
- Verify JIRA_USERNAME is your email
- Regenerate API token

### Issue: "Sprint not found"
**Fix:**
- Verify JIRA_SPRINT_ID
- Check JIRA_BOARD_ID matches
- List sprints: `curl -u email:token https://yourcompany.atlassian.net/rest/agile/1.0/board/BOARD_ID/sprint`

### Issue: "Playwright error"
**Fix:**
```bash
playwright install chromium
# If still fails:
playwright install-deps
```

---

## 📝 Next Steps

### Customize Your Report

**Change Issue Types (.env):**
```env
STORY_TYPES=Story,Task,Epic
DEFECT_TYPES=Bug,Defect,Production Issue
```

**Adjust Screenshot Size (.env):**
```env
SCREENSHOT_WIDTH=1200
EMAIL_IMAGE_MAX_WIDTH=800
```

### Automate Daily Reports

**Windows Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task → Daily → 9:00 AM
3. Action: Start Program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `C:\path\to\jira_sprint_reporter.py`
   - Start in: `C:\path\to\project`

**Mac/Linux Cron:**
```bash
crontab -e

# Add this line (runs daily at 9 AM)
0 9 * * * cd /path/to/project && /path/to/venv/bin/python jira_sprint_reporter.py
```

---

## 🎓 Learn More

- **Full Documentation**: See [README.md](README.md)
- **API Integrations**: See [API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md)
- **Future Features**: See [FUTURE_SCOPE.md](FUTURE_SCOPE.md)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 💡 Pro Tips

### 1. Test with One Recipient First
```env
EMAIL_RECIPIENTS=your.email@company.com
```

### 2. Use Test Sprint
Use a small, completed sprint for your first run

### 3. Check Logs
If something fails, read the console output carefully

### 4. Backup Your .env
```bash
# Keep .env safe and never commit it!
cp .env .env.backup
```

---

## 🆘 Need Help?

**Quick Checks:**
1. Is Python 3.8+? → `python --version`
2. Is virtual env active? → Should see `(venv)` in terminal
3. Is .env configured? → Check all required fields filled
4. Are dependencies installed? → `pip list`

**Still stuck?**
- Check [README.md](README.md) for detailed troubleshooting
- Open an issue: https://github.com/vinaykumarkv/jira-sprint-reporter/issues
- Email: vinaykumar.kv@outlook.com.com

---

## 🎉 You're All Set!

You've successfully set up JIRA Sprint Reporter. Now you can:

- ✅ Generate beautiful sprint reports
- ✅ Export data to CSV
- ✅ Send automated emails
- ✅ Track team progress

**Happy reporting! 📊**

---

*Estimated total time: **5-7 minutes** ⏱️*
