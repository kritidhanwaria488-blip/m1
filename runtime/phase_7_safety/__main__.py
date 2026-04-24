"""
Phase 7: Refusal & Safety Layer CLI

Usage:
    python -m runtime.phase_7_safety "What is the expense ratio?"
    python -m runtime.phase_7_safety --route-only "Should I invest?"
    python -m runtime.phase_7_safety --validate "answer text" --url "https://..."
"""

import argparse
import json
import logging
import sys

from runtime.phase_7_safety.validator import SafetyLayer, SafetyCheckResult, ValidationResult

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 7: Refusal & Safety Layer"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="User query to check"
    )
    parser.add_argument(
        "--route-only",
        action="store_true",
        help="Only check routing (advisory/PII detection)"
    )
    parser.add_argument(
        "--validate",
        help="Validate generated answer text"
    )
    parser.add_argument(
        "--url",
        help="Citation URL for validation"
    )
    parser.add_argument(
        "--max-sentences",
        type=int,
        default=3,
        help="Maximum allowed sentences (default: 3)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize safety layer
    safety = SafetyLayer(max_sentences=args.max_sentences)
    
    # Mode: Validate generated output
    if args.validate:
        if not args.url:
            logger.error("--url required with --validate")
            sys.exit(1)
        
        logger.info("=" * 60)
        logger.info("Phase 7: Post-Generation Validation")
        logger.info("=" * 60)
        
        result = safety.validate_output(args.validate, args.url)
        
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"\n{'=' * 60}")
            print("VALIDATION RESULT")
            print('=' * 60)
            print(f"Valid: {'[PASS] YES' if result.is_valid else '[FAIL] NO'}")
            print(f"Sentence count: {result.sentence_count} (max: {args.max_sentences})")
            print(f"URL valid: {result.has_valid_url}")
            print(f"URL on allowlist: {result.url_on_allowlist}")
            if result.forbidden_phrases_found:
                print(f"Forbidden phrases: {result.forbidden_phrases_found}")
            if result.violations:
                print(f"\nViolations:")
                for v in result.violations:
                    print(f"  [X] {v}")
            print('=' * 60)
        
        return 0 if result.is_valid else 1
    
    # Mode: Route-only check
    if args.route_only and args.query:
        logger.info("=" * 60)
        logger.info("Phase 7: Intent Routing Check")
        logger.info("=" * 60)
        logger.info(f"Query: {args.query}")
        logger.info("=" * 60)
        
        check_result = safety.router.check_query(args.query)
        
        if args.json:
            output = {
                "query": args.query,
                "routing": check_result.to_dict(),
                "action": "refuse" if not check_result.is_safe else "proceed"
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\n{'=' * 60}")
            print("ROUTING CHECK")
            print('=' * 60)
            print(f"Query: {args.query}")
            print(f"Is safe: {'[PASS] YES' if check_result.is_safe else '[FAIL] NO'}")
            print(f"Is advisory: {'YES' if check_result.is_advisory else 'NO'}")
            print(f"Contains PII: {'YES' if check_result.contains_pii else 'NO'}")
            if check_result.violations:
                print(f"\nViolations:")
                for v in check_result.violations:
                    print(f"  [X] {v}")
            if check_result.pii_detected:
                print(f"\nPII detected: {check_result.pii_detected}")
            
            print(f"\nAction: {'Proceed to retrieval' if check_result.is_safe else 'REFUSE - No retrieval'}")
            print('=' * 60)
        
        return 0 if check_result.is_safe else 1
    
    # Mode: Full pipeline check (default)
    if not args.query:
        logger.error("Query required (use --validate for output validation)")
        parser.print_help()
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Phase 7: Full Safety Check")
    logger.info("=" * 60)
    logger.info(f"Query: {args.query}")
    logger.info("=" * 60)
    
    # Check input
    refusal = safety.check_input(args.query)
    
    if refusal:
        logger.info("Query refused by safety layer")
        
        if args.json:
            print(json.dumps(refusal, indent=2))
        else:
            print(f"\n{'=' * 60}")
            print("REFUSAL RESPONSE")
            print('=' * 60)
            print(f"\n{refusal['message']}")
            if refusal.get('educational_url'):
                print(f"\nLearn more: {refusal['educational_url']}")
            print('\n' + '=' * 60)
        
        return 1
    
    logger.info("Query approved by safety layer")
    
    if args.json:
        print(json.dumps({
            "query": args.query,
            "approved": True,
            "message": "Safe to proceed with retrieval"
        }, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print("SAFETY CHECK PASSED")
        print('=' * 60)
        print("Query is safe to proceed with retrieval")
        print('=' * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
