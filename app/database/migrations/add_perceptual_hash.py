"""
Database migration: Add perceptual_hash column to task_results table.
This enables perceptual caching for finding similar images.

Run this script to update existing databases:
    python app/database/migrations/add_perceptual_hash.py
"""

from sqlalchemy import text
from app.database.connection import SessionLocal
from app.monitoring.logging import get_logger

logger = get_logger("migration")


def migrate_add_perceptual_hash():
    """Add perceptual_hash column and index to task_results table."""
    db = SessionLocal()
    
    try:
        logger.info("🔄 Starting migration: Adding perceptual_hash column...")
        
        # Check if column already exists
        check_column = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='task_results' AND column_name='perceptual_hash'
        """)
        
        result = db.execute(check_column).fetchone()
        
        if result:
            logger.info("✅ Column 'perceptual_hash' already exists, skipping...")
            return True
        
        # Add perceptual_hash column
        logger.info("📝 Adding perceptual_hash column...")
        add_column = text("""
            ALTER TABLE task_results 
            ADD COLUMN perceptual_hash VARCHAR(64)
        """)
        db.execute(add_column)
        db.commit()
        logger.info("✅ Column added successfully")
        
        # Add index for perceptual_hash
        logger.info("📝 Creating index on perceptual_hash...")
        add_index = text("""
            CREATE INDEX IF NOT EXISTS idx_task_results_perceptual_hash 
            ON task_results(perceptual_hash)
        """)
        db.execute(add_index)
        db.commit()
        logger.info("✅ Index created successfully")
        
        # Add composite index for perceptual lookup
        logger.info("📝 Creating composite index for perceptual lookup...")
        add_composite_index = text("""
            CREATE INDEX IF NOT EXISTS idx_task_results_perceptual_lookup 
            ON task_results(perceptual_hash, status)
        """)
        db.execute(add_composite_index)
        db.commit()
        logger.info("✅ Composite index created successfully")
        
        logger.info("🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


def rollback_perceptual_hash():
    """Rollback: Remove perceptual_hash column and indexes."""
    db = SessionLocal()
    
    try:
        logger.info("🔄 Rolling back migration...")
        
        # Drop indexes
        logger.info("📝 Dropping indexes...")
        drop_indexes = text("""
            DROP INDEX IF EXISTS idx_task_results_perceptual_lookup;
            DROP INDEX IF EXISTS idx_task_results_perceptual_hash;
        """)
        db.execute(drop_indexes)
        db.commit()
        
        # Drop column
        logger.info("📝 Dropping perceptual_hash column...")
        drop_column = text("""
            ALTER TABLE task_results 
            DROP COLUMN IF EXISTS perceptual_hash
        """)
        db.execute(drop_column)
        db.commit()
        
        logger.info("✅ Rollback completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Rollback failed: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("Rolling back perceptual_hash migration...")
        success = rollback_perceptual_hash()
    else:
        print("Applying perceptual_hash migration...")
        success = migrate_add_perceptual_hash()
    
    sys.exit(0 if success else 1)
