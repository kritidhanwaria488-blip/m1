"""
Phase 4.2: Chunk Storage Module

Handles persistence of chunked documents with embeddings.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from runtime.phase_4_chunk_embed.chunker import Chunk

logger = logging.getLogger(__name__)


class ChunkedStorage:
    """
    Storage manager for chunked documents with embeddings.
    
    Organizes files by run_id:
    data/structured/{run_id}/chunked/
        ├── {scheme_id}.jsonl          # One JSON per line (chunk)
        └── manifest.json              # Run metadata
    """
    
    def __init__(self, base_dir: str = "data/structured"):
        self.base_dir = Path(base_dir)
        logger.info(f"Initialized ChunkedStorage at {self.base_dir}")
    
    def _ensure_dir(self, path: Path) -> None:
        """Create directory if it doesn't exist."""
        path.mkdir(parents=True, exist_ok=True)
    
    def _compute_chunk_hash(self, chunk: Chunk) -> str:
        """Compute hash of chunk content for deduplication."""
        return hashlib.sha256(chunk.text.encode('utf-8')).hexdigest()[:16]
    
    def save_chunks(
        self,
        chunks: List[Chunk],
        scheme_id: str,
        run_id: str
    ) -> Optional[Path]:
        """
        Save chunks for a single scheme as JSONL.
        
        Args:
            chunks: List of Chunk objects (with embeddings)
            scheme_id: Scheme identifier
            run_id: Run identifier
            
        Returns:
            Path to saved file or None
        """
        chunked_dir = self.base_dir / run_id / "chunked"
        self._ensure_dir(chunked_dir)
        
        file_path = chunked_dir / f"{scheme_id}.jsonl"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    # Convert to dict and add content hash
                    chunk_dict = chunk.to_dict()
                    chunk_dict['content_hash'] = self._compute_chunk_hash(chunk)
                    
                    # Write as JSON line
                    f.write(json.dumps(chunk_dict, ensure_ascii=False) + '\n')
            
            logger.debug(f"Saved {len(chunks)} chunks to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save chunks for {scheme_id}: {e}")
            return None
    
    def save_all_chunks(
        self,
        chunks_by_scheme: Dict[str, List[Chunk]],
        run_id: str,
        model_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save all chunks grouped by scheme and generate manifest.
        
        Args:
            chunks_by_scheme: Dict mapping scheme_id to list of Chunks
            run_id: Run identifier
            model_info: Info about the embedding model used
            
        Returns:
            Manifest dictionary
        """
        saved_files = []
        total_chunks = 0
        
        for scheme_id, chunks in chunks_by_scheme.items():
            path = self.save_chunks(chunks, scheme_id, run_id)
            if path:
                saved_files.append({
                    'scheme_id': scheme_id,
                    'file': str(path.relative_to(self.base_dir)),
                    'chunk_count': len(chunks),
                    'avg_token_count': sum(c.token_count for c in chunks) // max(len(chunks), 1)
                })
                total_chunks += len(chunks)
        
        # Generate manifest
        manifest = {
            'run_id': run_id,
            'phase': '4.2',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'base_dir': str(self.base_dir),
            'embedding_model': model_info,
            'total_schemes': len(chunks_by_scheme),
            'total_chunks': total_chunks,
            'files': saved_files
        }
        
        # Save manifest
        manifest_path = self.base_dir / run_id / "chunked" / "manifest.json"
        self._ensure_dir(manifest_path.parent)
        
        try:
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved manifest: {manifest_path}")
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
        
        return manifest
    
    def load_chunks(self, run_id: str, scheme_id: str) -> List[Chunk]:
        """Load chunks for a specific scheme."""
        file_path = self.base_dir / run_id / "chunked" / f"{scheme_id}.jsonl"
        
        if not file_path.exists():
            logger.warning(f"Chunk file not found: {file_path}")
            return []
        
        chunks = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # Convert back to Chunk object
                        chunk = Chunk(**data)
                        chunks.append(chunk)
        except Exception as e:
            logger.error(f"Failed to load chunks: {e}")
        
        return chunks
    
    def load_all_chunks(self, run_id: str) -> List[Chunk]:
        """Load all chunks for a run."""
        chunked_dir = self.base_dir / run_id / "chunked"
        
        if not chunked_dir.exists():
            return []
        
        all_chunks = []
        for jsonl_file in chunked_dir.glob("*.jsonl"):
            scheme_id = jsonl_file.stem
            chunks = self.load_chunks(run_id, scheme_id)
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def load_manifest(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load manifest for a run."""
        manifest_path = self.base_dir / run_id / "chunked" / "manifest.json"
        
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            return None
