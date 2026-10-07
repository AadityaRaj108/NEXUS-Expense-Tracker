import sqlite3
from pathlib import Path

from flask import current_app, g


# ============================================================
# NEXUS DATABASE
# ============================================================
#
# Safe, idempotent database initialization + migration.
#
# IMPORTANT:
# Existing users, transactions and budgets are preserved.
# Existing tables are NEVER dropped or recreated.
#
# Legacy workspace schemas are handled safely, including the
# older "owner_id" column used by previous NEXUS versions.
#
# Communication history:
#   - email_logs
#   - sms_logs
#
# Both email and SMS records are retained for tracking,
# debugging and future communication-history UI.
# ============================================================


SCHEMA = """
PRAGMA foreign_keys = ON;


-- ============================================================
-- ORIGINAL NEXUS TABLES
-- ============================================================

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

    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    month TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),

    UNIQUE(user_id, category, month),

    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- USER PROFILE
-- ============================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INTEGER PRIMARY KEY,
    display_name TEXT,
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    currency TEXT NOT NULL DEFAULT 'INR',
    locale TEXT NOT NULL DEFAULT 'en-IN',
    avatar_initials TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- NOTIFICATION PREFERENCES
-- ============================================================

CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id INTEGER PRIMARY KEY,

    email_enabled INTEGER NOT NULL DEFAULT 1
        CHECK(email_enabled IN (0,1)),

    budget_alerts INTEGER NOT NULL DEFAULT 1
        CHECK(budget_alerts IN (0,1)),

    transaction_alerts INTEGER NOT NULL DEFAULT 1
        CHECK(transaction_alerts IN (0,1)),

    monthly_summary INTEGER NOT NULL DEFAULT 1
        CHECK(monthly_summary IN (0,1)),

    unusual_spending_alerts INTEGER NOT NULL DEFAULT 1
        CHECK(unusual_spending_alerts IN (0,1)),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- NOTIFICATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,

    notification_type TEXT NOT NULL DEFAULT 'system',
    title TEXT NOT NULL DEFAULT 'NEXUS Notification',
    message TEXT NOT NULL DEFAULT '',

    channel TEXT NOT NULL DEFAULT 'in_app',

    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(
            status IN (
                'pending',
                'queued',
                'sent',
                'read',
                'failed'
            )
        ),

    reference_type TEXT,
    reference_id INTEGER,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,
    read_at TEXT,

    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- EMAIL LOG
-- ============================================================

CREATE TABLE IF NOT EXISTS email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,

    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,

    template TEXT,

    message_body TEXT NOT NULL DEFAULT '',

    provider_message_id TEXT,

    status TEXT NOT NULL DEFAULT 'queued'
        CHECK(
            status IN (
                'queued',
                'sent',
                'failed'
            )
        ),

    error_message TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,

    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE SET NULL
);


-- ============================================================
-- SMS LOG
-- ============================================================

CREATE TABLE IF NOT EXISTS sms_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,

    recipient TEXT NOT NULL,

    message_body TEXT NOT NULL,

    provider_message_id TEXT,

    status TEXT NOT NULL DEFAULT 'queued'
        CHECK(
            status IN (
                'queued',
                'sent',
                'failed'
            )
        ),

    error_message TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,

    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE SET NULL
);


-- ============================================================
-- WORKSPACES
-- ============================================================

CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL,

    workspace_type TEXT NOT NULL DEFAULT 'personal'
        CHECK(
            workspace_type IN (
                'personal',
                'family',
                'team'
            )
        ),

    owner_user_id INTEGER NOT NULL,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(owner_user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- WORKSPACE MEMBERS
-- ============================================================

CREATE TABLE IF NOT EXISTS workspace_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    workspace_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,

    role TEXT NOT NULL DEFAULT 'member'
        CHECK(
            role IN (
                'owner',
                'admin',
                'member',
                'viewer'
            )
        ),

    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(workspace_id, user_id),

    FOREIGN KEY(workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- VOICE COMMAND HISTORY
-- ============================================================

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
        CHECK(
            status IN (
                'received',
                'parsed',
                'confirmed',
                'rejected',
                'failed'
            )
        ),

    transaction_id INTEGER,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY(transaction_id)
        REFERENCES transactions(id)
        ON DELETE SET NULL
);
"""


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():
    if "db" not in g:
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


# ============================================================
# CLOSE CONNECTION
# ============================================================

