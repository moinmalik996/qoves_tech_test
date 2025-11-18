"""
PostgreSQL cache service for facial processing results.
Handles caching, retrieval, and cache management operations.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import desc, func, and_, or_

from app.database.connection import SessionLocal
from app.database.models import TaskResult, ProcessingMetrics
from app.database.utils import generate_cache_key
from app.monitoring.logging import get_logger
from app.monitoring.metrics import errors_total

# Configure logger
cache_logger = get_logger()

class CacheService:
    """
    PostgreSQL-based cache service for facial processing results.
    Provides intelligent caching with TTL, metrics, and performance tracking.
    """
    
    def __init__(self, default_ttl_hours: int = 24):
        self.default_ttl_hours = default_ttl_hours
    
    def get_cached_result(self, image_data: str, landmarks: list, segmentation_map: str,
                         show_landmarks: bool = False, region_opacity: float = 0.7) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached result if available and not expired.
        
        Returns:
            Cached result dict or None if not found/expired
        """
        db = SessionLocal()
        try:
            # Generate cache key
            cache_key = generate_cache_key(
                image_data, landmarks, segmentation_map, show_landmarks, region_opacity
            )
            
            cache_logger.debug(f"[cache]🔍 Looking for cached result: {cache_key[:12]}...[/]")
            
            # Query for cached result
            cached_task = db.query(TaskResult).filter(
                and_(
                    TaskResult.input_hash == cache_key,
                    TaskResult.status == 'SUCCESS',
                    or_(
                        TaskResult.ttl_expires_at.is_(None),
                        TaskResult.ttl_expires_at > datetime.utcnow()
                    )
                )
            ).first()
            
            if cached_task:
                # Update cache hit statistics
                cached_task.cache_hits += 1
                cached_task.last_accessed = datetime.utcnow()
                db.commit()
                
                cache_logger.info(f"[success]💾 Cache HIT for key {cache_key[:12]}... (hits: {cached_task.cache_hits})[/]")
                
                # Record cache hit metric
                self._record_cache_metric("cache_hit", cache_key)
                
                return {
                    "task_id": cached_task.task_id,
                    "status": "SUCCESS",
                    "result": cached_task.result_data,
                    "svg": cached_task.svg_data,
                    "mask_contours": cached_task.mask_contours,
                    "processing_time_ms": cached_task.processing_time_ms,
                    "regions_detected": cached_task.regions_detected,
                    "completed_at": cached_task.completed_at.isoformat(),
                    "cache_hit": True,
                    "cache_hits": cached_task.cache_hits
                }
            else:
                cache_logger.debug(f"[warning]❌ Cache MISS for key {cache_key[:12]}...[/]")
                self._record_cache_metric("cache_miss", cache_key)
                return None
                
        except Exception as e:
            cache_logger.error(f"[error]💥 Cache lookup error: {str(e)}[/]")
            errors_total.labels(error_type=type(e).__name__, component="cache").inc()
            return None
        finally:
            db.close()
    
    def store_task_result(self, task_id: str, image_data: str, landmarks: list, 
                         segmentation_map: str, result_data: Dict[str, Any],
                         show_landmarks: bool = False, region_opacity: float = 0.7,
                         processing_time_ms: float = 0) -> bool:
        """
        Store task result in cache.
        
        Returns:
            True if stored successfully, False otherwise
        """
        db = SessionLocal()
        try:
            # Generate cache key
            cache_key = generate_cache_key(
                image_data, landmarks, segmentation_map, show_landmarks, region_opacity
            )
            
            cache_logger.debug(f"[cache]💾 Storing result for key {cache_key[:12]}...[/]")
            
            # Check if task already exists (update scenario)
            existing_task = db.query(TaskResult).filter(TaskResult.task_id == task_id).first()
            
            if existing_task:
                # Update existing record
                existing_task.status = 'SUCCESS'
                existing_task.completed_at = datetime.utcnow()
                existing_task.result_data = result_data
                existing_task.svg_data = result_data.get('svg')
                existing_task.mask_contours = result_data.get('mask_contours')
                existing_task.processing_time_ms = processing_time_ms
                existing_task.regions_detected = result_data.get('regions_detected', 0)
                existing_task.ttl_expires_at = datetime.utcnow() + timedelta(hours=self.default_ttl_hours)
                
                cache_logger.info(f"[cache]📝 Updated existing cache entry for task {task_id[:8]}[/]")
            else:
                # Create new cache entry
                cache_entry = TaskResult(
                    task_id=task_id,
                    input_hash=cache_key,
                    status='SUCCESS',
                    task_type='facial_processing',
                    submitted_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    result_data=result_data,
                    svg_data=result_data.get('svg'),
                    mask_contours=result_data.get('mask_contours'),
                    show_landmarks=str(show_landmarks),
                    region_opacity=region_opacity,
                    processing_time_ms=processing_time_ms,
                    regions_detected=result_data.get('regions_detected', 0),
                    landmarks_count=len(landmarks),
                    ttl_expires_at=datetime.utcnow() + timedelta(hours=self.default_ttl_hours)
                )
                
                # Extract image dimensions if available
                if 'image_shape' in result_data:
                    cache_entry.image_width = result_data['image_shape'].get('width')
                    cache_entry.image_height = result_data['image_shape'].get('height')
                
                db.add(cache_entry)
                cache_logger.info(f"[success]💾 Stored new cache entry for task {task_id[:8]}[/]")
            
            db.commit()
            self._record_cache_metric("cache_store", cache_key)
            return True
            
        except Exception as e:
            db.rollback()
            cache_logger.error(f"[error]💥 Cache store error: {str(e)}[/]")
            errors_total.labels(error_type=type(e).__name__, component="cache").inc()
            return False
        finally:
            db.close()
    
    def store_task_error(self, task_id: str, error_message: str, error_type: str,
                        image_data: str, landmarks: list, segmentation_map: str,
                        show_landmarks: bool = False, region_opacity: float = 0.7) -> bool:
        """Store task error information."""
        db = SessionLocal()
        try:
            cache_key = generate_cache_key(
                image_data, landmarks, segmentation_map, show_landmarks, region_opacity
            )
            
            # Check if task exists
            existing_task = db.query(TaskResult).filter(TaskResult.task_id == task_id).first()
            
            if existing_task:
                existing_task.status = 'FAILURE'
                existing_task.error_message = error_message
                existing_task.error_type = error_type
                existing_task.completed_at = datetime.utcnow()
            else:
                error_entry = TaskResult(
                    task_id=task_id,
                    input_hash=cache_key,
                    status='FAILURE',
                    task_type='facial_processing',
                    submitted_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    error_message=error_message,
                    error_type=error_type,
                    show_landmarks=str(show_landmarks),
                    region_opacity=region_opacity,
                    landmarks_count=len(landmarks)
                )
                db.add(error_entry)
            
            db.commit()
            cache_logger.warning(f"[warning]📝 Stored error for task {task_id[:8]}: {error_type}[/]")
            return True
            
        except Exception as e:
            db.rollback()
            cache_logger.error(f"[error]💥 Error store failed: {str(e)}[/]")
            return False
        finally:
            db.close()
    
    def get_cache_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get cache performance statistics."""
        db = SessionLocal()
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Total requests in period
            total_requests = db.query(TaskResult).filter(
                TaskResult.submitted_at >= start_date
            ).count()
            
            # Cache hits (requests served from cache)
            cache_hits = db.query(TaskResult).filter(
                and_(
                    TaskResult.submitted_at >= start_date,
                    TaskResult.cache_hits > 0
                )
            ).count()
            
            # Successful completions
            successful_tasks = db.query(TaskResult).filter(
                and_(
                    TaskResult.submitted_at >= start_date,
                    TaskResult.status == 'SUCCESS'
                )
            ).count()
            
            # Average processing time
            avg_processing_time = db.query(func.avg(TaskResult.processing_time_ms)).filter(
                and_(
                    TaskResult.submitted_at >= start_date,
                    TaskResult.status == 'SUCCESS',
                    TaskResult.processing_time_ms.isnot(None)
                )
            ).scalar() or 0
            
            # Cache hit ratio
            cache_hit_ratio = (cache_hits / total_requests * 100) if total_requests > 0 else 0
            
            # Total cached entries
            total_cached = db.query(TaskResult).filter(
                TaskResult.status == 'SUCCESS'
            ).count()
            
            return {
                "period_days": days,
                "total_requests": total_requests,
                "cache_hits": cache_hits,
                "cache_hit_ratio": round(cache_hit_ratio, 2),
                "successful_tasks": successful_tasks,
                "avg_processing_time_ms": round(float(avg_processing_time), 2),
                "total_cached_entries": total_cached,
                "cache_efficiency": "excellent" if cache_hit_ratio > 70 else "good" if cache_hit_ratio > 40 else "needs_improvement"
            }
            
        except Exception as e:
            cache_logger.error(f"[error]📊 Stats calculation error: {str(e)}[/]")
            return {"error": str(e)}
        finally:
            db.close()
    
    def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries."""
        db = SessionLocal()
        try:
            # Delete expired entries
            deleted_count = db.query(TaskResult).filter(
                and_(
                    TaskResult.ttl_expires_at.isnot(None),
                    TaskResult.ttl_expires_at < datetime.utcnow()
                )
            ).delete()
            
            db.commit()
            
            if deleted_count > 0:
                cache_logger.info(f"[cache]🧹 Cleaned up {deleted_count} expired cache entries[/]")
            
            return deleted_count
            
        except Exception as e:
            db.rollback()
            cache_logger.error(f"[error]🧹 Cache cleanup error: {str(e)}[/]")
            return 0
        finally:
            db.close()
    
    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent task results for monitoring."""
        db = SessionLocal()
        try:
            recent_tasks = db.query(TaskResult).order_by(
                desc(TaskResult.submitted_at)
            ).limit(limit).all()
            
            return [{
                "task_id": task.task_id[:8],
                "status": task.status,
                "submitted_at": task.submitted_at.isoformat(),
                "processing_time_ms": task.processing_time_ms,
                "regions_detected": task.regions_detected,
                "cache_hits": task.cache_hits,
                "error_type": task.error_type
            } for task in recent_tasks]
            
        except Exception as e:
            cache_logger.error(f"[error]📋 Recent tasks query error: {str(e)}[/]")
            return []
        finally:
            db.close()
    
    def _record_cache_metric(self, metric_type: str, cache_key: str):
        """Record cache-related metrics."""
        db = SessionLocal()
        try:
            metric = ProcessingMetrics(
                task_id="cache_operation",
                metric_name=metric_type,
                metric_value=1,
                metric_unit="count",
                component="cache",
                operation=metric_type,
                additional_data={"cache_key": cache_key[:12]}
            )
            db.add(metric)
            db.commit()
        except Exception as e:
            cache_logger.debug(f"[warning]📊 Metric recording failed: {str(e)}[/]")
        finally:
            db.close()
    
    def get_perceptual_cached_result(
        self, 
        image_base64: str,
        landmarks: list,
        show_labels: bool = True,
        region_opacity: float = 0.65,
        stroke_width: int = 0,
        similarity_threshold: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached result using perceptual hashing for similar images.
        Falls back to exact matching if no similar images found.
        
        Args:
            image_base64: Base64 encoded image
            landmarks: List of landmarks
            show_labels: Whether labels are shown
            region_opacity: Opacity value
            stroke_width: Stroke width
            similarity_threshold: Maximum Hamming distance for similarity (default 10)
            
        Returns:
            Cached result dict or None if not found
        """
        from app.utils.perceptual_hash import (
            generate_perceptual_cache_key,
            hamming_distance
        )
        
        db = SessionLocal()
        try:
            # Generate both perceptual and exact keys
            perceptual_hash, exact_key = generate_perceptual_cache_key(
                image_base64, landmarks, show_labels, region_opacity, stroke_width
            )
            
            cache_logger.debug(f"[cache]🔍 Perceptual lookup: {perceptual_hash[:12]}...[/]")
            
            # First try exact match
            exact_match = db.query(TaskResult).filter(
                and_(
                    TaskResult.input_hash == exact_key,
                    TaskResult.status == 'SUCCESS',
                    or_(
                        TaskResult.ttl_expires_at.is_(None),
                        TaskResult.ttl_expires_at > datetime.utcnow()
                    )
                )
            ).first()
            
            if exact_match:
                exact_match.cache_hits += 1
                exact_match.last_accessed = datetime.utcnow()
                db.commit()
                cache_logger.info("[success]💾 EXACT Cache HIT[/]")
                self._record_cache_metric("exact_cache_hit", exact_key)
                
                return {
                    "task_id": exact_match.task_id,
                    "status": "SUCCESS",
                    "result": exact_match.result_data,
                    "processing_time_ms": exact_match.processing_time_ms,
                    "cache_hit": True,
                    "cache_type": "exact",
                    "cache_hits": exact_match.cache_hits
                }
            
            # Try perceptual matching - get candidates with similar hashes
            candidates = db.query(TaskResult).filter(
                and_(
                    TaskResult.perceptual_hash.isnot(None),
                    TaskResult.status == 'SUCCESS',
                    or_(
                        TaskResult.ttl_expires_at.is_(None),
                        TaskResult.ttl_expires_at > datetime.utcnow()
                    )
                )
            ).all()
            
            # Find best match within threshold
            best_match = None
            best_distance = similarity_threshold + 1
            
            for candidate in candidates:
                if candidate.perceptual_hash:
                    distance = hamming_distance(perceptual_hash, candidate.perceptual_hash)
                    if distance < best_distance:
                        best_distance = distance
                        best_match = candidate
            
            if best_match and best_distance <= similarity_threshold:
                best_match.cache_hits += 1
                best_match.last_accessed = datetime.utcnow()
                db.commit()
                
                cache_logger.info(
                    f"[success]🎯 PERCEPTUAL Cache HIT "
                    f"(distance: {best_distance}/{similarity_threshold})[/]"
                )
                self._record_cache_metric("perceptual_cache_hit", perceptual_hash)
                
                return {
                    "task_id": best_match.task_id,
                    "status": "SUCCESS",
                    "result": best_match.result_data,
                    "processing_time_ms": best_match.processing_time_ms,
                    "cache_hit": True,
                    "cache_type": "perceptual",
                    "similarity_distance": best_distance,
                    "cache_hits": best_match.cache_hits
                }
            
            cache_logger.debug("[warning]❌ No similar cached results found[/]")
            self._record_cache_metric("perceptual_cache_miss", perceptual_hash)
            return None
            
        except Exception as e:
            cache_logger.error(f"[error]💥 Perceptual cache lookup error: {str(e)}[/]")
            errors_total.labels(error_type=type(e).__name__, component="perceptual_cache").inc()
            return None
        finally:
            db.close()
    
    def store_task_result_with_phash(
        self,
        task_id: str,
        image_base64: str,
        landmarks: list,
        result_data: Dict[str, Any],
        show_labels: bool = True,
        region_opacity: float = 0.65,
        stroke_width: int = 0,
        processing_time_ms: float = 0
    ) -> bool:
        """
        Store task result with both exact and perceptual hashing.
        
        Returns:
            True if stored successfully
        """
        from app.utils.perceptual_hash import generate_perceptual_cache_key
        
        db = SessionLocal()
        try:
            # Generate both keys
            perceptual_hash, exact_key = generate_perceptual_cache_key(
                image_base64, landmarks, show_labels, region_opacity, stroke_width
            )
            
            # Calculate TTL
            ttl_expires_at = datetime.utcnow() + timedelta(hours=self.default_ttl_hours)
            
            # Check if already exists
            existing = db.query(TaskResult).filter_by(input_hash=exact_key).first()
            
            if existing:
                cache_logger.info("[cache]🔄 Updating existing cache entry[/]")
                existing.result_data = result_data
                existing.perceptual_hash = perceptual_hash
                existing.processing_time_ms = processing_time_ms
                existing.ttl_expires_at = ttl_expires_at
                existing.last_accessed = datetime.utcnow()
            else:
                cache_logger.info("[cache]💾 Creating new cache entry with pHash[/]")
                task_result = TaskResult(
                    task_id=task_id,
                    input_hash=exact_key,
                    perceptual_hash=perceptual_hash,
                    status='SUCCESS',
                    result_data=result_data,
                    processing_time_ms=processing_time_ms,
                    ttl_expires_at=ttl_expires_at,
                    show_landmarks=str(show_labels),
                    region_opacity=region_opacity
                )
                db.add(task_result)
            
            db.commit()
            cache_logger.info("[success]✅ Task result stored with perceptual hash[/]")
            return True
            
        except Exception as e:
            cache_logger.error(f"[error]💥 Failed to store result: {str(e)}[/]")
            db.rollback()
            return False
        finally:
            db.close()

# Global cache service instance
cache_service = CacheService()