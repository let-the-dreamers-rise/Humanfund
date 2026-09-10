"""SQLite repository for indexed blocks and transfers.

Repository pattern: business logic (the indexer) depends on these methods, not on
SQL. All writes are parameterized. Reorg safety lives in rollback_from().
"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS blocks (
  number      INTEGER PRIMARY KEY,
  hash        TEXT NOT NULL,
  parent_hash TEXT,
  timestamp   INTEGER,
  tx_count    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS transfers (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  block_number INTEGER NOT NULL,
  tx_hash      TEXT,
  log_index    INTEGER,
  token        TEXT,
  from_addr    TEXT,
  to_addr      TEXT,
  value        TEXT,
  standard     TEXT
);
CREATE INDEX IF NOT EXISTS ix_transfers_block ON transfers(block_number);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


class Store:
    def __init__(self, path=":memory:"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # --- cursor ---------------------------------------------------------------
    def get_cursor(self):
        row = self.conn.execute("SELECT value FROM meta WHERE key='cursor'").fetchone()
        return int(row["value"]) if row else None

    def set_cursor(self, number):
        self.conn.execute(
            "INSERT INTO meta(key,value) VALUES('cursor',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(int(number)),),
        )
        self.conn.commit()

    # --- blocks ---------------------------------------------------------------
    def get_block_hash(self, number):
        row = self.conn.execute(
            "SELECT hash FROM blocks WHERE number=?", (number,)
        ).fetchone()
        return row["hash"] if row else None

    def insert_block(self, number, hash, parent, ts, tx_count):
        self.conn.execute(
            "INSERT INTO blocks(number,hash,parent_hash,timestamp,tx_count) VALUES(?,?,?,?,?) "
            "ON CONFLICT(number) DO UPDATE SET "
            "hash=excluded.hash, parent_hash=excluded.parent_hash, "
            "timestamp=excluded.timestamp, tx_count=excluded.tx_count",
            (number, hash, parent, ts, tx_count),
        )
        self.conn.commit()

    def insert_transfers(self, rows):
        """rows: iterable of (block_number, tx_hash, log_index, token, from, to, value, standard)."""
        rows = list(rows)
        if not rows:
            return 0
        self.conn.executemany(
            "INSERT INTO transfers"
            "(block_number,tx_hash,log_index,token,from_addr,to_addr,value,standard) "
            "VALUES(?,?,?,?,?,?,?,?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    # --- reorg safety ---------------------------------------------------------
    def rollback_from(self, number):
        """Delete every block and transfer at or above `number` (orphaned by a reorg)."""
        self.conn.execute("DELETE FROM transfers WHERE block_number>=?", (number,))
        self.conn.execute("DELETE FROM blocks WHERE number>=?", (number,))
        self.conn.commit()

    # --- reads ----------------------------------------------------------------
    def block_count(self):
        return self.conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]

    def transfer_count(self):
        return self.conn.execute("SELECT COUNT(*) FROM transfers").fetchone()[0]

    def recent_transfers(self, limit=15):
        cur = self.conn.execute(
            "SELECT block_number,token,from_addr,to_addr,value,standard "
            "FROM transfers ORDER BY block_number DESC, log_index DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]

    def close(self):
        self.conn.close()
