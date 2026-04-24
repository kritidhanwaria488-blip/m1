"""
Phase 4.2: Chunking & Embedding CLI

Splits normalized HTML into semantic chunks and generates BGE embeddings.

Usage:
    python -m runtime.phase_4_chunk_embed --run-id <RUN_ID>

Examples:
    python -m runtime.phase_4_chunk_embed --run-id 20240115-091500
    python -m runtime.phase_4_chunk_embed --run-id 20240115-091500 --chunk-size 300 --verbose
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from runtime.phase_4_chunk_embed.chunker import HTMLChunker
from runtime.phase_4_chunk_embed.embedder import BGEEmbedder
from runtime.phase_4_chunk_embed.storage import ChunkedStorage
from runtime.phase_4_normalize.storage import StructuredStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 4.2: Chunk HTML and generate embeddings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m runtime.phase_4_chunk_embed --run-id 20240115-091500
  python -m runtime.phase_4_chunk_embed --run-id 20240115-091500 --chunk-size 300 --verbose
        """
    )
    
    parser.add_argument('--run-id', required=True, help='Run identifier from Phase 4.1')
    parser.add_argument('--input-dir', default='data/structured', help='Input normalized directory')
    parser.add_argument('--output-dir', default='data/structured', help='Output chunked directory')
    parser.add_argument('--model', default='BAAI/bge-small-en-v1.5', help='Embedding model')
    parser.add_argument('--chunk-size', type=int, default=375, help='Target chunk size (tokens)')
    parser.add_argument('--overlap', type=float, default=0.12, help='Overlap percentage (0-1)')
    parser.add_argument('--batch-size', type=int, default=32, help='Embedding batch size')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=" * 60)
    logger.info("Phase 4.2: Chunking & Embedding")
    logger.info("=" * 60)
    logger.info(f"Run ID: {args.run_id}")
    logger.info(f"Model: {args.model}")
    logger.info(f"Chunk size: {args.chunk_size} tokens")
    logger.info(f"Overlap: {args.overlap}")
    logger.info(f"Batch size: {args.batch_size}")
    
    # Initialize components
    structured_storage = StructuredStorage(base_dir=args.input_dir)
    chunked_storage = ChunkedStorage(base_dir=args.output_dir)
    
    chunker = HTMLChunker(
        target_tokens=args.chunk_size,
        overlap_percent=args.overlap
    )
    
    embedder = BGEEmbedder(
        model_name=args.model,
        batch_size=args.batch_size
    )
    
    # Load normalized content
    logger.info("Loading normalized HTML...")
    normalized_dir = Path(args.input_dir) / args.run_id / "normalized"
    
    if not normalized_dir.exists():
        logger.error(f"Normalized directory not found: {normalized_dir}")
        sys.exit(1)
    
    # Load metrics for metadata
    metrics_list = structured_storage.load_all_metrics(args.run_id)
    metrics_by_scheme = {m.scheme_id: m for m in metrics_list}
    
    logger.info(f"Found {len(metrics_list)} schemes with metrics")
    
    # Process each scheme
    chunks_by_scheme = {}
    
    for html_file in normalized_dir.glob("*.html"):
        scheme_id = html_file.stem
        
        logger.info(f"Processing {scheme_id}...")
        
        # Load normalized HTML
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            logger.error(f"Failed to load {html_file}: {e}")
            continue
        
        # Get metadata
        metrics = metrics_by_scheme.get(scheme_id)
        if not metrics:
            logger.warning(f"No metrics found for {scheme_id}, using defaults")
            metadata = {
                'scheme_id': scheme_id,
                'scheme_name': scheme_id,
                'amc': 'hdfc_mutual_fund',
                'source_url': '',
                'source_type': 'groww_scheme_page',
                'fetched_at': '',
                'content_hash': ''
            }
        else:
            metadata = {
                'scheme_id': metrics.scheme_id,
                'scheme_name': metrics.scheme_name,
                'amc': metrics.amc,
                'source_url': metrics.source_url,
                'source_type': metrics.source_type,
                'fetched_at': metrics.fetched_at,
                'content_hash': metrics.content_hash
            }
        
        # Chunk the HTML
        try:
            chunks = chunker.chunk_html(html_content, metadata)
            logger.info(f"Created {len(chunks)} chunks for {scheme_id}")
            
            if not chunks:
                logger.warning(f"No chunks created for {scheme_id}")
                continue
            
            chunks_by_scheme[scheme_id] = chunks
            
        except Exception as e:
            logger.error(f"Failed to chunk {scheme_id}: {e}")
            continue
    
    # Generate embeddings
    logger.info("=" * 60)
    logger.info("Generating embeddings...")
    logger.info("=" * 60)
    
    total_chunks = sum(len(chunks) for chunks in chunks_by_scheme.values())
    logger.info(f"Total chunks to embed: {total_chunks}")
    
    for scheme_id, chunks in chunks_by_scheme.items():
        try:
            chunks_with_embeddings = embedder.embed_chunks(chunks)
            chunks_by_scheme[scheme_id] = chunks_with_embeddings
            logger.info(f"Embedded {len(chunks)} chunks for {scheme_id}")
        except Exception as e:
            logger.error(f"Failed to embed chunks for {scheme_id}: {e}")
    
    # Save all chunks
    logger.info("=" * 60)
    logger.info("Saving chunked output...")
    logger.info("=" * 60)
    
    model_info = embedder.get_model_info()
    manifest = chunked_storage.save_all_chunks(chunks_by_scheme, args.run_id, model_info)
    
    # Summary
    logger.info("=" * 60)
    logger.info("Phase 4.2 Complete")
    logger.info("=" * 60)
    logger.info(f"Schemes processed: {manifest['total_schemes']}")
    logger.info(f"Total chunks created: {manifest['total_chunks']}")
    logger.info(f"Embedding model: {model_info['model_name']}")
    logger.info(f"Dimensions: {model_info['dimensions']}")
    logger.info(f"Output: {Path(args.output_dir) / args.run_id / 'chunked'}")
    
    # Show per-scheme breakdown
    for file_info in manifest['files']:
        logger.info(
            f"  {file_info['scheme_id']}: "
            f"{file_info['chunk_count']} chunks "
            f"(~{file_info['avg_token_count']} tokens avg)"
        )
    
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
