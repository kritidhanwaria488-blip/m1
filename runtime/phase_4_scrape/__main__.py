"""
Phase 4.0: Scrape Service CLI

Entry point for the scraping service.

Usage:
    python -m runtime.phase_4_scrape [OPTIONS]

Examples:
    # Standard run with auto-generated run_id
    python -m runtime.phase_4_scrape

    # Run with custom run_id
    python -m runtime.phase_4_scrape --run-id 20240115-091500

    # Custom config and output
    python -m runtime.phase_4_scrape --config config/urls.yaml --output-dir data/raw
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from runtime.phase_4_scrape.fetcher import HTTPFetcher
from runtime.phase_4_scrape.storage import RawStorage


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_url_config(config_path: str) -> list[dict]:
    """
    Load URL configuration from YAML file.
    
    Returns list of dicts with 'url' and 'scheme_id' keys.
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    urls = []
    for scheme in config.get('schemes', []):
        urls.append({
            'url': scheme['url'],
            'scheme_id': scheme['id'],
            'scheme_name': scheme.get('name', ''),
            'category': scheme.get('category', '')
        })
    
    return urls


def generate_run_id() -> str:
    """Generate a run ID based on current timestamp."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def main():
    """Main entry point for scraping service."""
    parser = argparse.ArgumentParser(
        description="Phase 4.0: Scrape URLs from registry and save raw HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m runtime.phase_4_scrape
  python -m runtime.phase_4_scrape --run-id 20240115-091500 --verbose
        """
    )
    
    parser.add_argument(
        '--run-id',
        type=str,
        default=None,
        help='Run identifier (default: auto-generated from timestamp)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/urls.yaml',
        help='Path to URL registry YAML file (default: config/urls.yaml)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/raw',
        help='Base directory for raw HTML storage (default: data/raw)'
    )
    parser.add_argument(
        '--user-agent',
        type=str,
        default=None,
        help='User-Agent string (default: from INGEST_USER_AGENT env var or "MutualFundFAQ-Assistant/1.0")'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=2.0,
        help='Delay between requests in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging("DEBUG" if args.verbose else "INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Phase 4.0: Scraping Service")
    logger.info("=" * 60)
    
    # Generate or use provided run_id
    run_id = args.run_id or generate_run_id()
    logger.info(f"Run ID: {run_id}")
    
    # Check config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    
    logger.info(f"Loading URLs from: {config_path}")
    
    try:
        urls = load_url_config(str(config_path))
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)
    
    if not urls:
        logger.error("No URLs found in config")
        sys.exit(1)
    
    logger.info(f"Loaded {len(urls)} URLs")
    
    # Get user agent from env or args
    user_agent = args.user_agent or os.getenv('INGEST_USER_AGENT', 'MutualFundFAQ-Assistant/1.0')
    
    # Initialize fetcher and storage
    fetcher = HTTPFetcher(
        user_agent=user_agent,
        timeout=args.timeout,
        rate_limit_delay=args.rate_limit
    )
    
    storage = RawStorage(base_dir=args.output_dir)
    
    # Fetch all URLs
    logger.info("Starting fetch operations...")
    results = fetcher.fetch_all(urls)
    
    # Save results
    logger.info("Saving results...")
    manifest = storage.save_all(results, run_id)
    
    # Summary
    logger.info("=" * 60)
    logger.info("Scraping Complete")
    logger.info("=" * 60)
    logger.info(f"Total URLs: {manifest['total_urls']}")
    logger.info(f"Successful: {manifest['successful']}")
    logger.info(f"Failed: {manifest['failed']}")
    logger.info(f"Output directory: {Path(args.output_dir) / run_id}")
    logger.info("=" * 60)
    
    # Exit with error if any failed
    if manifest['failed'] > 0:
        logger.warning(f"{manifest['failed']} URL(s) failed to fetch")
        # Don't exit with error - let pipeline continue with partial data
    
    logger.info("Phase 4.0 complete")


if __name__ == '__main__':
    main()
