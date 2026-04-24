"""
Phase 4.1: Normalization & Structured Extraction CLI

Parses raw HTML, extracts structured fund metrics (NAV, SIP, Expense Ratio, etc.),
and saves cleaned HTML + structured JSON.

Usage:
    python -m runtime.phase_4_normalize --run-id <RUN_ID>

Examples:
    python -m runtime.phase_4_normalize --run-id 20240115-091500
    python -m runtime.phase_4_normalize --run-id 20240115-091500 --verbose
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from bs4 import BeautifulSoup

from runtime.phase_4_normalize.parser import GrowwSchemeParser, FundMetrics
from runtime.phase_4_normalize.storage import StructuredStorage
from runtime.phase_4_scrape.storage import RawStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_html(html_content: str) -> str:
    """
    Clean HTML by removing boilerplate elements.
    
    Removes: nav, footer, scripts, styles, ads
    Keeps: main content, tables, headings
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        element.decompose()
    
    # Remove elements with common ad/boilerplate classes
    ad_classes = ['ad', 'advertisement', 'popup', 'modal', 'cookie-banner', 'newsletter']
    for class_name in ad_classes:
        for element in soup.find_all(class_=re.compile(class_name, re.I)):
            element.decompose()
    
    # Get text but preserve structure
    return str(soup)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 4.1: Normalize HTML and extract structured fund metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m runtime.phase_4_normalize --run-id 20240115-091500
  python -m runtime.phase_4_normalize --run-id 20240115-091500 --verbose
        """
    )
    
    parser.add_argument('--run-id', required=True, help='Run identifier from Phase 4.0')
    parser.add_argument('--input-dir', default='data/raw', help='Input raw HTML directory')
    parser.add_argument('--output-dir', default='data/structured', help='Output directory')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=" * 60)
    logger.info("Phase 4.1: Normalization & Structured Extraction")
    logger.info("=" * 60)
    logger.info(f"Run ID: {args.run_id}")
    
    # Initialize storage and parser
    raw_storage = RawStorage(base_dir=args.input_dir)
    structured_storage = StructuredStorage(base_dir=args.output_dir)
    scheme_parser = GrowwSchemeParser()
    
    # Load scrape manifest
    scrape_manifest = raw_storage.load_manifest(args.run_id)
    if not scrape_manifest:
        logger.error(f"Scrape manifest not found for run {args.run_id}")
        sys.exit(1)
    
    logger.info(f"Found {scrape_manifest['successful']} successful scrapes")
    
    # Process each scheme
    metrics_list = []
    
    for file_info in scrape_manifest.get('files', []):
        scheme_id = file_info['scheme_id']
        source_url = file_info['url']
        content_hash = file_info['content_hash']
        
        logger.info(f"Processing {scheme_id}...")
        
        # Load raw HTML
        html_content = raw_storage.load_html(args.run_id, scheme_id)
        if not html_content:
            logger.warning(f"Could not load HTML for {scheme_id}, skipping")
            continue
        
        # Clean HTML
        cleaned_html = clean_html(html_content)
        
        # Save normalized HTML
        normalized_path = structured_storage.save_normalized_html(
            scheme_id=scheme_id,
            html_content=cleaned_html,
            run_id=args.run_id
        )
        
        if not normalized_path:
            logger.warning(f"Failed to save normalized HTML for {scheme_id}")
        
        # Extract structured metrics
        metadata = {
            'scheme_id': scheme_id,
            'scheme_name': file_info.get('scheme_name', scheme_id),
            'amc': 'hdfc_mutual_fund',
            'source_url': source_url,
            'fetched_at': scrape_manifest.get('timestamp', ''),
            'content_hash': content_hash
        }
        
        try:
            metrics = scheme_parser.parse(html_content, metadata)
            metrics_list.append(metrics)
            
            # Save individual metrics
            structured_storage.save_metrics(metrics, args.run_id)
            
            logger.info(
                f"Extracted: NAV={metrics.nav}, "
                f"Expense={metrics.expense_ratio}%, "
                f"SIP=₹{metrics.minimum_sip}, "
                f"Size={metrics.fund_size}Cr"
            )
            
        except Exception as e:
            logger.error(f"Failed to parse {scheme_id}: {e}")
            continue
    
    # Save combined manifest
    manifest = structured_storage.save_all_metrics(metrics_list, args.run_id)
    
    # Summary
    logger.info("=" * 60)
    logger.info("Phase 4.1 Complete")
    logger.info("=" * 60)
    logger.info(f"Schemes processed: {len(metrics_list)}")
    logger.info(f"Metrics extracted: {len(metrics_list)}")
    logger.info(f"Output: {Path(args.output_dir) / args.run_id}")
    
    # Show metrics summary
    for m in metrics_list:
        logger.info(
            f"  {m.scheme_id}: "
            f"NAV={m.nav or 'N/A'}, "
            f"Expense={m.expense_ratio or 'N/A'}%, "
            f"SIP={m.minimum_sip or 'N/A'}, "
            f"Size={m.fund_size or 'N/A'}Cr, "
            f"Rating={m.rating_value or 'N/A'}"
        )
    
    logger.info("=" * 60)


if __name__ == '__main__':
    import re  # Required for clean_html
    main()