def close_db(_error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


# ============================================================
# SCHEMA HELPERS
# ============================================================

def table_exists(db, table_name):
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


def column_exists(db, table_name, column_name):
    if not table_exists(db, table_name):
        return False

    columns = db.execute(
        f"PRAGMA table_info({table_name})"
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
# MIGRATE EXISTING SUPPORT TABLES
# ============================================================

def migrate_support_tables(db):
    """
    Existing databases may already contain some of the new
    tables from an earlier attempt.

    SQLite CREATE TABLE IF NOT EXISTS does NOT upgrade an
    existing table, so we explicitly add missing columns.

    Special handling is included for legacy workspaces that
    used owner_id instead of owner_user_id.
    """

    # --------------------------------------------------------
    # notifications
    # --------------------------------------------------------

    notification_columns = [
        (
            "notification_type",
            "TEXT NOT NULL DEFAULT 'system'",
        ),
        (
            "title",
            "TEXT NOT NULL DEFAULT 'NEXUS Notification'",
        ),
        (
            "message",
            "TEXT NOT NULL DEFAULT ''",
        ),
        (
            "channel",
            "TEXT NOT NULL DEFAULT 'in_app'",
        ),
        (
            "status",
            "TEXT NOT NULL DEFAULT 'pending'",
        ),
        (
            "reference_type",
            "TEXT",
        ),
        (
            "reference_id",
            "INTEGER",
        ),
        (
            "created_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ),
        (
            "sent_at",
            "TEXT",
        ),
        (
            "read_at",
            "TEXT",
        ),
    ]

    for name, definition in notification_columns:
        add_column_if_missing(
            db,
            "notifications",
            name,
            definition,
        )

    # --------------------------------------------------------
    # email_logs
    # --------------------------------------------------------

    email_columns = [
        (
            "user_id",
            "INTEGER",
        ),
        (
            "recipient",
            "TEXT NOT NULL DEFAULT ''",
        ),
        (
            "subject",
            "TEXT NOT NULL DEFAULT ''",
        ),
        (
            "template",
            "TEXT",
        ),
        (
            "message_body",
            "TEXT NOT NULL DEFAULT ''",
        ),
        (
            "provider_message_id",
            "TEXT",
        ),
        (
            "status",
            "TEXT NOT NULL DEFAULT 'queued'",
        ),
        (
            "error_message",
            "TEXT",
        ),
        (
            "created_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ),
        (
            "sent_at",
            "TEXT",
        ),
    ]

    for name, definition in email_columns:
        add_column_if_missing(
            db,
            "email_logs",
            name,
            definition,
        )

    # --------------------------------------------------------
    # sms_logs
    # --------------------------------------------------------
    #
    # Fresh databases receive this table from SCHEMA.
    #
    # Existing databases that somehow already contain an
    # sms_logs table are upgraded safely with missing columns.
    # --------------------------------------------------------

    sms_columns = [
        (
            "user_id",
            "INTEGER",
        ),
        (
            "recipient",
            "TEXT NOT NULL DEFAULT ''",
        ),
        (
            "message_body",
            "TEXT NOT NULL DEFAULT ''",
        ),
        (
            "provider_message_id",
            "TEXT",
        ),
        (
            "status",
            "TEXT NOT NULL DEFAULT 'queued'",
        ),
        (
            "error_message",
            "TEXT",
        ),
        (
            "created_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ),
        (
            "sent_at",
            "TEXT",
        ),
    ]

    for name, definition in sms_columns:
        add_column_if_missing(
            db,
            "sms_logs",
            name,
            definition,
        )

    # --------------------------------------------------------
    # user_profiles
    # --------------------------------------------------------

    profile_columns = [
        (
            "display_name",
            "TEXT",
        ),
        (
            "timezone",
            "TEXT NOT NULL DEFAULT 'Asia/Kolkata'",
        ),
        (
            "currency",
            "TEXT NOT NULL DEFAULT 'INR'",
        ),
        (
            "locale",
            "TEXT NOT NULL DEFAULT 'en-IN'",
        ),
        (
            "avatar_initials",
            "TEXT",
        ),
        (
            "created_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ),
        (
            "updated_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ),
    ]

    for name, definition in profile_columns:
        add_column_if_missing(
            db,
            "user_profiles",
            name,
            definition,
        )

    # --------------------------------------------------------
    # notification_preferences
    # --------------------------------------------------------

    preference_columns = [
        (
            "email_enabled",
            "INTEGER NOT NULL DEFAULT 1",
        ),
        (
            "budget_alerts",
            "INTEGER NOT NULL DEFAULT 1",
        ),
        (
            "transaction_alerts",
            "INTEGER NOT NULL DEFAULT 1",
        ),
        (
            "monthly_summary",
            "INTEGER NOT NULL DEFAULT 1",
        ),
        (
            "unusual_spending_alerts",
            "INTEGER NOT NULL DEFAULT 1",
        ),
        (
            "created_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ),
        (
            "updated_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ),
    ]

    for name, definition in preference_columns:
        add_column_if_missing(
            db,
            "notification_preferences",
            name,
            definition,
        )

    # --------------------------------------------------------
    # workspaces
    # --------------------------------------------------------
    #
    # IMPORTANT:
    # Older NEXUS databases may contain:
    #
    #     owner_id INTEGER NOT NULL
    #
    # while newer NEXUS code uses:
    #
    #     owner_user_id INTEGER
    #
    # We preserve the old column and synchronize it with the
    # new column instead of dropping/recreating the table.
    # --------------------------------------------------------

    workspace_columns = [
        (
            "name",
            "TEXT NOT NULL DEFAULT 'Personal Space'",
        ),
        (
            "workspace_type",
            "TEXT NOT NULL DEFAULT 'personal'",
        ),
        (
            "owner_user_id",
            "INTEGER",
        ),
        (
            "created_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ),
    ]

    for name, definition in workspace_columns:
        add_column_if_missing(
            db,
            "workspaces",
            name,
            definition,
        )

    # --------------------------------------------------------
    # LEGACY WORKSPACE OWNER MIGRATION
    # --------------------------------------------------------

    if column_exists(db, "workspaces", "owner_id"):

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

    # --------------------------------------------------------
    # workspace_members
    # --------------------------------------------------------

    member_columns = [
        (
            "workspace_id",
            "INTEGER",
        ),
        (
            "user_id",
            "INTEGER",
        ),
        (
            "role",
            "TEXT NOT NULL DEFAULT 'member'",
        ),
        (
            "joined_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ),
    ]

    for name, definition in member_columns:
        add_column_if_missing(
            db,
            "workspace_members",
            name,
            definition,
        )

    # --------------------------------------------------------
    # voice_commands
    # --------------------------------------------------------

    voice_columns = [
        (
            "user_id",
            "INTEGER",
        ),
        (
            "transcript",
            "TEXT NOT NULL DEFAULT ''",
        ),
        (
            "parsed_kind",
            "TEXT",
        ),
        (
            "parsed_amount",
            "REAL",
        ),
        (
            "parsed_category",
            "TEXT",
        ),
        (
            "parsed_payment_method",
            "TEXT",
        ),
        (
            "parsed_date",
            "TEXT",
        ),
        (
            "parsed_note",
            "TEXT",
        ),
        (
            "status",
            "TEXT NOT NULL DEFAULT 'received'",
        ),
        (
            "transaction_id",
            "INTEGER",
        ),
        (
            "created_at",
            "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ),
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
    """
    Adds future-compatible fields to the original NEXUS
    transaction and budget tables.
    """

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
# EXISTING USER FOUNDATION
# ============================================================

def ensure_user_foundation(db):
    """
    Give every existing user:
        - profile
        - notification preferences
        - personal workspace
        - owner membership
    """

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

        # ----------------------------------------------------
        # Profile
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Notification preferences
        # ----------------------------------------------------

        db.execute(
            """
            INSERT OR IGNORE INTO notification_preferences(
                user_id
            )
            VALUES(?)
            """,
            (user_id,),
        )

        # ----------------------------------------------------
        # Personal workspace
        # ----------------------------------------------------

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

            # ------------------------------------------------
            # IMPORTANT LEGACY COMPATIBILITY
            # ------------------------------------------------

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

            # ------------------------------------------------
            # Keep legacy owner_id synchronized if it exists.
            # ------------------------------------------------

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

        # ----------------------------------------------------
        # Workspace membership
        # ----------------------------------------------------

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
# LINK OLD DATA TO PERSONAL WORKSPACE
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

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_transactions_user_date
        ON transactions(
            user_id,
            transaction_date DESC
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_transactions_user_kind
        ON transactions(
            user_id,
            kind
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_transactions_user_category
        ON transactions(
            user_id,
            category
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_transactions_workspace
        ON transactions(
            workspace_id
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_transactions_source
        ON transactions(
            source
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_budgets_user_month
        ON budgets(
            user_id,
            month
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_budgets_workspace
        ON budgets(
            workspace_id
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_notifications_user_created
        ON notifications(
            user_id,
            created_at DESC
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_notifications_user_status
        ON notifications(
            user_id,
            status
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_email_logs_user_created
        ON email_logs(
            user_id,
            created_at DESC
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_email_logs_status
        ON email_logs(
            status,
            created_at DESC
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_sms_logs_user_created
        ON sms_logs(
            user_id,
            created_at DESC
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_sms_logs_status
        ON sms_logs(
            status,
            created_at DESC
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_voice_commands_user_created
        ON voice_commands(
            user_id,
            created_at DESC
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_workspace_members_user
        ON workspace_members(
            user_id
        )
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_workspace_members_workspace
        ON workspace_members(
            workspace_id
        )
        """
    )


# ============================================================
# MAIN MIGRATION
# ============================================================

def migrate_db(db):

    # --------------------------------------------------------
    # STEP 1
    # Create missing tables only.
    # --------------------------------------------------------

    db.executescript(SCHEMA)

    # --------------------------------------------------------
    # STEP 2
    # Upgrade tables that already existed.
    # --------------------------------------------------------

    migrate_support_tables(db)

    migrate_transaction_tables(db)

    # --------------------------------------------------------
    # STEP 3
    # Make sure every existing user has the new foundation.
    # --------------------------------------------------------

    ensure_user_foundation(db)

    # --------------------------------------------------------
    # STEP 4
    # Link existing transactions/budgets to personal space.
    # --------------------------------------------------------

    connect_existing_data(db)

    # --------------------------------------------------------
    # STEP 5
    # ONLY NOW create indexes.
    # --------------------------------------------------------

    create_indexes(db)

    # --------------------------------------------------------
    # STEP 6
    # Mark migration version.
    # --------------------------------------------------------

    db.execute(
        "PRAGMA user_version = 3"
    )

    db.commit()


# ============================================================
# APP INITIALIZATION
# ============================================================

def init_db(app):

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

