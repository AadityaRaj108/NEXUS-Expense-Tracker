import os
import re
import sqlite3
from pathlib import Path

from flask import current_app, g

try:
    import psycopg
    from psycopg.rows import tuple_row
except ImportError:
    psycopg = None
    tuple_row = None


# ============================================================
# DATABASE SCHEMA
# ============================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
    amount REAL NOT NULL CHECK(amount > 0),
    category TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    month TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),
    UNIQUE(user_id, category, month),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INTEGER PRIMARY KEY,
    display_name TEXT,
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    currency TEXT NOT NULL DEFAULT 'INR',
    locale TEXT NOT NULL DEFAULT 'en-IN',
    avatar_initials TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id INTEGER PRIMARY KEY,
    email_enabled INTEGER NOT NULL DEFAULT 1 CHECK(email_enabled IN (0,1)),
    budget_alerts INTEGER NOT NULL DEFAULT 1 CHECK(budget_alerts IN (0,1)),
    transaction_alerts INTEGER NOT NULL DEFAULT 1 CHECK(transaction_alerts IN (0,1)),
    monthly_summary INTEGER NOT NULL DEFAULT 1 CHECK(monthly_summary IN (0,1)),
    unusual_spending_alerts INTEGER NOT NULL DEFAULT 1 CHECK(unusual_spending_alerts IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    notification_type TEXT NOT NULL DEFAULT 'system',
    title TEXT NOT NULL DEFAULT 'NEXUS Notification',
    message TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL DEFAULT 'in_app',
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','queued','sent','read','failed')),
    reference_type TEXT,
    reference_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,
    read_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    template TEXT,
    message_body TEXT NOT NULL DEFAULT '',
    provider_message_id TEXT,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK(status IN ('queued','sent','failed')),
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sms_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    recipient TEXT NOT NULL,
    message_body TEXT NOT NULL,
    provider_message_id TEXT,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK(status IN ('queued','sent','failed')),
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    workspace_type TEXT NOT NULL DEFAULT 'personal'
        CHECK(workspace_type IN ('personal','family','team')),
    owner_user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workspace_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'member'
        CHECK(role IN ('owner','admin','member','viewer')),
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workspace_id, user_id),
    FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS voice_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    transcript TEXT NOT NULL,
    parsed_kind TEXT,
    parsed_amount REAL,
    parsed_category TEXT,
    parsed_payment_method TEXT,
    parsed_date TEXT,
    parsed_note TEXT,
    status TEXT NOT NULL DEFAULT 'received'
        CHECK(status IN ('received','parsed','confirmed','rejected','failed')),
    transaction_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(transaction_id) REFERENCES transactions(id) ON DELETE SET NULL
);
"""


# ============================================================
# POSTGRES COMPATIBILITY LAYER
# ============================================================

class CompatRow:
    """
    Behaves like sqlite3.Row for the parts used by NEXUS.

    Supports:
        row["id"]
        row[0]
    """

    def __init__(self, columns, values):
        self._columns = list(columns)
        self._values = tuple(values)
        self._mapping = dict(zip(self._columns, self._values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._mapping[key]

    def keys(self):
        return self._columns

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __repr__(self):
        return repr(self._mapping)


class CompatCursor:
    def __init__(self, cursor, lastrowid=None):
        self._cursor = cursor
        self.lastrowid = lastrowid

    def _convert(self, row):
        if row is None:
            return None

        if isinstance(row, CompatRow):
            return row

        columns = [
            getattr(description, "name", description[0])
            for description in self._cursor.description
        ]

        return CompatRow(columns, row)

    def fetchone(self):
        return self._convert(self._cursor.fetchone())

    def fetchall(self):
        return [
            self._convert(row)
            for row in self._cursor.fetchall()
        ]

    def fetchmany(self, size=None):
        rows = (
            self._cursor.fetchmany()
            if size is None
            else self._cursor.fetchmany(size)
        )
        return [
            self._convert(row)
            for row in rows
        ]

    def __iter__(self):
        for row in self._cursor:
            yield self._convert(row)

    def close(self):
        self._cursor.close()


class PostgresDB:
    """
    Small compatibility wrapper allowing the existing NEXUS
    routes to continue using SQLite-style SQL.

    It handles:
        ? placeholders
        INSERT OR IGNORE
        lastrowid
        SQLite PRAGMA statements used by the app
        row["column"] access
    """

    def __init__(self, url):
        if psycopg is None:
            raise RuntimeError(
                "psycopg is required for PostgreSQL DATABASE_URL."
            )

        self.connection = psycopg.connect(
            url,
            row_factory=tuple_row,
        )

    @staticmethod
    def _adapt_placeholders(sql):
        return sql.replace("?", "%s")

    @staticmethod
    def _strip_semicolon(sql):
        return sql.rstrip().rstrip(";").rstrip()

    @staticmethod
    def _is_insert(sql):
        return bool(
            re.match(
                r"^\s*INSERT\s+(?:OR\s+IGNORE\s+)?INTO\b",
                sql,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _adapt_insert(sql):
        sql = PostgresDB._strip_semicolon(sql)

        ignore = bool(
            re.match(
                r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\b",
                sql,
                re.IGNORECASE,
            )
        )

        if ignore:
            sql = re.sub(
                r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\b",
                "INSERT INTO",
                sql,
                count=1,
                flags=re.IGNORECASE,
            )

        if (
            " RETURNING " not in sql.upper()
            and re.match(
                r"^\s*INSERT\s+INTO\b",
                sql,
                re.IGNORECASE,
            )
        ):
            if ignore:
                sql += " ON CONFLICT DO NOTHING"

            sql += " RETURNING id"

        elif ignore and " RETURNING " not in sql.upper():
            sql += " ON CONFLICT DO NOTHING"

        return sql

    def execute(self, sql, params=None):
        if not isinstance(sql, str):
            raise TypeError("SQL statement must be a string.")

        stripped = sql.strip()

        # SQLite-only PRAGMA statements.
        if stripped.upper().startswith("PRAGMA "):
            class EmptyCursor:
                lastrowid = None

                def fetchone(self):
                    return None

                def fetchall(self):
                    return []

                def __iter__(self):
                    return iter(())

            return EmptyCursor()

        # SQLite's table-info compatibility query used by routes.py.
        if "pragma_table_info" in stripped.lower():
            match = re.search(
                r"pragma_table_info\s*\(\s*'([^']+)'\s*\)",
                stripped,
                re.IGNORECASE,
            )

            table_name = match.group(1) if match else ""

            cur = self.connection.cursor()

            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                  AND column_name = 'owner_id'
                LIMIT 1
                """,
                (table_name,),
            )

            row = cur.fetchone()

            class SimpleCursor:
                lastrowid = None

                def fetchone(self_inner):
                    if row is None:
                        return None
                    return CompatRow(["1"], row)

                def fetchall(self_inner):
                    if row is None:
                        return []
                    return [CompatRow(["1"], row)]

                def __iter__(self_inner):
                    return iter(self_inner.fetchall())

            return SimpleCursor()

        # SQLite's last_insert_rowid().
        if "last_insert_rowid()" in stripped.lower():
            cur = self.connection.cursor()
            cur.execute(
                """
                SELECT currval(
                    pg_get_serial_sequence('workspaces', 'id')
                )
                """
            )
            row = cur.fetchone()

            class LastInsertCursor:
                lastrowid = row[0] if row else None

                def fetchone(self_inner):
                    if row is None:
                        return None
                    return (row[0],)

                def fetchall(self_inner):
                    if row is None:
                        return []
                    return [(row[0],)]

                def __iter__(self_inner):
                    return iter(self_inner.fetchall())

            return LastInsertCursor()

        sql = self._adapt_placeholders(sql)

        if self._is_insert(sql):
            sql = self._adapt_insert(sql)

        cur = self.connection.cursor()

        try:
            cur.execute(sql, params or ())
        except Exception:
            cur.close()
            raise

        lastrowid = None

        if self._is_insert(sql) and cur.description:
            row = cur.fetchone()

            if row is not None:
                lastrowid = row[0]

            return CompatCursor(
                _BufferedCursor(cur, row),
                lastrowid=lastrowid,
            )

        return CompatCursor(
            cur,
            lastrowid=lastrowid,
        )

    def executescript(self, script):
        """
        PostgreSQL doesn't provide SQLite's executescript().
        NEXUS only uses it for the schema, so statements are
        executed individually.
        """

        statements = [
            statement.strip()
            for statement in script.split(";")
            if statement.strip()
        ]

        for statement in statements:
            statement = statement.replace(
                "INTEGER PRIMARY KEY AUTOINCREMENT",
                "INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY",
            )

            statement = statement.replace(
                "REAL NOT NULL",
                "DOUBLE PRECISION NOT NULL",
            )

            statement = statement.replace(
                "REAL,",
                "DOUBLE PRECISION,",
            )

            self.execute(statement)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


