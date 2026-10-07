# NEXUS — AI-Powered Personal Expense Tracker & Forecasting System

A major-project foundation built with Flask, SQLite, HTML5, CSS3, JavaScript, Chart.js and scikit-learn.

## Core principle
The application does not require a downloaded external expense dataset. Transactions are created by the user and become the personal dataset used by the analytics/forecasting layer.

## Run
1. Create a Python virtual environment.
2. Install requirements.
3. Run `python run.py`.
4. Open `http://127.0.0.1:5000`.

## Forecasting
The forecasting engine uses the user's own monthly expense history. With at least three months of history it fits a simple linear trend; before that it uses a transparent weighted personal-history baseline. This prevents fake ML claims when a new user has no history.

## Planned major-project extensions
- Edit transactions
- Recurring transactions
- Advanced filters/search
- PDF/CSV reports
- Forecast evaluation dashboard
- Category-level forecasting
- Model registry/versioning
- Security hardening
- Automated tests
- Production deployment
