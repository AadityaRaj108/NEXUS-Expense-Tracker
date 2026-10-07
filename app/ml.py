"""
NEXUS Personal Expense Forecasting Engine

This module forecasts a user's next-month expenses using ONLY
that user's own NEXUS transaction history.

No external dataset is used.

Forecast strategy:
    0 months  -> No-history response
    1-2 months -> Weighted personal-history baseline
    3+ months -> Personal linear-trend model

Additional personal signals:
    - recent spending
    - overall spending trend
    - month-to-month volatility
    - transaction activity

The public forecast_next_month() contract intentionally remains
compatible with the existing NEXUS dashboard and API.
"""

from datetime import date

import numpy as np
from sklearn.linear_model import LinearRegression

from .db import get_db


# ============================================================
# CONFIGURATION
# ============================================================

MIN_ML_MONTHS = 3

# Recent months receive more importance when blending the
# statistical trend with the recent personal spending level.
RECENT_WEIGHT = 0.60
TREND_WEIGHT = 0.40

# Prevent a very aggressive linear trend from producing an
# unrealistic forecast relative to the user's recent history.
MAX_FORECAST_MULTIPLIER = 2.50
MIN_FORECAST_MULTIPLIER = 0.25


# ============================================================
# BASIC PERSONAL DATA
# ============================================================

def monthly_expenses(user_id):
    """
    Return the user's historical monthly expense totals.

    Result:
        [
            ("2026-01", 8500.0),
            ("2026-02", 9200.0),
            ...
        ]

    Only the authenticated user's own expense transactions
    are considered.
    """

    db = get_db()

    rows = db.execute(
        """
        SELECT
            substr(
                transaction_date,
                1,
                7
            ) AS month,

            SUM(amount) AS total

        FROM transactions

        WHERE user_id=?
          AND kind='expense'

        GROUP BY month

        ORDER BY month
        """,
        (user_id,),
    ).fetchall()

    return [
        (
            row["month"],
            float(row["total"] or 0.0),
        )
        for row in rows
    ]


def monthly_income(user_id):
    """
    Return the user's historical monthly income totals.

    This is kept separate from expense forecasting so the
    forecasting engine can optionally expose income-aware
    planning information without changing the existing
    dashboard contract.
    """

    db = get_db()

    rows = db.execute(
        """
        SELECT
            substr(
                transaction_date,
                1,
                7
            ) AS month,

            SUM(amount) AS total

        FROM transactions

        WHERE user_id=?
          AND kind='income'

        GROUP BY month

        ORDER BY month
        """,
        (user_id,),
    ).fetchall()

    return [
        (
            row["month"],
            float(row["total"] or 0.0),
        )
        for row in rows
    ]


# ============================================================
# STATISTICAL HELPERS
# ============================================================

def _weighted_recent_average(values):
    """
    Calculate a recency-weighted average.

    More recent personal spending receives more influence.
    """

    values = np.asarray(
        values,
        dtype=float,
    )

    if len(values) == 0:
        return 0.0

    weights = np.arange(
        1,
        len(values) + 1,
        dtype=float,
    )

    return float(
        np.average(
            values,
            weights=weights,
        )
    )


def _recent_average(values, window=3):
    """
    Calculate the average of the most recent observations.
    """

    values = np.asarray(
        values,
        dtype=float,
    )

    if len(values) == 0:
        return 0.0

    recent = values[-window:]

    return float(
        np.mean(recent)
    )


def _trend_prediction(values):
    """
    Train a Linear Regression model on the user's own
    historical monthly expense totals.

    The model learns:

        month_index -> personal_monthly_expense

    No external data is used.
    """

    values = np.asarray(
        values,
        dtype=float,
    )

    x = np.arange(
        len(values),
        dtype=float,
    ).reshape(-1, 1)

    model = LinearRegression()

    model.fit(
        x,
        values,
    )

    prediction = float(
        model.predict(
            [[len(values)]]
        )[0]
    )

    return prediction


