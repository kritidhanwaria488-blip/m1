"""
Phase 4.1: Structured Storage Module

Handles persistence of normalized HTML and structured fund metrics.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from runtime.phase_4_normalize.parser import FundMetrics

logger = logging.getLogger(__name__)


class StructuredStorage:
    """
    Storage manager for normalized content and structured data.
    
    Organizes files by run_id:
    data/structured/{run_id}/
        ├── normalized/{scheme_id}.html       (cleaned HTML)
        ├── metrics/{scheme_id}.json          (structured metrics)
        └── manifest.json                      (run metadata)
    """
    
    def __init__(self, base_dir: str = "data/structured"):
        self.base_dir = Path(base_dir)
        logger.info(f"Initialized StructuredStorage at {self.base_dir}")
    
    def _ensure_dir(self, path: Path) -> None:
        """Create directory if it doesn't exist."""
        path.mkdir(parents=True, exist_ok=True)
    
    def save_normalized_html(
        self, 
        scheme_id: str, 
        html_content: str, 
        run_id: str
    ) -> Optional[Path]:
        """
        Save cleaned/normalized HTML.
        
        Args:
            scheme_id: Scheme identifier
            html_content: Cleaned HTML string
            run_id: Run identifier
            
        Returns:
            Path to saved file or None
        """
        normalized_dir = self.base_dir / run_id / "normalized"
        self._ensure_dir(normalized_dir)
        
        file_path = normalized_dir / f"{scheme_id}.html"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.debug(f"Saved normalized HTML: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save normalized HTML for {scheme_id}: {e}")
            return None
    
    def save_metrics(
        self, 
        metrics: FundMetrics, 
        run_id: str
    ) -> Optional[Path]:
        """
        Save structured fund metrics as JSON.
        
        Args:
            metrics: FundMetrics dataclass
            run_id: Run identifier
            
        Returns:
            Path to saved file or None
        """
        metrics_dir = self.base_dir / run_id / "metrics"
        self._ensure_dir(metrics_dir)
        
        file_path = metrics_dir / f"{metrics.scheme_id}.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(metrics.to_json())
            
            logger.debug(f"Saved metrics: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save metrics for {metrics.scheme_id}: {e}")
            return None
    
    def save_all_metrics(
        self, 
        metrics_list: list[FundMetrics], 
        run_id: str
    ) -> Dict[str, Any]:
        """
        Save multiple metrics and generate combined manifest.
        
        Args:
            metrics_list: List of FundMetrics objects
            run_id: Run identifier
            
        Returns:
            Manifest dictionary
        """
        saved_files = []
        
        for metrics in metrics_list:
            path = self.save_metrics(metrics, run_id)
            if path:
                saved_files.append({
                    'scheme_id': metrics.scheme_id,
                    'file': str(path.relative_to(self.base_dir)),
                    'nav': metrics.nav,
                    'expense_ratio': metrics.expense_ratio,
                    'minimum_sip': metrics.minimum_sip,
                    'fund_size': metrics.fund_size,
                    'rating': metrics.rating_value
                })
        
        # Create combined metrics file
        combined = [m.to_dict() for m in metrics_list]
        combined_path = self.base_dir / run_id / "all_metrics.json"
        
        try:
            with open(combined_path, 'w', encoding='utf-8') as f:
                json.dump(combined, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved combined metrics: {combined_path}")
        except Exception as e:
            logger.error(f"Failed to save combined metrics: {e}")
        
        # Generate manifest
        manifest = {
            'run_id': run_id,
            'phase': '4.1',
            'timestamp': metrics_list[0].extracted_at if metrics_list else '',
            'base_dir': str(self.base_dir),
            'total_schemes': len(metrics_list),
            'files': saved_files,
            'combined_file': str(combined_path.relative_to(self.base_dir)) if combined_path.exists() else None
        }
        
        # Save manifest
        manifest_path = self.base_dir / run_id / "manifest.json"
        try:
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved manifest: {manifest_path}")
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
        
        return manifest
    
    def load_metrics(self, run_id: str, scheme_id: str) -> Optional[FundMetrics]:
        """Load metrics for a specific scheme."""
        file_path = self.base_dir / run_id / "metrics" / f"{scheme_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return FundMetrics(**data)
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
            return None
    
    def load_all_metrics(self, run_id: str) -> list[FundMetrics]:
        """Load all metrics for a run."""
        metrics_dir = self.base_dir / run_id / "metrics"
        
        if not metrics_dir.exists():
            return []
        
        metrics_list = []
        for file_path in metrics_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                metrics_list.append(FundMetrics(**data))
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")
        
        return metrics_list
    
    def load_manifest(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load manifest for a run."""
        manifest_path = self.base_dir / run_id / "manifest.json"
        
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            return None
