#!/usr/bin/env python3
"""
Local Scheduler - Simulates GitHub Actions Ingestion Pipeline

Runs all ingestion phases in sequence with comprehensive logging:
Phase 4.0: Scrape → Phase 4.1: Normalize → Phase 4.2: Chunk & Embed → Phase 4.3: Index

Usage:
    python scripts/local_scheduler.py [--run-id <ID>] [--verbose]

Logs to: logs/scheduler_YYYYMMDD-HHMMSS.log
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

# Configure logging
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
LOG_FILE = LOGS_DIR / f"scheduler_{RUN_ID}.log"

# Setup file and console logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("LocalScheduler")

# ANSI colors for console output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def log_section(title: str, width: int = 70) -> None:
    """Log a section header."""
    logger.info("")
    logger.info("=" * width)
    logger.info(f"  {title}")
    logger.info("=" * width)


def log_subsection(title: str) -> None:
    """Log a subsection header."""
    logger.info("")
    logger.info(f"--- {title} ---")


def run_phase(
    phase_name: str,
    command: List[str],
    env_vars: Dict[str, str] = None,
    timeout: int = 300
) -> Tuple[bool, str, float]:
    """
    Run a pipeline phase and capture output.
    
    Returns:
        (success: bool, output: str, duration: float)
    """
    log_subsection(f"Running {phase_name}")
    logger.info(f"Command: {' '.join(command)}")
    
    start_time = time.time()
    
    try:
        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # Run the command
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
            cwd=Path(__file__).parent.parent  # Run from project root
        )
        
        duration = time.time() - start_time
        
        # Log stdout
        if result.stdout:
            logger.info(f"STDOUT:\n{result.stdout}")
        
        # Log stderr (if any)
        if result.stderr:
            logger.warning(f"STDERR:\n{result.stderr}")
        
        # Check result
        if result.returncode == 0:
            logger.info(f"[PASS] {phase_name} completed in {duration:.2f}s")
            return True, result.stdout, duration
        else:
            logger.error(f"[FAIL] {phase_name} failed with code {result.returncode}")
            logger.error(f"Error output: {result.stderr[:500]}")
            return False, result.stderr, duration
            
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        logger.error(f"[TIMEOUT] {phase_name} timed out after {timeout}s")
        return False, "Timeout", duration
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[ERROR] {phase_name} crashed: {e}")
        return False, str(e), duration


def run_pipeline(run_id: str, verbose: bool = False) -> Dict:
    """Run the complete ingestion pipeline."""
    
    log_section("LOCAL INGESTION PIPELINE SCHEDULER")
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Log File: {LOG_FILE.absolute()}")
    logger.info("")
    
    results = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phases": {},
        "success": True,
        "total_duration": 0,
    }
    
    pipeline_start = time.time()
    
    # ============================================
    # Phase 4.0: Scrape
    # ============================================
    log_section("PHASE 4.0: SCRAPE URLS")
    
    success, output, duration = run_phase(
        "Phase 4.0 (Scrape)",
        [
            sys.executable, "-m", "runtime.phase_4_scrape",
            "--run-id", run_id,
            "--config", "config/urls.yaml",
            *(["--verbose"] if verbose else [])
        ]
    )
    
    results["phases"]["4.0_scrape"] = {
        "success": success,
        "duration": duration,
        "output_preview": output[:500] if output else None
    }
    
    if not success:
        logger.error("[HALT] Pipeline halted: Scrape phase failed")
        results["success"] = False
        return results
    
    # ============================================
    # Phase 4.1: Normalize
    # ============================================
    log_section("PHASE 4.1: NORMALIZE HTML")
    
    success, output, duration = run_phase(
        "Phase 4.1 (Normalize)",
        [
            sys.executable, "-m", "runtime.phase_4_normalize",
            "--run-id", run_id,
            "--input-dir", "data/raw",
            "--output-dir", "data/structured",
            *(["--verbose"] if verbose else [])
        ]
    )
    
    results["phases"]["4.1_normalize"] = {
        "success": success,
        "duration": duration,
        "output_preview": output[:500] if output else None
    }
    
    if not success:
        logger.error("[HALT] Pipeline halted: Normalize phase failed")
        results["success"] = False
        return results
    
    # ============================================
    # Phase 4.2: Chunk & Embed
    # ============================================
    log_section("PHASE 4.2: CHUNK & EMBED")
    
    success, output, duration = run_phase(
        "Phase 4.2 (Chunk & Embed)",
        [
            sys.executable, "-m", "runtime.phase_4_chunk_embed",
            "--run-id", run_id,
            "--input-dir", "data/structured",
            "--output-dir", "data/structured",
            "--model", "BAAI/bge-small-en-v1.5",
            "--chunk-size", "375",
            "--overlap", "0.12",
            *(["--verbose"] if verbose else [])
        ]
    )
    
    results["phases"]["4.2_chunk_embed"] = {
        "success": success,
        "duration": duration,
        "output_preview": output[:500] if output else None
    }
    
    if not success:
        logger.error("[HALT] Pipeline halted: Chunk/Embed phase failed")
        results["success"] = False
        return results
    
    # ============================================
    # Phase 4.3: Index to Local ChromaDB
    # ============================================
    log_section("PHASE 4.3: INDEX TO LOCAL CHROMADB")
    
    success, output, duration = run_phase(
        "Phase 4.3 (Index)",
        [
            sys.executable, "-m", "runtime.phase_4_index",
            "--run-id", run_id,
            "--input-dir", "data/structured",
            "--collection", "mf_faq_chunks",
            "--persist-dir", "data/chroma",
            *(["--verbose"] if verbose else [])
        ]
    )
    
    results["phases"]["4.3_index"] = {
        "success": success,
        "duration": duration,
        "output_preview": output[:500] if output else None
    }
    
    if not success:
        logger.error("[HALT] Pipeline halted: Index phase failed")
        results["success"] = False
        return results
    
    # ============================================
    # Verification
    # ============================================
    log_section("VERIFICATION")
    
    try:
        import chromadb
        client = chromadb.PersistentClient(path="data/chroma")
        collection = client.get_collection("mf_faq_chunks")
        count = collection.count()
        
        logger.info(f"[VERIFY] Collection 'mf_faq_chunks': {count} documents")
        results["final_collection_count"] = count
        
        # Get manifest info
        manifest_path = Path(f"data/structured/{run_id}/chunked/manifest.json")
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
                logger.info(f"Chunks created: {manifest.get('total_chunks', 'N/A')}")
                logger.info(f"Schemes processed: {manifest.get('total_schemes', 'N/A')}")
                results["manifest"] = manifest
    except Exception as e:
        logger.warning(f"[WARN] Verification check failed: {e}")
    
    # Calculate totals
    total_duration = time.time() - pipeline_start
    results["total_duration"] = total_duration
    
    # ============================================
    # Summary
    # ============================================
    log_section("PIPELINE SUMMARY")
    
    for phase_id, phase_data in results["phases"].items():
        status = "[PASS]" if phase_data["success"] else "[FAIL]"
        logger.info(f"{status} | {phase_id:<20} | {phase_data['duration']:>6.2f}s")
    
    logger.info("")
    logger.info(f"Total Duration: {total_duration:.2f}s")
    logger.info(f"Overall Status: {'[SUCCESS]' if results['success'] else '[FAILED]'}")
    logger.info(f"Log File: {LOG_FILE.absolute()}")
    logger.info("")
    logger.info("=" * 70)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Local Ingestion Pipeline Scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/local_scheduler.py
  python scripts/local_scheduler.py --run-id 20240424-180000
  python scripts/local_scheduler.py --verbose
        """
    )
    
    parser.add_argument(
        '--run-id',
        help='Custom run ID (default: auto-generated timestamp)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging for all phases'
    )
    
    args = parser.parse_args()
    
    # Use custom or auto-generated run ID
    run_id = args.run_id or RUN_ID
    
    # Update log file if custom run ID
    global LOG_FILE
    if args.run_id:
        LOG_FILE = LOGS_DIR / f"scheduler_{args.run_id}.log"
        # Reconfigure logging for new file
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                logging.root.removeHandler(handler)
        
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            '%Y-%m-%d %H:%M:%S'
        ))
        logging.root.addHandler(file_handler)
    
    # Run pipeline
    try:
        results = run_pipeline(run_id, verbose=args.verbose)
        
        # Save results JSON
        results_file = LOGS_DIR / f"results_{run_id}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to: {results_file.absolute()}")
        
        # Exit with appropriate code
        sys.exit(0 if results["success"] else 1)
        
    except KeyboardInterrupt:
        logger.info("\n[INTERRUPT] Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("[CRASH] Pipeline crashed unexpectedly")
        sys.exit(1)


if __name__ == "__main__":
    main()
