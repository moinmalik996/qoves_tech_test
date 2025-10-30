"""
Database setup and migration utilities.
Creates views, functions, and indexes after table creation.
"""

from sqlalchemy import text
from database import get_db_session
from rich_logging import get_rich_logger

# Configure logger
db_logger = get_rich_logger("database_setup", {"component": "postgresql"})

def create_database_views_and_functions():
    """
    Create database views and functions after tables exist.
    This is called after SQLAlchemy creates the tables.
    """
    db = get_db_session()
    try:
        db_logger.info("[database]🔧 Creating database views and functions...[/]")
        
        # Create cache performance view
        cache_performance_view = """
        CREATE OR REPLACE VIEW cache_performance AS
        SELECT 
            DATE(submitted_at) as date,
            COUNT(*) as total_requests,
            COUNT(CASE WHEN cache_hits > 0 THEN 1 END) as cache_hits,
            ROUND(
                (COUNT(CASE WHEN cache_hits > 0 THEN 1 END) * 100.0 / COUNT(*))::numeric, 
                2
            ) as hit_ratio_percent,
            AVG(processing_time_ms) as avg_processing_time_ms,
            MIN(processing_time_ms) as min_processing_time_ms,
            MAX(processing_time_ms) as max_processing_time_ms
        FROM task_results 
        WHERE status = 'SUCCESS'
        GROUP BY DATE(submitted_at)
        ORDER BY date DESC;
        """
        
        db.execute(text(cache_performance_view))
        db_logger.debug("[database]✅ Cache performance view created[/]")
        
        # Create cleanup function
        cleanup_function = """
        CREATE OR REPLACE FUNCTION cleanup_old_cache_entries()
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            -- Delete entries older than 30 days with no cache hits
            DELETE FROM task_results 
            WHERE submitted_at < NOW() - INTERVAL '30 days'
            AND cache_hits = 0
            AND status = 'SUCCESS';
            
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            
            -- Also delete failed tasks older than 7 days
            DELETE FROM task_results 
            WHERE submitted_at < NOW() - INTERVAL '7 days'
            AND status = 'FAILURE';
            
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        db.execute(text(cleanup_function))
        db_logger.debug("[database]✅ Cleanup function created[/]")
        
        # Create additional performance indexes if they don't exist
        additional_indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_task_results_performance ON task_results (status, submitted_at, processing_time_ms);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_task_results_cache_performance ON task_results (cache_hits, last_accessed) WHERE cache_hits > 0;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_metrics_performance ON processing_metrics (recorded_at, metric_name, component);"
        ]
        
        for index_sql in additional_indexes:
            try:
                db.execute(text(index_sql))
                db_logger.debug(f"[database]📊 Index created: {index_sql.split()[5]}[/]")
            except Exception as e:
                # Index might already exist, that's ok
                db_logger.debug(f"[warning]⚠️ Index creation skipped: {str(e)[:50]}...[/]")
        
        db.commit()
        db_logger.info("[success]✅ Database views and functions created successfully[/]")
        
    except Exception as e:
        db.rollback()
        db_logger.error(f"[error]❌ Failed to create database views/functions: {str(e)}[/]")
        raise
    finally:
        db.close()

def get_database_stats():
    """Get basic database statistics for monitoring."""
    db = get_db_session()
    try:
        # Check if tables exist first
        table_check = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'task_results'
        );
        """
        
        result = db.execute(text(table_check)).scalar()
        if not result:
            return {"status": "tables_not_created", "message": "Database tables not yet created"}
        
        # Get basic statistics
        stats_query = """
        SELECT 
            (SELECT COUNT(*) FROM task_results) as total_tasks,
            (SELECT COUNT(*) FROM task_results WHERE status = 'SUCCESS') as successful_tasks,
            (SELECT COUNT(*) FROM task_results WHERE cache_hits > 0) as cached_results,
            (SELECT COUNT(*) FROM processing_metrics) as total_metrics,
            (SELECT pg_size_pretty(pg_database_size(current_database()))) as database_size;
        """
        
        result = db.execute(text(stats_query)).fetchone()
        
        return {
            "total_tasks": result[0],
            "successful_tasks": result[1], 
            "cached_results": result[2],
            "total_metrics": result[3],
            "database_size": result[4],
            "status": "healthy"
        }
        
    except Exception as e:
        db_logger.error(f"[error]📊 Database stats error: {str(e)}[/]")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()

def test_database_connection():
    """Test database connection and basic functionality."""
    try:
        db_logger.info("[database]🔍 Testing database connection...[/]")
        
        db = get_db_session()
        try:
            # Simple connection test
            result = db.execute(text("SELECT 1 as test")).scalar()
            if result == 1:
                db_logger.info("[success]✅ Database connection successful[/]")
                return True
            else:
                db_logger.error("[error]❌ Database connection test failed[/]")
                return False
        finally:
            db.close()
            
    except Exception as e:
        db_logger.error(f"[error]💥 Database connection failed: {str(e)}[/]")
        return False

if __name__ == "__main__":
    # Test connection and create views when run directly
    if test_database_connection():
        create_database_views_and_functions()
        print("Database setup completed successfully!")
    else:
        print("Database connection failed!")