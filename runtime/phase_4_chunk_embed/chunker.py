"""
Phase 4.2: HTML Chunker Module

Splits normalized HTML into semantic chunks while preserving tables and structure.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

from bs4 import BeautifulSoup, NavigableString

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A single document chunk with metadata."""
    
    # Identity
    chunk_id: str
    scheme_id: str
    scheme_name: str
    amc: str
    
    # Source metadata
    source_url: str
    source_type: str
    fetched_at: str
    content_hash: str
    
    # Chunk metadata
    chunk_index: int
    section_title: Optional[str]
    chunk_type: str  # overview, metrics_table, performance, details, risk
    
    # Content
    text: str
    token_count: int
    
    # Embedding (populated later)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class HTMLChunker:
    """
    Semantic chunker for HTML content.
    
    Preserves:
    - Tables (especially metrics tables)
    - Section structure
    - Context at chunk boundaries
    
    Target: 300-450 tokens per chunk with 10-15% overlap
    """
    
    def __init__(
        self,
        target_tokens: int = 375,
        overlap_percent: float = 0.12,
        max_tokens: int = 512,
        min_tokens: int = 100
    ):
        self.target_tokens = target_tokens
        self.overlap_tokens = int(target_tokens * overlap_percent)
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        
        # Approximate: 1 token ≈ 4 chars for English
        self.chars_per_token = 4
        self.target_chars = target_tokens * self.chars_per_token
        self.overlap_chars = self.overlap_tokens * self.chars_per_token
        
        logger.info(
            f"Initialized HTMLChunker: target={target_tokens} tokens "
            f"({self.target_chars} chars), overlap={self.overlap_tokens} tokens"
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return len(text) // self.chars_per_token
    
    def _clean_text(self, text: str) -> str:
        """Clean text content."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove empty lines
        text = re.sub(r'\n\s*\n', '\n', text)
        return text.strip()
    
    def _extract_section_title(self, element) -> Optional[str]:
        """Extract section title from heading or context."""
        # Look for preceding heading
        prev = element.find_previous(['h1', 'h2', 'h3', 'h4'])
        if prev:
            return self._clean_text(prev.get_text())
        
        # Look for heading within parent
        parent = element.find_parent(['section', 'div'])
        if parent:
            heading = parent.find(['h1', 'h2', 'h3', 'h4'], recursive=False)
            if heading:
                return self._clean_text(heading.get_text())
        
        return None
    
    def _determine_chunk_type(self, element, text: str) -> str:
        """Determine chunk type based on content."""
        text_lower = text.lower()
        
        # Check for table element or table-like content
        if element.name == 'table' or element.find_parent('table'):
            if any(kw in text_lower for kw in ['expense', 'nav', 'sip', 'aum', 'fund size']):
                return 'metrics_table'
            return 'table'
        
        # Check for performance data
        if any(kw in text_lower for kw in ['return', 'performance', '1 year', '3 year', '5 year', 'cagr']):
            return 'performance'
        
        # Check for risk/rating
        if any(kw in text_lower for kw in ['risk', 'rating', 'riskometer', 'moderate', 'high', 'low']):
            return 'risk'
        
        # Check for exit load, SIP details
        if any(kw in text_lower for kw in ['exit load', 'minimum sip', 'lock-in', 'redemption']):
            return 'details'
        
        # Check for fund overview/description
        if any(kw in text_lower for kw in ['objective', 'investment strategy', 'about the fund']):
            return 'overview'
        
        return 'general'
    
    def _table_to_text(self, table) -> str:
        """Convert HTML table to readable text format."""
        rows = []
        
        # Get headers
        headers = []
        header_row = table.find('thead')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # Process rows
        for tr in table.find_all('tr'):
            cells = []
            tds = tr.find_all(['td', 'th'])
            
            for i, td in enumerate(tds):
                cell_text = td.get_text(strip=True)
                if header_row and i < len(headers):
                    cells.append(f"{headers[i]}: {cell_text}")
                else:
                    cells.append(cell_text)
            
            if cells:
                rows.append(' | '.join(cells))
        
        return '\n'.join(rows)
    
    def _split_large_text(self, text: str, section_title: Optional[str]) -> List[dict]:
        """
        Split large text into overlapping chunks.
        
        Strategy:
        1. Try to split on paragraph boundaries
        2. If paragraph still too large, split on sentence boundaries
        3. Add overlap between chunks for context
        """
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = []
        current_chars = 0
        
        for sentence in sentences:
            sentence_chars = len(sentence)
            
            # Check if adding this sentence exceeds target
            if current_chars + sentence_chars > self.target_chars and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                if self.min_tokens <= self._estimate_tokens(chunk_text) <= self.max_tokens:
                    chunks.append({
                        'text': chunk_text,
                        'section_title': section_title,
                        'token_count': self._estimate_tokens(chunk_text)
                    })
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences + [sentence]
                current_chars = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_chars += sentence_chars
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_tokens * self.chars_per_token:
                chunks.append({
                    'text': chunk_text,
                    'section_title': section_title,
                    'token_count': self._estimate_tokens(chunk_text)
                })
        
        return chunks
    
    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """Get sentences for overlap based on target overlap size."""
        overlap_chars = 0
        overlap_sentences = []
        
        # Take sentences from the end until we hit overlap target
        for sentence in reversed(sentences):
            if overlap_chars + len(sentence) <= self.overlap_chars:
                overlap_sentences.insert(0, sentence)
                overlap_chars += len(sentence)
            else:
                break
        
        return overlap_sentences
    
    def chunk_html(
        self,
        html_content: str,
        metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Chunk HTML content into semantic pieces.
        
        Args:
            html_content: Cleaned HTML string
            metadata: Dict with scheme_id, scheme_name, amc, source_url, etc.
            
        Returns:
            List of Chunk objects
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        chunks = []
        chunk_index = 0
        
        # Process tables first (preserve as units)
        for table in soup.find_all('table'):
            table_text = self._table_to_text(table)
            
            if not table_text:
                continue
            
            # Determine if table should be split
            token_count = self._estimate_tokens(table_text)
            
            if token_count <= self.max_tokens:
                # Keep table as single chunk
                section_title = self._extract_section_title(table)
                chunk_type = self._determine_chunk_type(table, table_text)
                
                chunk = Chunk(
                    chunk_id=f"{metadata['scheme_id']}_{chunk_index:03d}_{chunk_type}",
                    scheme_id=metadata['scheme_id'],
                    scheme_name=metadata['scheme_name'],
                    amc=metadata['amc'],
                    source_url=metadata['source_url'],
                    source_type=metadata.get('source_type', 'groww_scheme_page'),
                    fetched_at=metadata.get('fetched_at', ''),
                    content_hash=metadata.get('content_hash', ''),
                    chunk_index=chunk_index,
                    section_title=section_title,
                    chunk_type=chunk_type,
                    text=table_text,
                    token_count=token_count
                )
                
                chunks.append(chunk)
                chunk_index += 1
                
                # Remove table from soup to avoid re-processing
                table.decompose()
        
        # Process remaining content by sections
        # Split on headings or large divs
        content_elements = soup.find_all(['section', 'div', 'p', 'article'])
        
        for element in content_elements:
            text = self._clean_text(element.get_text())
            
            if not text or len(text) < self.min_tokens * self.chars_per_token:
                continue
            
            section_title = self._extract_section_title(element)
            chunk_type = self._determine_chunk_type(element, text)
            token_count = self._estimate_tokens(text)
            
            if token_count <= self.max_tokens:
                # Fits in one chunk
                chunk = Chunk(
                    chunk_id=f"{metadata['scheme_id']}_{chunk_index:03d}_{chunk_type}",
                    scheme_id=metadata['scheme_id'],
                    scheme_name=metadata['scheme_name'],
                    amc=metadata['amc'],
                    source_url=metadata['source_url'],
                    source_type=metadata.get('source_type', 'groww_scheme_page'),
                    fetched_at=metadata.get('fetched_at', ''),
                    content_hash=metadata.get('content_hash', ''),
                    chunk_index=chunk_index,
                    section_title=section_title,
                    chunk_type=chunk_type,
                    text=text,
                    token_count=token_count
                )
                
                chunks.append(chunk)
                chunk_index += 1
            else:
                # Split into smaller chunks
                sub_chunks = self._split_large_text(text, section_title)
                
                for sub_chunk in sub_chunks:
                    chunk = Chunk(
                        chunk_id=f"{metadata['scheme_id']}_{chunk_index:03d}_{chunk_type}",
                        scheme_id=metadata['scheme_id'],
                        scheme_name=metadata['scheme_name'],
                        amc=metadata['amc'],
                        source_url=metadata['source_url'],
                        source_type=metadata.get('source_type', 'groww_scheme_page'),
                        fetched_at=metadata.get('fetched_at', ''),
                        content_hash=metadata.get('content_hash', ''),
                        chunk_index=chunk_index,
                        section_title=sub_chunk['section_title'],
                        chunk_type=chunk_type,
                        text=sub_chunk['text'],
                        token_count=sub_chunk['token_count']
                    )
                    
                    chunks.append(chunk)
                    chunk_index += 1
        
        logger.info(
            f"Created {len(chunks)} chunks from {metadata['scheme_id']} "
            f"(avg {sum(c.token_count for c in chunks) // max(len(chunks), 1)} tokens)"
        )
        
        return chunks
    
    def chunk_batch(
        self,
        html_files: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        Chunk multiple HTML files.
        
        Args:
            html_files: List of dicts with 'html_content' and 'metadata'
            
        Returns:
            Combined list of all chunks
        """
        all_chunks = []
        
        for file_info in html_files:
            chunks = self.chunk_html(
                html_content=file_info['html_content'],
                metadata=file_info['metadata']
            )
            all_chunks.extend(chunks)
        
        logger.info(f"Total chunks created: {len(all_chunks)}")
        return all_chunks
