# Budget Bot

A Telegram bot for family budget tracking with Google Sheets integration.

## Table of Contents

- [Background](#background)
- [Install](#install)
- [Usage](#usage)
- [Configuration](#configuration)
- [License](#license)

## Background

This bot helps track family income and expenses through Telegram. All transactions are stored in a Google Sheets spreadsheet for easy analysis and reporting.

**Features:**
- Quick transaction entry by sending just a number
- Expense and income categorization
- Optional description for each transaction
- Automatic date stamping
- Multi-user support with whitelist

## Install

### Prerequisites

- Python 3.10+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google Cloud service account with Sheets API enabled

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/budget-management.git
cd budget-management
```

2. Create and activate virtual environment:
```bash
python -m venv venv
.\venv\Scripts\Activate  # Windows
source venv/bin/activate  # Linux/macOS
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure Google Sheets access:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable **Google Sheets API** and **Google Drive API**
   - Create a Service Account and download the JSON key
   - Place the JSON file in the project root
   - Share your Google Sheet with the service account email (Editor access)

5. Create `.env` file (see [Configuration](#configuration))

## Usage

Start the bot:
```bash
python bot.py
```

### Transaction Flow

**Quick entry (number first):**
1. Send any number (e.g., `500`)
2. Select Expense or Income
3. Choose a category
4. Enter description or skip

**Standard entry:**
1. Send `/start` or any text
2. Select Expense or Income
3. Enter amount
4. Choose a category
5. Enter description or skip

## Configuration

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_telegram_bot_token
SHEET_ID=your_google_sheet_id
ALLOWED_USERS=123456789,987654321
GOOGLE_CREDENTIALS_FILE=service_account.json
TIMEZONE_OFFSET=4
```

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram Bot API token from BotFather |
| `SHEET_ID` | Google Sheets document ID (from URL) |
| `ALLOWED_USERS` | Comma-separated Telegram user IDs |
| `GOOGLE_CREDENTIALS_FILE` | Path to service account JSON (default: `service_account.json`) |
| `TIMEZONE_OFFSET` | UTC offset in hours (default: `4`) |

### Google Sheet Structure

The bot expects a sheet named "Транзакции" with:
- **Expenses**: Columns B-E (Date, Amount, Description, Category)
- **Income**: Columns G-J (Date, Amount, Description, Category)
- Data starts from row 4

Categories are loaded from a "Settings" sheet with columns:
- Column A: Category name
- Column B: Type (`expense` or `income`)

## License

MIT
