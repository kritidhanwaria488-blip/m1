"""
Phase 7: Refusal & Safety Layer

Intent routing, advisory detection, and post-generation validation.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Advisory/comparative query patterns
ADVISORY_PATTERNS = [
    r"should\s+i\s+(buy|invest|choose|pick)",
    r"which\s+(is\s+)?better\s+(than)?",
    r"best\s+fund",
    r"recommend",
    r"suggest",
    r"good\s+investment",
    r"worth\s+(buying|investing)",
    r"outperform",
    r"beat\s+the\s+market",
    r"guarantee",
    r"sure\s+shot",
    r"safe\s+bet",
    r"i\s+am\s+\d+.*(years\s+old|age)",  # Personal situation
    r"my\s+portfolio",
    r"for\s+me",
]

# Forbidden phrases in generated output
FORBIDDEN_PHRASES = [
    "invest in",
    "you should",
    "better than",
    "outperform",
    "guarantee",
    "guaranteed",
    "will make you",
    "best choice",
    "recommend buying",
    "recommend investing",
    "must buy",
    "safe investment",
    "high returns",
]

# Allowlisted domains for citations
ALLOWLISTED_DOMAINS = [
    "hdfcfund.com",
    "amfiindia.com",
    "sebi.gov.in",
    "mfapi.com",
    "moneycontrol.com",
    "valueresearchonline.com",
    "morningstar.in",
]


@dataclass
class SafetyCheckResult:
    """Result of safety validation."""
    is_safe: bool
    is_advisory: bool
    contains_pii: bool
    violations: List[str]
    pii_detected: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "is_advisory": self.is_advisory,
            "contains_pii": self.contains_pii,
            "violations": self.violations,
            "pii_detected": self.pii_detected
        }


@dataclass
class ValidationResult:
    """Result of post-generation validation."""
    is_valid: bool
    sentence_count: int
    has_valid_url: bool
    url_on_allowlist: bool
    forbidden_phrases_found: List[str]
    violations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "sentence_count": self.sentence_count,
            "has_valid_url": self.has_valid_url,
            "url_on_allowlist": self.url_on_allowlist,
            "forbidden_phrases_found": self.forbidden_phrases_found,
            "violations": self.violations
        }


class AdvisoryDetector:
    """
    Detects advisory/comparative queries that should be refused.
    
    Patterns:
    - "should I", "which is better", "best fund", "recommend"
    - Implicit ranking, personal situations
    """
    
    def __init__(self, patterns: Optional[List[str]] = None):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in (patterns or ADVISORY_PATTERNS)]
    
    def is_advisory(self, query: str) -> Tuple[bool, List[str]]:
        """
        Check if query is advisory/comparative.
        
        Returns:
            Tuple of (is_advisory, matched_patterns)
        """
        matched = []
        for pattern in self.patterns:
            if pattern.search(query):
                matched.append(pattern.pattern)
        
        is_advisory = len(matched) > 0
        if is_advisory:
            logger.warning(f"Advisory query detected: {matched}")
        
        return is_advisory, matched


class PIIDetector:
    """
    Detects personally identifiable information (PII).
    
    Patterns:
    - PAN: [A-Z]{5}[0-9]{4}[A-Z]{1}
    - Aadhaar: [0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}
    - Account numbers: \d{9,18}
    """
    
    PII_PATTERNS = {
        "PAN": re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]{1}"),
        "Aadhaar": re.compile(r"[0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}"),
        "Account_Number": re.compile(r"\b\d{9,18}\b"),
        "Email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        "Phone": re.compile(r"\b\d{10}\b|\+91[-\s]?\d{10}"),
    }
    
    def detect(self, text: str) -> Tuple[bool, List[str]]:
        """
        Detect PII in text.
        
        Returns:
            Tuple of (contains_pii, detected_types)
        """
        detected = []
        for pii_type, pattern in self.PII_PATTERNS.items():
            if pattern.search(text):
                detected.append(pii_type)
                logger.warning(f"PII detected: {pii_type}")
        
        return len(detected) > 0, detected


class SafetyRouter:
    """
    Routes queries based on safety checks.
    
    For advisory queries:
    - No retrieval for advisory queries
    - Or retrieval only for static educational snippets
    - Response: Polite refusal + one educational link
    """
    
    def __init__(
        self,
        advisory_patterns: Optional[List[str]] = None,
        educational_urls: Optional[List[str]] = None
    ):
        self.advisory_detector = AdvisoryDetector(advisory_patterns)
        self.pii_detector = PIIDetector()
        self.educational_urls = educational_urls or [
            "https://www.amfiindia.com/investor-corner/knowledge-center/what-are-mutual-funds.html",
            "https://www.sebi.gov.in/investor-education.html"
        ]
    
    def check_query(self, query: str) -> SafetyCheckResult:
        """
        Perform safety checks on input query.
        
        Args:
            query: User query text
            
        Returns:
            SafetyCheckResult with all safety checks
        """
        violations = []
        
        # Check for advisory intent
        is_advisory, advisory_patterns = self.advisory_detector.is_advisory(query)
        if is_advisory:
            violations.append("Advisory/comparative query detected")
        
        # Check for PII
        contains_pii, pii_types = self.pii_detector.detect(query)
        if contains_pii:
            violations.append(f"PII detected: {', '.join(pii_types)}")
        
        is_safe = not is_advisory and not contains_pii
        
        return SafetyCheckResult(
            is_safe=is_safe,
            is_advisory=is_advisory,
            contains_pii=contains_pii,
            violations=violations,
            pii_detected=pii_types
        )
    
    def get_refusal_response(self, check_result: SafetyCheckResult) -> Dict[str, Any]:
        """
        Generate refusal response for unsafe queries.
        
        Args:
            check_result: Safety check result
            
        Returns:
            Refusal response with educational link
        """
        if check_result.contains_pii:
            message = (
                "I cannot process queries containing personal information "
                "(PAN, Aadhaar, account numbers, etc.). Please remove any PII and try again."
            )
        elif check_result.is_advisory:
            message = (
                "I cannot provide investment advice or recommendations. "
                "Please consult a SEBI-registered investment advisor.\n\n"
                "For educational information, see: "
            )
        else:
            message = "I cannot process this query."
        
        return {
            "type": "refusal",
            "message": message,
            "educational_url": self.educational_urls[0] if check_result.is_advisory else None,
            "safety_check": check_result.to_dict()
        }


class PostGenerationValidator:
    """
    Validates generated output against safety rules.
    
    Checks:
    - Sentence count ≤ 3
    - Exactly one HTTP(S) URL, on allowlist
    - No forbidden phrases
    """
    
    def __init__(
        self,
        max_sentences: int = 3,
        forbidden_phrases: Optional[List[str]] = None,
        allowlisted_domains: Optional[List[str]] = None
    ):
        self.max_sentences = max_sentences
        self.forbidden_phrases = [p.lower() for p in (forbidden_phrases or FORBIDDEN_PHRASES)]
        self.allowlisted_domains = allowlisted_domains or ALLOWLISTED_DOMAINS
    
    def count_sentences(self, text: str) -> int:
        """Count sentences using regex split on . ? !"""
        # Split on sentence terminators
        sentences = re.split(r'[.!?]+', text)
        # Filter out empty strings and whitespace-only
        sentences = [s.strip() for s in sentences if s.strip()]
        return len(sentences)
    
    def validate_url(self, url: str) -> Tuple[bool, bool]:
        """
        Validate URL format and check if on allowlist.
        
        Returns:
            Tuple of (is_valid_url, is_on_allowlist)
        """
        if not url:
            return False, False
        
        try:
            parsed = urlparse(url)
            is_valid = parsed.scheme in ('http', 'https') and parsed.netloc
            
            if not is_valid:
                return False, False
            
            # Check allowlist
            domain = parsed.netloc.lower()
            is_on_allowlist = any(allowed in domain for allowed in self.allowlisted_domains)
            
            return is_valid, is_on_allowlist
            
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False, False
    
    def check_forbidden_phrases(self, text: str) -> List[str]:
        """Check for forbidden advisory phrases."""
        text_lower = text.lower()
        found = []
        for phrase in self.forbidden_phrases:
            if phrase in text_lower:
                found.append(phrase)
        return found
    
    def validate(
        self,
        answer: str,
        citation_url: str
    ) -> ValidationResult:
        """
        Validate generated answer.
        
        Args:
            answer: Generated answer text
            citation_url: Citation URL
            
        Returns:
            ValidationResult with all checks
        """
        violations = []
        
        # Check sentence count
        sentence_count = self.count_sentences(answer)
        if sentence_count > self.max_sentences:
            violations.append(f"Too many sentences: {sentence_count} (max: {self.max_sentences})")
        
        # Check URL validity
        has_valid_url, url_on_allowlist = self.validate_url(citation_url)
        if not has_valid_url:
            violations.append("Invalid or missing citation URL")
        elif not url_on_allowlist:
            violations.append(f"URL not on allowlist: {citation_url}")
        
        # Check forbidden phrases
        forbidden_found = self.check_forbidden_phrases(answer)
        if forbidden_found:
            violations.append(f"Forbidden phrases: {', '.join(forbidden_found)}")
        
        is_valid = len(violations) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            sentence_count=sentence_count,
            has_valid_url=has_valid_url,
            url_on_allowlist=url_on_allowlist,
            forbidden_phrases_found=forbidden_found,
            violations=violations
        )


class SafetyLayer:
    """
    Complete safety layer combining all safety checks.
    """
    
    def __init__(
        self,
        max_sentences: int = 3,
        advisory_patterns: Optional[List[str]] = None,
        forbidden_phrases: Optional[List[str]] = None,
        allowlisted_domains: Optional[List[str]] = None,
        educational_urls: Optional[List[str]] = None
    ):
        self.router = SafetyRouter(advisory_patterns, educational_urls)
        self.validator = PostGenerationValidator(
            max_sentences=max_sentences,
            forbidden_phrases=forbidden_phrases,
            allowlisted_domains=allowlisted_domains
        )
    
    def check_input(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Check if query is safe to process.
        
        Args:
            query: User input query
            
        Returns:
            Refusal response if unsafe, None if safe
        """
        check_result = self.router.check_query(query)
        
        if not check_result.is_safe:
            return self.router.get_refusal_response(check_result)
        
        return None
    
    def validate_output(
        self,
        answer: str,
        citation_url: str
    ) -> ValidationResult:
        """
        Validate generated output.
        
        Args:
            answer: Generated answer
            citation_url: Citation URL
            
        Returns:
            ValidationResult
        """
        return self.validator.validate(answer, citation_url)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test safety layer
    safety = SafetyLayer()
    
    # Test advisory detection
    test_queries = [
        "What is the expense ratio of HDFC ELSS?",  # Safe
        "Should I invest in HDFC ELSS?",  # Advisory
        "Which is better, HDFC ELSS or SBI Blue Chip?",  # Comparative
        "My PAN is ABCDE1234F",  # PII
        "I am 45 years old, what fund is good for me?",  # Advisory with PII
    ]
    
    print("=" * 60)
    print("Safety Layer Tests")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = safety.check_input(query)
        if result:
            print(f"  REFUSED: {result['message'][:50]}...")
        else:
            print(f"  APPROVED")
    
    # Test validation
    print("\n" + "=" * 60)
    print("Post-Generation Validation Tests")
    print("=" * 60)
    
    test_answers = [
        ("HDFC ELSS has an expense ratio of 1.23%. The fund is managed by HDFC AMC.", 
         "https://www.hdfcfund.com/hdfc-elss-taxsaver"),  # Valid
        ("You should invest in HDFC ELSS for tax savings. It is the best choice. "
         "This fund will give you high returns guaranteed.", 
         "https://www.hdfcfund.com"),  # Forbidden phrases
        ("HDFC ELSS is an equity-linked savings scheme with a three-year lock-in. "
         "It offers tax benefits under Section 80C. The fund invests primarily in equities. "
         "Investors should consider their risk profile.", 
         "https://www.hdfcfund.com"),  # Too long
    ]
    
    for answer, url in test_answers:
        print(f"\nAnswer: {answer[:60]}...")
        print(f"URL: {url}")
        result = safety.validate_output(answer, url)
        print(f"  Valid: {result.is_valid}")
        print(f"  Sentences: {result.sentence_count}")
        print(f"  URL on allowlist: {result.url_on_allowlist}")
        if result.violations:
            print(f"  Violations: {result.violations}")
