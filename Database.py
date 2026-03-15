import sqlite3
import json
import hashlib
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

DB_PATH = "fishquest.db"


class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path

    
    @contextmanager
    def _conn(self):
        """Context manager that yields a WAL-mode connection with row_factory."""
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")   
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    # Schema 

    def init(self):
        """Create all tables (idempotent — safe to call on every startup)."""
        with self._conn() as con:
            con.executescript("""
            -- ── Users ──────────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL UNIQUE,
                email       TEXT    NOT NULL UNIQUE,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            -- ── Catches ─────────────────────────────────────────────────────
            -- One row per submitted image that passed the classifier threshold.
            -- Detection dict from fish_detector.detect_fish() maps directly here.
            CREATE TABLE IF NOT EXISTS catches (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                species         TEXT    NOT NULL,
                confidence      REAL    NOT NULL,
                rarity          TEXT    NOT NULL,   -- common|uncommon|rare|legendary
                rarity_score    REAL    NOT NULL,   -- 0.0–1.0 from rewards.compute_rarity()
                habitat         TEXT,
                ocean_region    TEXT,
                model_version   TEXT,
                latitude        REAL,
                longitude       REAL,
                caught_at       TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_catches_user    ON catches(user_id);
            CREATE INDEX IF NOT EXISTS idx_catches_species ON catches(species);
            CREATE INDEX IF NOT EXISTS idx_catches_geo     ON catches(latitude, longitude);

            -- ── Species collection (Pokédex) ─────────────────────────────────
            -- One row per unique species per user.
            -- Updated on each new catch; first_caught_at never changes.
            CREATE TABLE IF NOT EXISTS species_collection (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                species         TEXT    NOT NULL,
                catch_count     INTEGER NOT NULL DEFAULT 1,
                best_confidence REAL    NOT NULL,
                rarity          TEXT    NOT NULL,
                first_caught_at TEXT    NOT NULL DEFAULT (datetime('now')),
                last_caught_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_id, species)
            );
            CREATE INDEX IF NOT EXISTS idx_collection_user ON species_collection(user_id);

            -- ── Rewards catalog ──────────────────────────────────────────────
            -- Populated by admin / seed data; read by rewards.py.
            CREATE TABLE IF NOT EXISTS rewards (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                title         TEXT    NOT NULL,
                description   TEXT,
                partner_name  TEXT    NOT NULL,
                partner_type  TEXT    NOT NULL,   -- restaurant | attraction
                discount_pct  INTEGER NOT NULL DEFAULT 10,
                trigger_type  TEXT    NOT NULL,   -- milestone | rarity
                trigger_value TEXT    NOT NULL,   -- "5"|"10"|"rare"|"legendary"
                is_active     INTEGER NOT NULL DEFAULT 1,
                expires_at    TEXT
            );

            -- ── User rewards (earned QR codes) ───────────────────────────────
            CREATE TABLE IF NOT EXISTS user_rewards (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(id),
                reward_id     INTEGER NOT NULL REFERENCES rewards(id),
                token         TEXT    NOT NULL UNIQUE,
                qr_image_b64  TEXT,                   -- base64 PNG, set after generation
                is_redeemed   INTEGER NOT NULL DEFAULT 0,
                unlocked_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                redeemed_at   TEXT,
                UNIQUE(user_id, reward_id)             -- one reward per user
            );
            CREATE INDEX IF NOT EXISTS idx_ur_user  ON user_rewards(user_id);
            CREATE INDEX IF NOT EXISTS idx_ur_token ON user_rewards(token);

            -- ── Redemption audit log ─────────────────────────────────────────
            -- Immutable record every time a QR is scanned, valid or not.
            CREATE TABLE IF NOT EXISTS redemptions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                token         TEXT    NOT NULL,
                scanned_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                was_valid     INTEGER NOT NULL,   -- 1 = accepted, 0 = rejected
                reject_reason TEXT                -- null if accepted
            );
            """)
        self._seed_rewards()
        print(f"✓ Database ready: {self.path}")

    
    def create_user(self, username: str, email: str) -> int:
        """Insert a new user. Returns new user id."""
        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO users (username, email) VALUES (?, ?)",
                (username, email),
            )
            return cur.lastrowid

    def get_user(self, user_id: int) -> Optional[dict]:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[dict]:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            return dict(row) if row else None

    
    def record_catch(
        self,
        user_id: int,
        detection: dict,        
        rarity_score: float,    
        rarity_tier: str,       
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> tuple[int, list[dict]]:
        """
        Save a catch, update the species collection, check for newly
        unlocked rewards, and return (catch_id, list_of_new_reward_dicts).

        Detection dict shape (from fish_detector.detect_fish()):
            is_fish, species, confidence, habitat, ocean_region, model_version
        """
        with self._conn() as con:
            
            cur = con.execute(
                """INSERT INTO catches
                   (user_id, species, confidence, rarity, rarity_score,
                    habitat, ocean_region, model_version, latitude, longitude)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    detection["species"],
                    detection["confidence"],
                    rarity_tier,
                    rarity_score,
                    detection.get("habitat", ""),
                    detection.get("ocean_region", ""),
                    detection.get("model_version", ""),
                    latitude,
                    longitude,
                ),
            )
            catch_id = cur.lastrowid

            
            con.execute(
                """INSERT INTO species_collection
                       (user_id, species, catch_count, best_confidence,
                        rarity, last_caught_at)
                   VALUES (?, ?, 1, ?, ?, datetime('now'))
                   ON CONFLICT(user_id, species) DO UPDATE SET
                       catch_count     = catch_count + 1,
                       best_confidence = MAX(best_confidence, excluded.best_confidence),
                       last_caught_at  = excluded.last_caught_at""",
                (user_id, detection["species"], detection["confidence"], rarity_tier),
            )

            
            total_catches = con.execute(
                "SELECT COUNT(*) FROM catches WHERE user_id = ?", (user_id,)
            ).fetchone()[0]

            new_rewards = self._unlock_rewards(
                con, user_id, rarity_tier, total_catches
            )

        return catch_id, new_rewards

    def get_catches(self, user_id: int, limit: int = 50) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                """SELECT * FROM catches WHERE user_id = ?
                   ORDER BY caught_at DESC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_area_species(
        self, lat: float, lon: float, radius_deg: float = 0.1
    ) -> list[str]:
        """Return species names from catches within ~11 km (used for local rarity)."""
        with self._conn() as con:
            rows = con.execute(
                """SELECT species FROM catches
                   WHERE latitude  BETWEEN ? AND ?
                     AND longitude BETWEEN ? AND ?""",
                (lat - radius_deg, lat + radius_deg,
                 lon - radius_deg, lon + radius_deg),
            ).fetchall()
            return [r["species"] for r in rows]
        
    def get_collection(self, user_id: int) -> list[dict]:
        """Full Pokédex for a user, sorted rarest first."""
        with self._conn() as con:
            rows = con.execute(
                """SELECT * FROM species_collection
                   WHERE user_id = ?
                   ORDER BY
                     CASE rarity
                       WHEN 'legendary' THEN 1
                       WHEN 'rare'      THEN 2
                       WHEN 'uncommon'  THEN 3
                       ELSE 4
                     END,
                     catch_count DESC""",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def has_caught_species(self, user_id: int, species: str) -> bool:
        with self._conn() as con:
            row = con.execute(
                "SELECT 1 FROM species_collection WHERE user_id=? AND species=?",
                (user_id, species),
            ).fetchone()
            return row is not None

    # ── Stats + leaderboard ────────────────────────────────────────────────────

    def get_user_stats(self, user_id: int) -> dict:
        """Catch stats + milestone progress for one user."""
        MILESTONES = [5, 10, 25, 50, 100]
        with self._conn() as con:
            total = con.execute(
                "SELECT COUNT(*) FROM catches WHERE user_id=?", (user_id,)
            ).fetchone()[0]

            unique = con.execute(
                "SELECT COUNT(*) FROM species_collection WHERE user_id=?", (user_id,)
            ).fetchone()[0]

            rarity_counts = {
                r["rarity"]: r["cnt"]
                for r in con.execute(
                    """SELECT rarity, COUNT(*) as cnt
                       FROM catches WHERE user_id=?
                       GROUP BY rarity""",
                    (user_id,),
                ).fetchall()
            }

        next_ms = next((m for m in MILESTONES if m > total), None)
        return {
            "total_catches":           total,
            "unique_species":          unique,
            "catches_by_rarity":       rarity_counts,
            "next_milestone":          next_ms,
            "catches_to_next_milestone": (next_ms - total) if next_ms else None,
        }

    def get_leaderboard(self, limit: int = 10) -> list[dict]:
        """
        Global leaderboard ranked by:
          1. unique species discovered
          2. legendary catches
          3. total catches
        """
        with self._conn() as con:
            rows = con.execute(
                """SELECT
                       u.id,
                       u.username,
                       COUNT(DISTINCT sc.species)                       AS unique_species,
                       COUNT(c.id)                                      AS total_catches,
                       SUM(CASE WHEN c.rarity='legendary' THEN 1 ELSE 0 END) AS legendary_catches,
                       SUM(CASE WHEN c.rarity='rare'      THEN 1 ELSE 0 END) AS rare_catches
                   FROM users u
                   LEFT JOIN catches          c  ON c.user_id  = u.id
                   LEFT JOIN species_collection sc ON sc.user_id = u.id
                   GROUP BY u.id
                   ORDER BY unique_species DESC,
                            legendary_catches DESC,
                            total_catches DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    #Rewards

    def get_user_rewards(self, user_id: int) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                """SELECT ur.*, r.title, r.description, r.partner_name,
                          r.partner_type, r.discount_pct
                   FROM user_rewards ur
                   JOIN rewards r ON r.id = ur.reward_id
                   WHERE ur.user_id = ?
                   ORDER BY ur.unlocked_at DESC""",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_reward_by_token(self, token: str) -> Optional[dict]:
        with self._conn() as con:
            row = con.execute(
                """SELECT ur.*, r.title, r.partner_name, r.discount_pct
                   FROM user_rewards ur
                   JOIN rewards r ON r.id = ur.reward_id
                   WHERE ur.token = ?""",
                (token,),
            ).fetchone()
            return dict(row) if row else None

    def redeem_reward(self, token: str) -> dict:
        """
        Mark a reward as redeemed (one-time use).
        Returns result dict with 'success' bool and 'message'.
        Logs every scan to the redemptions table regardless of outcome.
        """
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM user_rewards WHERE token=?", (token,)
            ).fetchone()

            if not row:
                con.execute(
                    "INSERT INTO redemptions (token, was_valid, reject_reason) VALUES (?,0,?)",
                    (token, "token_not_found"),
                )
                return {"success": False, "message": "Invalid QR code."}

            if row["is_redeemed"]:
                con.execute(
                    "INSERT INTO redemptions (token, was_valid, reject_reason) VALUES (?,0,?)",
                    (token, "already_redeemed"),
                )
                return {
                    "success": False,
                    "message": f"Already redeemed on {row['redeemed_at']}.",
                }

            con.execute(
                """UPDATE user_rewards
                   SET is_redeemed=1, redeemed_at=datetime('now')
                   WHERE token=?""",
                (token,),
            )
            con.execute(
                "INSERT INTO redemptions (token, was_valid) VALUES (?,1)", (token,)
            )

            reward_row = con.execute(
                "SELECT * FROM rewards WHERE id=?", (row["reward_id"],)
            ).fetchone()

            return {
                "success":      True,
                "message":      "Reward redeemed successfully!",
                "reward_title": reward_row["title"],
                "partner_name": reward_row["partner_name"],
                "discount_pct": reward_row["discount_pct"],
            }

    def set_qr_image(self, user_reward_id: int, b64_png: str):
        with self._conn() as con:
            con.execute(
                "UPDATE user_rewards SET qr_image_b64=? WHERE id=?",
                (b64_png, user_reward_id),
            )

    def add_reward(
        self,
        title: str,
        partner_name: str,
        partner_type: str,
        trigger_type: str,
        trigger_value: str,
        discount_pct: int = 10,
        description: str = "",
        expires_at: Optional[str] = None,
    ) -> int:
        with self._conn() as con:
            cur = con.execute(
                """INSERT INTO rewards
                   (title, description, partner_name, partner_type,
                    discount_pct, trigger_type, trigger_value, expires_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (title, description, partner_name, partner_type,
                 discount_pct, trigger_type, trigger_value, expires_at),
            )
            return cur.lastrowid

    def list_rewards(self) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM rewards WHERE is_active=1"
            ).fetchall()
            return [dict(r) for r in rows]
    def _unlock_rewards(
        self,
        con: sqlite3.Connection,
        user_id: int,
        rarity_tier: str,
        total_catches: int,
    ) -> list[dict]:
        """
        Called inside record_catch() transaction.
        Returns list of newly unlocked reward dicts (with token).
        """
        TIER_RANK = {"common": 0, "uncommon": 1, "rare": 2, "legendary": 3}

        active_rewards = con.execute(
            "SELECT * FROM rewards WHERE is_active=1"
        ).fetchall()

        already = {
            r["reward_id"]
            for r in con.execute(
                "SELECT reward_id FROM user_rewards WHERE user_id=?", (user_id,)
            ).fetchall()
        }

        newly_unlocked = []
        for reward in active_rewards:
            if reward["id"] in already:
                continue

            earned = False
            if reward["trigger_type"] == "milestone":
                earned = total_catches >= int(reward["trigger_value"])
            elif reward["trigger_type"] == "rarity":
                required = reward["trigger_value"].lower()
                earned = TIER_RANK.get(rarity_tier, 0) >= TIER_RANK.get(required, 99)

            if earned:
                token = self._make_token(user_id, reward["id"])
                con.execute(
                    """INSERT OR IGNORE INTO user_rewards (user_id, reward_id, token)
                       VALUES (?, ?, ?)""",
                    (user_id, reward["id"], token),
                )
                newly_unlocked.append({
                    "reward_id":    reward["id"],
                    "title":        reward["title"],
                    "partner_name": reward["partner_name"],
                    "discount_pct": reward["discount_pct"],
                    "token":        token,
                })

        return newly_unlocked

    @staticmethod
    def _make_token(user_id: int, reward_id: int) -> str:
        raw = f"{user_id}-{reward_id}-{time.time()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _seed_rewards(self):
        """Demo partner rewards."""
        with self._conn() as con:
            if con.execute("SELECT COUNT(*) FROM rewards").fetchone()[0] > 0:
                return
            demo = [
                ("10% off at Dockside Grill",      "Dockside Grill",        "restaurant",  "milestone", "5",         10),
                ("Free drink at Coral Cafe",        "Coral Cafe",            "restaurant",  "milestone", "10",        0),
                ("15% off Harbor Kayak Tours",      "Harbor Kayak Tours",    "attraction",  "milestone", "25",        15),
                ("Free entry: Ocean Discovery Ctr", "Ocean Discovery Center","attraction",  "rarity",    "rare",      100),
                ("20% off Sunset Seafood",          "Sunset Seafood",        "restaurant",  "rarity",    "legendary", 20),
            ]
            con.executemany(
                """INSERT INTO rewards
                   (title, partner_name, partner_type, trigger_type, trigger_value, discount_pct)
                   VALUES (?,?,?,?,?,?)""",
                demo,
            )