class _BufferedCursor:
    """
    Cursor wrapper that preserves a RETURNING row consumed by
    the compatibility layer.
    """

    def __init__(self, cursor, first_row):
        self._cursor = cursor
        self._first_row = first_row
        self._used_first = False
        self.description = cursor.description
        self.lastrowid = (
            first_row[0]
            if first_row is not None
            else None
        )

    def fetchone(self):
        if not self._used_first:
            self._used_first = True
            return self._first_row

        return self._cursor.fetchone()

    def fetchall(self):
        rows = []

        if not self._used_first:
            self._used_first = True

            if self._first_row is not None:
                rows.append(self._first_row)

        rows.extend(self._cursor.fetchall())

        return rows

    def fetchmany(self, size=None):
        if size is None:
            size = 1

        rows = []

        if not self._used_first:
            self._used_first = True

            if self._first_row is not None:
                rows.append(self._first_row)

        remaining = max(size - len(rows), 0)

        if remaining:
            rows.extend(
                self._cursor.fetchmany(remaining)
            )

        return rows

    def __iter__(self):
        while True:
            row = self.fetchone()

            if row is None:
                break

            yield row

    def close(self):
        self._cursor.close()


# ============================================================
# CONNECTION HELPERS
# ============================================================

def using_postgres(db=None):
    if db is not None:
        return isinstance(db, PostgresDB)

    return bool(
        current_app.config.get("DATABASE_URL")
    )


