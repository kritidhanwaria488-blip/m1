"""
Phase 4.0: Storage Module

Handles persistence of raw HTML and metadata.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from runtime.phase_4_scrape.fetcher import FetchResult

logger = logging.getLogger(__name__)


class RawStorage:
    """
    Storage manager for raw scraped HTML content.
    
    Organizes files by run_id for reproducibility:
    data/raw/{run_id}/{scheme_id}.html
    data/raw/{run_id}/manifest.json
    """
    
    def __init__(self, base_dir: str = "data/raw"):
        self.base_dir = Path(base_dir)
        logger.info(f"Initialized RawStorage at {self.base_dir}")
    
    def _ensure_dir(self, path: Path) -> None:
        """Create directory if it doesn't exist."""
        path.mkdir(parents=True, exist_ok=True)
    
    def save_result(self, result: FetchResult, run_id: str) -> Optional[Path]:
        """
        Save a single fetch result to disk.
        
        Args:
            result: FetchResult to save
            run_id: Run identifier for organization
            
        Returns:
            Path to saved file, or None if failed
        """
        if not result.success or not result.content:
            logger.warning(f"Skipping save for failed fetch: {result.url}")
            return None
        
        # Build path: data/raw/{run_id}/{scheme_id}.html
        run_dir = self.base_dir / run_id
        self._ensure_dir(run_dir)
        
        file_path = run_dir / f"{result.scheme_id}.html"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(result.content)
            
            logger.debug(f"Saved {result.scheme_id} to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save {result.scheme_id}: {e}")
            return None
    
    def save_all(self, results: List[FetchResult], run_id: str) -> dict:
        """
        Save multiple fetch results and generate manifest.
        
        Args:
            results: List of FetchResult objects
            run_id: Run identifier
            
        Returns:
            Manifest dictionary with metadata
        """
        run_dir = self.base_dir / run_id
        self._ensure_dir(run_dir)
        
        saved_files = []
        failed_schemes = []
        
        # Save each successful result
        for result in results:
            if result.success:
                path = self.save_result(result, run_id)
                if path:
                    saved_files.append({
                        'scheme_id': result.scheme_id,
                        'url': result.url,
                        'file': str(path.relative_to(self.base_dir)),
                        'content_hash': result.content_hash,
                        'size_bytes': len(result.content.encode('utf-8')),
                        'fetch_time_ms': result.fetch_time_ms
                    })
            else:
                failed_schemes.append({
                    'scheme_id': result.scheme_id,
                    'url': result.url,
                    'error': result.error,
                    'fetch_time_ms': result.fetch_time_ms
                })
        
        # Generate manifest
        manifest = {
            'run_id': run_id,
            'phase': '4.0',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'base_dir': str(self.base_dir),
            'total_urls': len(results),
            'successful': len(saved_files),
            'failed': len(failed_schemes),
            'files': saved_files,
            'failures': failed_schemes
        }
        
        # Save manifest
        manifest_path = run_dir / 'manifest.json'
        try:
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved manifest to {manifest_path}")
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
        
        return manifest
    
    def load_manifest(self, run_id: str) -> Optional[dict]:
        """Load manifest for a given run_id."""
        manifest_path = self.base_dir / run_id / 'manifest.json'
        
        if not manifest_path.exists():
            logger.warning(f"Manifest not found for run {run_id}")
            return None
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            return None
    
    def load_html(self, run_id: str, scheme_id: str) -> Optional[str]:
        """Load raw HTML content for a specific scheme."""
        file_path = self.base_dir / run_id / f"{scheme_id}.html"
        
        if not file_path.exists():
            logger.warning(f"HTML file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load HTML: {e}")
            return None
    
    def list_runs(self) -> List[str]:
        """List all run directories."""
        if not self.base_dir.exists():
            return []
        
        return [
            d.name for d in self.base_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]
