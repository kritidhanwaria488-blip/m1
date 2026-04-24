"""
Phase 4.1: HTML Parser & Extractor

Parses Groww scheme pages and extracts structured fund metrics.
"""

import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pathlib import Path

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class FundMetrics:
    """Structured fund metrics extracted from scheme page."""
    
    # Identity
    scheme_id: str
    scheme_name: str
    amc: str
    source_url: str
    source_type: str = "groww_scheme_page"
    
    # Extraction metadata
    fetched_at: str = ""
    content_hash: str = ""
    extracted_at: str = ""
    
    # Fund metrics (all optional - null if not found)
    nav: Optional[float] = None
    nav_date: Optional[str] = None
    currency: str = "INR"
    
    minimum_sip: Optional[float] = None
    minimum_sip_frequency: Optional[str] = None  # monthly, weekly, etc.
    
    fund_size: Optional[float] = None  # In Cr
    fund_size_unit: str = "Cr"
    
    expense_ratio: Optional[float] = None  # As percentage (e.g., 0.52 for 0.52%)
    expense_ratio_type: Optional[str] = None  # Direct, Regular
    
    rating_value: Optional[str] = None  # Raw value e.g., "5", "4★"
    rating_kind: Optional[str] = None  # riskometer, analyst, unknown
    
    # Additional fields (for future expansion)
    benchmark: Optional[str] = None
    risk_level: Optional[str] = None
    fund_type: Optional[str] = None
    category: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with null handling."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class GrowwSchemeParser:
    """
    Parser for Groww mutual fund scheme pages.
    
    Extracts structured metrics from HTML using CSS selectors and regex patterns.
    """
    
    def __init__(self):
        self.selectors = {
            # NAV - usually in a prominent box
            'nav': [
                '[data-testid="nav-value"]',
                '.nav-value',
                '[class*="nav"]',
                '.mf-nav',
            ],
            # Expense ratio
            'expense_ratio': [
                '[data-testid="expense-ratio"]',
                '.expense-ratio',
                'td:contains("Expense Ratio") + td',
                'tr:has(td:contains("Expense Ratio")) td:last-child',
            ],
            # Minimum SIP
            'minimum_sip': [
                '[data-testid="min-sip"]',
                '.min-sip',
                'td:contains("Min SIP") + td',
                'tr:has(td:contains("Min SIP")) td:last-child',
            ],
            # Fund Size (AUM)
            'fund_size': [
                '[data-testid="fund-size"]',
                '.fund-size',
                '.aum-value',
                'td:contains("Fund Size") + td',
                'tr:has(td:contains("Fund Size")) td:last-child',
            ],
            # Rating - could be stars or riskometer
            'rating': [
                '[data-testid="rating"]',
                '.rating',
                '.star-rating',
                '[class*="riskometer"]',
            ],
        }
    
    def _clean_number(self, text: str) -> Optional[float]:
        """
        Extract numeric value from text.
        
        Examples:
            "₹ 125.67" → 125.67
            "0.52%" → 0.52
            "₹ 500" → 500
            "28,500 Cr" → 28500
        """
        if not text:
            return None
        
        # Remove currency symbols, commas, whitespace
        cleaned = re.sub(r'[₹$,\s%]', '', text.strip())
        
        # Extract number (including decimals)
        match = re.search(r'[\d.]+', cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None
    
    def _extract_nav(self, soup: BeautifulSoup) -> tuple[Optional[float], Optional[str]]:
        """Extract NAV value and date."""
        # Try various selectors
        for selector in self.selectors['nav']:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                nav = self._clean_number(text)
                if nav:
                    # Look for date nearby
                    date_elem = element.find_next(string=re.compile(r'\d{1,2}\s+[A-Za-z]{3}')) or \
                               element.parent.find(string=re.compile(r'as\s+on'))
                    nav_date = None
                    if date_elem:
                        date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', str(date_elem))
                        if date_match:
                            nav_date = date_match.group(1)
                    
                    logger.debug(f"Found NAV: {nav} (date: {nav_date})")
                    return nav, nav_date
        
        # Fallback: search for pattern in entire text
        nav_patterns = [
            r'NAV[\s:₹]*([\d,.]+)',
            r'Net\s+Asset\s+Value[\s:₹]*([\d,.]+)',
        ]
        for pattern in nav_patterns:
            match = re.search(pattern, soup.get_text(), re.IGNORECASE)
            if match:
                nav = self._clean_number(match.group(1))
                if nav:
                    return nav, None
        
        return None, None
    
    def _extract_expense_ratio(self, soup: BeautifulSoup) -> tuple[Optional[float], Optional[str]]:
        """Extract expense ratio and type (Direct/Regular)."""
        for selector in self.selectors['expense_ratio']:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                expense = self._clean_number(text)
                if expense:
                    # Determine type from surrounding text
                    type_elem = element.find_previous(string=re.compile(r'(Direct|Regular)', re.I)) or \
                               element.find_parent(text=re.compile(r'(Direct|Regular)', re.I))
                    expense_type = None
                    if type_elem:
                        type_match = re.search(r'(Direct|Regular)', str(type_elem), re.I)
                        if type_match:
                            expense_type = type_match.group(1).capitalize()
                    
                    logger.debug(f"Found Expense Ratio: {expense}% (type: {expense_type})")
                    return expense, expense_type
        
        # Fallback patterns
        expense_patterns = [
            r'Expense\s+Ratio[\s:]*([\d.]+)\s*%',
            r'Expense\s+Ratio.*?([\d.]+)\s*%',
        ]
        text = soup.get_text()
        for pattern in expense_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._clean_number(match.group(1)), None
        
        return None, None
    
    def _extract_minimum_sip(self, soup: BeautifulSoup) -> tuple[Optional[float], Optional[str]]:
        """Extract minimum SIP amount and frequency."""
        for selector in self.selectors['minimum_sip']:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                sip = self._clean_number(text)
                if sip:
                    # Determine frequency
                    freq = "monthly"  # default
                    if "weekly" in text.lower():
                        freq = "weekly"
                    elif "daily" in text.lower():
                        freq = "daily"
                    
                    logger.debug(f"Found Minimum SIP: {freq} ₹{sip}")
                    return sip, freq
        
        # Fallback patterns
        sip_patterns = [
            r'Min(?:imum)?\s+SIP[\s:₹]*([\d,]+)',
            r'SIP\s+from[\s:₹]*([\d,]+)',
        ]
        text = soup.get_text()
        for pattern in sip_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._clean_number(match.group(1)), "monthly"
        
        return None, None
    
    def _extract_fund_size(self, soup: BeautifulSoup) -> tuple[Optional[float], Optional[str]]:
        """Extract fund size/AUM."""
        for selector in self.selectors['fund_size']:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                size = self._clean_number(text)
                if size:
                    # Determine unit
                    unit = "Cr"
                    if "lakh" in text.lower() or "lac" in text.lower():
                        unit = "Lakh"
                    elif "million" in text.lower() or "mn" in text.lower():
                        unit = "Mn"
                    elif "billion" in text.lower() or "bn" in text.lower():
                        unit = "Bn"
                    
                    logger.debug(f"Found Fund Size: {size} {unit}")
                    return size, unit
        
        # Fallback patterns
        size_patterns = [
            r'Fund\s+Size[\s:₹]*([\d,.]+)\s*(Cr|Lakh|Lac)?',
            r'AUM[\s:₹]*([\d,.]+)\s*(Cr|Lakh|Lac)?',
        ]
        text = soup.get_text()
        for pattern in size_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                size = self._clean_number(match.group(1))
                unit = match.group(2) if match.group(2) else "Cr"
                return size, unit
        
        return None, None
    
    def _extract_rating(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        """
        Extract rating and determine type.
        
        Types:
        - riskometer: Risk level (Very High, High, Moderate, etc.)
        - analyst: Star rating (1-5 stars)
        - unknown: Could not determine type
        """
        for selector in self.selectors['rating']:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                
                # Check for star rating
                star_match = re.search(r'(\d)\s*(?:star|★|☆)', text, re.I)
                if star_match:
                    rating = star_match.group(1)
                    logger.debug(f"Found Analyst Rating: {rating} stars")
                    return rating, "analyst"
                
                # Check for riskometer patterns
                risk_patterns = [
                    r'(Very\s+High|High|Moderately\s+High|Moderate|Low|Very\s+Low)\s+risk',
                    r'Risk[\s:]+(Very\s+High|High|Moderately\s+High|Moderate|Low|Very\s+Low)',
                ]
                for pattern in risk_patterns:
                    risk_match = re.search(pattern, text, re.I)
                    if risk_match:
                        rating = risk_match.group(1)
                        logger.debug(f"Found Riskometer: {rating}")
                        return rating, "riskometer"
        
        # Fallback: search in full text
        text = soup.get_text()
        
        # Riskometer in text
        risk_match = re.search(
            r'(Very\s+High|High|Moderately\s+High|Moderate|Low)\s+risk', 
            text, re.I
        )
        if risk_match:
            return risk_match.group(1), "riskometer"
        
        return None, None
    
    def parse(self, html_content: str, metadata: Dict[str, Any]) -> FundMetrics:
        """
        Parse HTML and extract all metrics.
        
        Args:
            html_content: Raw HTML string
            metadata: Dict with scheme_id, scheme_name, amc, source_url, fetched_at, content_hash
            
        Returns:
            FundMetrics dataclass with extracted values
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Initialize metrics with metadata
        metrics = FundMetrics(
            scheme_id=metadata.get('scheme_id', ''),
            scheme_name=metadata.get('scheme_name', ''),
            amc=metadata.get('amc', ''),
            source_url=metadata.get('source_url', ''),
            source_type=metadata.get('source_type', 'groww_scheme_page'),
            fetched_at=metadata.get('fetched_at', ''),
            content_hash=metadata.get('content_hash', ''),
            extracted_at=datetime.now(timezone.utc).isoformat(),
        )
        
        # Extract all metrics
        metrics.nav, metrics.nav_date = self._extract_nav(soup)
        metrics.expense_ratio, metrics.expense_ratio_type = self._extract_expense_ratio(soup)
        metrics.minimum_sip, metrics.minimum_sip_frequency = self._extract_minimum_sip(soup)
        metrics.fund_size, metrics.fund_size_unit = self._extract_fund_size(soup)
        metrics.rating_value, metrics.rating_kind = self._extract_rating(soup)
        
        # Try to extract category from page
        category_elem = soup.find(string=re.compile(r'(Equity|Debt|Hybrid|Liquid)', re.I))
        if category_elem:
            cat_match = re.search(r'(Large\s+Cap|Mid\s+Cap|Small\s+Cap|Multi\s+Cap|Equity|Debt|Hybrid|ELSS)', 
                                 str(category_elem), re.I)
            if cat_match:
                metrics.category = cat_match.group(1)
        
        logger.info(
            f"Extracted metrics for {metrics.scheme_id}: "
            f"NAV={metrics.nav}, "
            f"Expense={metrics.expense_ratio}%, "
            f"SIP={metrics.minimum_sip}, "
            f"Size={metrics.fund_size} {metrics.fund_size_unit}, "
            f"Rating={metrics.rating_value}({metrics.rating_kind})"
        )
        
        return metrics