def get_db():
    if "db" not in g:
        if using_postgres():
            g.db = PostgresDB(
                current_app.config["DATABASE_URL"]
            )
        else:
            g.db = sqlite3.connect(
                current_app.config["DATABASE"]
            )

            g.db.row_factory = sqlite3.Row

            g.db.execute(
                "PRAGMA foreign_keys = ON"
            )

            g.db.execute(
                "PRAGMA busy_timeout = 5000"
            )

    return g.db


def close_db(_error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()

# ============================================================
# DATABASE INTROSPECTION
# ============================================================

def table_exists(db, table_name):

    if using_postgres(db):

        row = db.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ?
            LIMIT 1
            """,
            (table_name,),
        ).fetchone()

        return row is not None

    row = db.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def column_exists(
    db,
    table_name,
    column_name,
):

    if not table_exists(
        db,
        table_name,
    ):
        return False

    if using_postgres(db):

        row = db.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ?
              AND column_name = ?
            LIMIT 1
            """,
            (
                table_name,
                column_name,
            ),
        ).fetchone()

        return row is not None

    columns = db.execute(
        f"""
        PRAGMA table_info({table_name})
        """
    ).fetchall()

    return any(
        column["name"] == column_name
        for column in columns
    )


def add_column_if_missing(
    db,
    table_name,
    column_name,
    definition,
):

    if not column_exists(
        db,
        table_name,
        column_name,
    ):

        db.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {definition}
            """
        )


# ============================================================
# SUPPORT TABLE MIGRATIONS
# ============================================================

def migrate_support_tables(db):

    notification_columns = [
        ("notification_type", "TEXT NOT NULL DEFAULT 'system'"),
        ("title", "TEXT NOT NULL DEFAULT 'NEXUS Notification'"),
        ("message", "TEXT NOT NULL DEFAULT ''"),
        ("channel", "TEXT NOT NULL DEFAULT 'in_app'"),
        ("status", "TEXT NOT NULL DEFAULT 'pending'"),
        ("reference_type", "TEXT"),
        ("reference_id", "INTEGER"),
        ("created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ("sent_at", "TEXT"),
        ("read_at", "TEXT"),
    ]

    for name, definition in notification_columns:
        add_column_if_missing(
            db,
            "notifications",
            name,
            definition,
        )

    email_columns = [
        ("user_id", "INTEGER"),
        ("recipient", "TEXT NOT NULL DEFAULT ''"),
        ("subject", "TEXT NOT NULL DEFAULT ''"),
        ("template", "TEXT"),
        ("message_body", "TEXT NOT NULL DEFAULT ''"),
        ("provider_message_id", "TEXT"),
        ("status", "TEXT NOT NULL DEFAULT 'queued'"),
        ("error_message", "TEXT"),
        ("created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ("sent_at", "TEXT"),
    ]

    for name, definition in email_columns:
        add_column_if_missing(
            db,
            "email_logs",
            name,
            definition,
        )

    sms_columns = [
        ("user_id", "INTEGER"),
        ("recipient", "TEXT NOT NULL DEFAULT ''"),
        ("message_body", "TEXT NOT NULL DEFAULT ''"),
        ("provider_message_id", "TEXT"),
        ("status", "TEXT NOT NULL DEFAULT 'queued'"),
        ("error_message", "TEXT"),
        ("created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ("sent_at", "TEXT"),
    ]

    for name, definition in sms_columns:
        add_column_if_missing(
            db,
            "sms_logs",
            name,
            definition,
        )

    profile_columns = [
        ("display_name", "TEXT"),
        ("timezone", "TEXT NOT NULL DEFAULT 'Asia/Kolkata'"),
        ("currency", "TEXT NOT NULL DEFAULT 'INR'"),
        ("locale", "TEXT NOT NULL DEFAULT 'en-IN'"),
        ("avatar_initials", "TEXT"),
        ("created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ]

    for name, definition in profile_columns:
        add_column_if_missing(
            db,
            "user_profiles",
            name,
            definition,
        )

    preference_columns = [
        ("email_enabled", "INTEGER NOT NULL DEFAULT 1"),
        ("budget_alerts", "INTEGER NOT NULL DEFAULT 1"),
        ("transaction_alerts", "INTEGER NOT NULL DEFAULT 1"),
        ("monthly_summary", "INTEGER NOT NULL DEFAULT 1"),
        ("unusual_spending_alerts", "INTEGER NOT NULL DEFAULT 1"),
        ("created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ]

    for name, definition in preference_columns:
        add_column_if_missing(
            db,
            "notification_preferences",
            name,
            definition,
        )

    workspace_columns = [
        ("name", "TEXT NOT NULL DEFAULT 'Personal Space'"),
        ("workspace_type", "TEXT NOT NULL DEFAULT 'personal'"),
        ("owner_user_id", "INTEGER"),
        ("created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ]

    for name, definition in workspace_columns:
        add_column_if_missing(
            db,
            "workspaces",
            name,
            definition,
        )

    if column_exists(
        db,
        "workspaces",
        "owner_id",
    ):

        db.execute(
            """
            UPDATE workspaces
            SET owner_user_id = owner_id
            WHERE owner_user_id IS NULL
              AND owner_id IS NOT NULL
            """
        )

        db.execute(
            """
            UPDATE workspaces
            SET owner_user_id = owner_id
            WHERE owner_id IS NOT NULL
              AND (
                    owner_user_id IS NULL
                    OR owner_user_id != owner_id
              )
            """
        )

    member_columns = [
        ("workspace_id", "INTEGER"),
        ("user_id", "INTEGER"),
        ("role", "TEXT NOT NULL DEFAULT 'member'"),
        ("joined_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ]

    for name, definition in member_columns:
        add_column_if_missing(
            db,
            "workspace_members",
            name,
            definition,
        )

    voice_columns = [
        ("user_id", "INTEGER"),
        ("transcript", "TEXT NOT NULL DEFAULT ''"),
        ("parsed_kind", "TEXT"),
        ("parsed_amount", "REAL"),
        ("parsed_category", "TEXT"),
        ("parsed_payment_method", "TEXT"),
        ("parsed_date", "TEXT"),
        ("parsed_note", "TEXT"),
        ("status", "TEXT NOT NULL DEFAULT 'received'"),
        ("transaction_id", "INTEGER"),
        ("created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ]

    for name, definition in voice_columns:
        add_column_if_missing(
            db,
            "voice_commands",
            name,
            definition,
        )


# ============================================================
# TRANSACTION / BUDGET MIGRATION
# ============================================================

def migrate_transaction_tables(db):

    add_column_if_missing(
        db,
        "transactions",
        "workspace_id",
        "INTEGER",
    )

    add_column_if_missing(
        db,
        "transactions",
        "source",
        "TEXT NOT NULL DEFAULT 'manual'",
    )

    add_column_if_missing(
        db,
        "transactions",
        "source_reference",
        "TEXT",
    )

    add_column_if_missing(
        db,
        "budgets",
        "workspace_id",
        "INTEGER",
    )


# ============================================================
# USER FOUNDATION
# ============================================================

def ensure_user_foundation(db):

    users = db.execute(
        """
        SELECT id, name
        FROM users
        ORDER BY id
        """
    ).fetchall()

    legacy_owner_column = column_exists(
        db,
        "workspaces",
        "owner_id",
    )

    for user in users:

        user_id = user["id"]
        name = (user["name"] or "").strip()

        parts = [
            part
            for part in name.split()
            if part
        ]

        initials = "".join(
            part[0]
            for part in parts
        )[:2].upper()

        if not initials:
            initials = "U"

        db.execute(
            """
            INSERT OR IGNORE INTO user_profiles(
                user_id,
                display_name,
                timezone,
                currency,
                locale,
                avatar_initials
            )
            VALUES(
                ?,
                ?,
                'Asia/Kolkata',
                'INR',
                'en-IN',
                ?
            )
            """,
            (
                user_id,
                name,
                initials,
            ),
        )

        db.execute(
            """
            INSERT OR IGNORE INTO notification_preferences(
                user_id
            )
            VALUES(?)
            """,
            (user_id,),
        )

        workspace = db.execute(
            """
            SELECT id
            FROM workspaces
            WHERE owner_user_id=?
              AND workspace_type='personal'
            ORDER BY id
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        if workspace is None:

            workspace_name = (
                f"{name or 'User'}'s Personal Space"
            )

            if legacy_owner_column:

                cursor = db.execute(
                    """
                    INSERT INTO workspaces(
                        name,
                        workspace_type,
                        owner_user_id,
                        owner_id
                    )
                    VALUES(
                        ?,
                        'personal',
                        ?,
                        ?
                    )
                    """,
                    (
                        workspace_name,
                        user_id,
                        user_id,
                    ),
                )

            else:

                cursor = db.execute(
                    """
                    INSERT INTO workspaces(
                        name,
                        workspace_type,
                        owner_user_id
                    )
                    VALUES(
                        ?,
                        'personal',
                        ?
                    )
                    """,
                    (
                        workspace_name,
                        user_id,
                    ),
                )

            workspace_id = cursor.lastrowid

        else:

            workspace_id = workspace["id"]

            if legacy_owner_column:

                db.execute(
                    """
                    UPDATE workspaces
                    SET owner_user_id = ?,
                        owner_id = ?
                    WHERE id = ?
                    """,
                    (
                        user_id,
                        user_id,
                        workspace_id,
                    ),
                )

        db.execute(
            """
            INSERT OR IGNORE INTO workspace_members(
                workspace_id,
                user_id,
                role
            )
            VALUES(
                ?,
                ?,
                'owner'
            )
            """,
            (
                workspace_id,
                user_id,
            ),
        )


