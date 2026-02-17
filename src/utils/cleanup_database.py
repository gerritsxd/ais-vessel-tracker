"""
Database Cleanup - Keep only last 30 days of data.

Removes:
  - vessel_positions older than 30 days
  - vessels_static with last_updated older than 30 days
  - vessel_wind_alignment for vessels no longer in vessels_static

Then runs VACUUM to reclaim disk space (critical for large DBs).

Run after git pull on VPS to enforce 30-day retention and shrink the database:
  cd /var/www/apihub && python src/utils/cleanup_database.py

Or: scripts/run_cleanup_30days.sh
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_NAME = "vessel_static_data.db"
DAYS_TO_KEEP = 30


def get_db_path(project_root: Path) -> Path:
    """Resolve database path (data/ first, then project root)."""
    for candidate in [project_root / "data" / DB_NAME, project_root / DB_NAME]:
        if candidate.exists():
            return candidate
    return project_root / "data" / DB_NAME


def cleanup_old_positions(conn: sqlite3.Connection) -> int:
    """Delete position records older than DAYS_TO_KEEP days."""
    cursor = conn.cursor()
    print(f"\n🧹 Cleaning vessel_positions (keeping last {DAYS_TO_KEEP} days)...")
    cursor.execute("SELECT COUNT(*) FROM vessel_positions")
    before = cursor.fetchone()[0]
    cursor.execute(
        "DELETE FROM vessel_positions WHERE datetime(timestamp) < datetime('now', '-' || ? || ' days')",
        (DAYS_TO_KEEP,),
    )
    deleted = cursor.rowcount
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM vessel_positions")
    after = cursor.fetchone()[0]
    print(f"   Before: {before:,} | Deleted: {deleted:,} | Remaining: {after:,}")
    return deleted


def cleanup_old_vessels_static(conn: sqlite3.Connection) -> int:
    """Delete vessels_static rows not updated in the last DAYS_TO_KEEP days."""
    cursor = conn.cursor()
    print(f"\n🧹 Cleaning vessels_static (keeping last {DAYS_TO_KEEP} days)...")
    cursor.execute("SELECT COUNT(*) FROM vessels_static")
    before = cursor.fetchone()[0]
    cursor.execute(
        "DELETE FROM vessels_static WHERE datetime(last_updated) < datetime('now', '-' || ? || ' days')",
        (DAYS_TO_KEEP,),
    )
    deleted = cursor.rowcount
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM vessels_static")
    after = cursor.fetchone()[0]
    print(f"   Before: {before:,} | Deleted: {deleted:,} | Remaining: {after:,}")
    return deleted


def cleanup_orphan_wind_alignment(conn: sqlite3.Connection) -> int:
    """Remove vessel_wind_alignment rows for MMSIs no longer in vessels_static."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vessel_wind_alignment'")
        if not cursor.fetchone():
            return 0
    except Exception:
        return 0
    print("\n🧹 Cleaning vessel_wind_alignment (removing orphans)...")
    cursor.execute("SELECT COUNT(*) FROM vessel_wind_alignment")
    before = cursor.fetchone()[0]
    cursor.execute("""
        DELETE FROM vessel_wind_alignment
        WHERE mmsi NOT IN (SELECT mmsi FROM vessels_static)
    """)
    deleted = cursor.rowcount
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM vessel_wind_alignment")
    after = cursor.fetchone()[0]
    print(f"   Before: {before:,} | Deleted: {deleted:,} | Remaining: {after:,}")
    return deleted


def checkpoint_and_vacuum(conn: sqlite3.Connection) -> None:
    """Checkpoint WAL and vacuum to reclaim disk space."""
    cursor = conn.cursor()
    print("\n🗜️  Checkpointing WAL and vacuuming to reclaim space...")
    try:
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except Exception:
        pass
    cursor.execute("VACUUM")
    print("   ✅ Database optimized and space reclaimed.")


def show_database_stats(conn: sqlite3.Connection) -> None:
    """Print current database statistics."""
    cursor = conn.cursor()
    print("\n📊 Database statistics:")
    print("   " + "=" * 50)
    for label, sql in [
        ("vessels_static", "SELECT COUNT(*) FROM vessels_static"),
        ("vessel_positions", "SELECT COUNT(*) FROM vessel_positions"),
    ]:
        try:
            cursor.execute(sql)
            print(f"   {label}: {cursor.fetchone()[0]:,}")
        except sqlite3.OperationalError:
            print(f"   {label}: N/A")
    try:
        cursor.execute("SELECT COUNT(*) FROM eu_mrv_emissions")
        print(f"   eu_mrv_emissions: {cursor.fetchone()[0]:,}")
    except sqlite3.OperationalError:
        print("   eu_mrv_emissions: N/A")
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM vessel_positions")
    min_ts, max_ts = cursor.fetchone()
    if min_ts:
        print(f"   Oldest position: {min_ts}")
    if max_ts:
        print(f"   Newest position: {max_ts}")
    print("   " + "=" * 50)


def main() -> None:
    project_root = Path(__file__).parent.parent.parent
    db_path = get_db_path(project_root)

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    size_before_mb = db_path.stat().st_size / (1024 * 1024)
    print("=" * 70)
    print(f"DATABASE CLEANUP (keep last {DAYS_TO_KEEP} days) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Size before: {size_before_mb:.1f} MB ({size_before_mb/1024:.2f} GB)")

    conn = sqlite3.connect(str(db_path), timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        show_database_stats(conn)
        total_deleted = 0
        total_deleted += cleanup_old_positions(conn)
        total_deleted += cleanup_old_vessels_static(conn)
        total_deleted += cleanup_orphan_wind_alignment(conn)

        if total_deleted > 0:
            checkpoint_and_vacuum(conn)
        else:
            print("\n⏭️  No rows deleted; skipping vacuum.")

        show_database_stats(conn)
        conn.close()

        size_after_mb = db_path.stat().st_size / (1024 * 1024)
        saved_mb = size_before_mb - size_after_mb
        print("\n✅ Cleanup complete")
        print(f"   Size after: {size_after_mb:.1f} MB ({size_after_mb/1024:.2f} GB)")
        if saved_mb > 0:
            print(f"   Space reclaimed: {saved_mb:.1f} MB ({saved_mb/1024:.2f} GB)")
        print("=" * 70 + "\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