def _volatility(values):
    """
    Return normalized month-to-month spending volatility.

    This is used as an informational signal and does not
    artificially inflate the forecast.
    """

    values = np.asarray(
        values,
        dtype=float,
    )

    if len(values) < 2:
        return 0.0

    mean_value = float(
        np.mean(values)
    )

    if mean_value <= 0:
        return 0.0

    return float(
        np.std(values) / mean_value
    )


def _safe_bound_prediction(
    prediction,
    recent_average,
):
    """
    Keep a trend-based forecast within sensible personal
    bounds.

    This protects users from extreme extrapolation when a
    short personal history contains an unusual month.
    """

    prediction = max(
        0.0,
        float(prediction),
    )

    recent_average = max(
        0.0,
        float(recent_average),
    )

    if recent_average <= 0:
        return prediction

    upper = (
        recent_average
        * MAX_FORECAST_MULTIPLIER
    )

    lower = (
        recent_average
        * MIN_FORECAST_MULTIPLIER
    )

    return float(
        np.clip(
            prediction,
            lower,
            upper,
        )
    )


# ============================================================
# FORECAST ENGINE
# ============================================================

def forecast_next_month(user_id):
    """
    Forecast the user's next-month expenses.

    The model is strictly personalized.

    Data source:
        NEXUS transactions belonging to user_id.

    Returns a dictionary compatible with the existing
    dashboard, analytics page and /api/forecast endpoint.

    Existing fields preserved:
        value
        method
        months_used
        confidence

    Additional useful fields:
        recent_average
        trend_prediction
        volatility
        data_points
    """

    history = monthly_expenses(
        user_id
    )

    # --------------------------------------------------------
    # NO HISTORY
    # --------------------------------------------------------

    if not history:

        return {
            "value": 0.0,
            "method": (
                "No personal history yet"
            ),
            "months_used": 0,
            "confidence": (
                "Not enough data"
            ),
            "recent_average": 0.0,
            "trend_prediction": 0.0,
            "volatility": 0.0,
            "data_points": 0,
        }

    values = np.asarray(
        [
            value
            for _, value in history
        ],
        dtype=float,
    )

    months_used = len(values)

    recent_average = _recent_average(
        values,
        window=min(
            3,
            months_used,
        ),
    )

    weighted_average = (
        _weighted_recent_average(
            values
        )
    )

    volatility = _volatility(
        values
    )

    # --------------------------------------------------------
    # COLD START
    # --------------------------------------------------------
    #
    # With fewer than three monthly observations, a supervised
    # trend model would be unnecessarily unstable.
    #
    # Instead, use the user's own recent history with stronger
    # emphasis on recent months.
    # --------------------------------------------------------

    if months_used < MIN_ML_MONTHS:

        prediction = weighted_average

        method = (
            "Weighted personal-history baseline"
        )

        confidence = (
            "Early estimate"
        )

        trend_prediction = (
            weighted_average
        )

    # --------------------------------------------------------
    # PERSONAL ML MODEL
    # --------------------------------------------------------

    else:

        trend_prediction = (
            _trend_prediction(
                values
            )
        )

        # Blend the learned personal trend with the recent
        # personal spending level. This makes the forecast less
        # sensitive to a single unusual historical month.
        prediction = (
            (
                recent_average
                * RECENT_WEIGHT
            )
            +
            (
                trend_prediction
                * TREND_WEIGHT
            )
        )

        prediction = (
            _safe_bound_prediction(
                prediction,
                recent_average,
            )
        )

        method = (
            "Personal ML trend + recent spending"
        )

        # Confidence is intentionally descriptive rather than
        # pretending that a tiny personal dataset has laboratory-
        # grade statistical certainty.
        if months_used >= 12:

            confidence = (
                "Strong personal-history signal"
            )

        elif months_used >= 6:

            confidence = (
                "Good personal-history signal"
            )

        else:

            confidence = (
                "Model-based early signal"
            )

    prediction = max(
        0.0,
        float(prediction),
    )

    return {
        "value": round(
            prediction,
            2,
        ),

        "method": method,

        "months_used": months_used,

        "confidence": confidence,

        "recent_average": round(
            recent_average,
            2,
        ),

        "trend_prediction": round(
            max(
                0.0,
                float(trend_prediction),
            ),
            2,
        ),

        "volatility": round(
            volatility,
            4,
        ),

        "data_points": months_used,
    }