# ============================================================
# LINK EXISTING DATA
# ============================================================

def connect_existing_data(db):

    db.execute(
        """
        UPDATE transactions
        SET workspace_id = (
            SELECT w.id
            FROM workspaces w
            WHERE w.owner_user_id = transactions.user_id
              AND w.workspace_type = 'personal'
            ORDER BY w.id
            LIMIT 1
        )
        WHERE workspace_id IS NULL
        """
    )

    db.execute(
        """
        UPDATE budgets
        SET workspace_id = (
            SELECT w.id
            FROM workspaces w
            WHERE w.owner_user_id = budgets.user_id
              AND w.workspace_type = 'personal'
            ORDER BY w.id
            LIMIT 1
        )
        WHERE workspace_id IS NULL
        """
    )


# ============================================================
# INDEXES
# ============================================================

def create_indexes(db):

    indexes = [
        """
        CREATE INDEX IF NOT EXISTS
        idx_transactions_user_date
        ON transactions(user_id, transaction_date DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_transactions_user_kind
        ON transactions(user_id, kind)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_transactions_user_category
        ON transactions(user_id, category)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_transactions_workspace
        ON transactions(workspace_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_transactions_source
        ON transactions(source)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_budgets_user_month
        ON budgets(user_id, month)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_budgets_workspace
        ON budgets(workspace_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_notifications_user_created
        ON notifications(user_id, created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_notifications_user_status
        ON notifications(user_id, status)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_email_logs_user_created
        ON email_logs(user_id, created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_email_logs_status
        ON email_logs(status, created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_sms_logs_user_created
        ON sms_logs(user_id, created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_sms_logs_status
        ON sms_logs(status, created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_voice_commands_user_created
        ON voice_commands(user_id, created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_workspace_members_user
        ON workspace_members(user_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS
        idx_workspace_members_workspace
        ON workspace_members(workspace_id)
        """,
    ]

    for statement in indexes:
        db.execute(statement)


# ============================================================
# MAIN MIGRATION
# ============================================================

def migrate_db(db):

    db.executescript(SCHEMA)

    migrate_support_tables(db)

    migrate_transaction_tables(db)

    ensure_user_foundation(db)

    connect_existing_data(db)

    create_indexes(db)

    if not using_postgres(db):
        db.execute(
            "PRAGMA user_version = 3"
        )

    db.commit()


# ============================================================
# APP INITIALIZATION
# ============================================================

def init_db(app):

    if app.config.get("DATABASE_URL"):

        db = PostgresDB(
            app.config["DATABASE_URL"]
        )

        try:
            migrate_db(db)
        finally:
            db.close()

    else:

        database_path = Path(
            app.config["DATABASE"]
        )

        database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        db = sqlite3.connect(
            str(database_path)
        )

        db.row_factory = sqlite3.Row

        try:

            db.execute(
                "PRAGMA foreign_keys = ON"
            )

            db.execute(
                "PRAGMA busy_timeout = 5000"
            )

            migrate_db(db)

        finally:

            db.close()

    app.teardown_appcontext(
        close_db
    )