# ============================================================
# OPTIONAL CATEGORY FORECASTING
# ============================================================

def category_expense_history(user_id):
    """
    Return monthly expense history broken down by category.

    This function is intentionally independent of the existing
    dashboard so it can support future category-level planning
    without changing the current UI.
    """

    db = get_db()

    rows = db.execute(
        """
        SELECT
            substr(
                transaction_date,
                1,
                7
            ) AS month,

            category,

            SUM(amount) AS total

        FROM transactions

        WHERE user_id=?
          AND kind='expense'

        GROUP BY
            month,
            category

        ORDER BY
            month,
            category
        """,
        (user_id,),
    ).fetchall()

    result = []

    for row in rows:

        result.append({
            "month": row["month"],
            "category": row["category"],
            "total": float(
                row["total"] or 0.0
            ),
        })

    return result


def forecast_category(
    user_id,
    category,
):
    """
    Forecast next-month spending for one category using the
    user's own historical category spending.

    This does not alter the existing dashboard forecast.
    """

    db = get_db()

    rows = db.execute(
        """
        SELECT
            substr(
                transaction_date,
                1,
                7
            ) AS month,

            SUM(amount) AS total

        FROM transactions

        WHERE user_id=?
          AND kind='expense'
          AND category=?

        GROUP BY month

        ORDER BY month
        """,
        (
            user_id,
            category,
        ),
    ).fetchall()

    history = [
        (
            row["month"],
            float(row["total"] or 0.0),
        )
        for row in rows
    ]

    if not history:

        return {
            "category": category,
            "value": 0.0,
            "months_used": 0,
            "method": (
                "No personal category history"
            ),
            "confidence": (
                "Not enough data"
            ),
        }

    values = np.asarray(
        [
            value
            for _, value in history
        ],
        dtype=float,
    )

    months_used = len(values)

    if months_used >= MIN_ML_MONTHS:

        trend = _trend_prediction(
            values
        )

        recent = _recent_average(
            values,
            window=min(
                3,
                months_used,
            ),
        )

        prediction = (
            recent * RECENT_WEIGHT
            +
            trend * TREND_WEIGHT
        )

        prediction = _safe_bound_prediction(
            prediction,
            recent,
        )

        method = (
            "Personal category trend"
        )

        confidence = (
            "Model-based"
        )

    else:

        prediction = (
            _weighted_recent_average(
                values
            )
        )

        method = (
            "Weighted category history"
        )

        confidence = (
            "Early estimate"
        )

    return {
        "category": category,
        "value": round(
            max(
                0.0,
                float(prediction),
            ),
            2,
        ),
        "months_used": months_used,
        "method": method,
        "confidence": confidence,
    }


# ============================================================
# PLANNING SUMMARY
# ============================================================

def forecast_summary(user_id):
    """
    Produce a compact planning summary using the user's
    forecast and recorded financial history.

    This is not required by the current dashboard, but provides
    a clean foundation for future NEXUS planning features.
    """

    forecast = forecast_next_month(
        user_id
    )

    income_history = monthly_income(
        user_id
    )

    if income_history:

        latest_income = float(
            income_history[-1][1]
        )

    else:

        latest_income = 0.0

    forecast_value = float(
        forecast["value"]
    )

    expected_balance = (
        latest_income
        - forecast_value
    )

    return {
        "forecast": forecast_value,
        "latest_income": round(
            latest_income,
            2,
        ),
        "expected_balance": round(
            expected_balance,
            2,
        ),
        "expected_savings_rate": round(
            (
                (
                    expected_balance
                    / latest_income
                )
                * 100
            )
            if latest_income > 0
            else 0.0,
            2,
        ),
        "months_used": forecast[
            "months_used"
        ],
        "confidence": forecast[
            "confidence"
        ],
    }