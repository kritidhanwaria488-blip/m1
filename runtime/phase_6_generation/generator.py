"""
Phase 6: Generation Layer

Generates factual answers using Groq API from retrieved context.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

from runtime.phase_5_retrieval.retriever import RetrievedChunk

load_dotenv()

logger = logging.getLogger(__name__)


# System prompt for factual mutual fund assistant
SYSTEM_PROMPT = """You are a factual mutual fund assistant. You answer ONLY objective, 
verifiable questions about mutual fund schemes using the provided context.

RULES:
1. Answer in maximum 3 sentences
2. Include exactly one source citation link (from provided metadata)
3. Add footer: "Last updated from sources: <date>"
4. NEVER provide investment advice or recommendations
5. Use only the CONTEXT; if insufficient, say you cannot find it
6. For advisory questions, refuse politely

Developer instruction: "Use only the CONTEXT; if CONTEXT is insufficient, 
say you cannot find it in the indexed sources and suggest the relevant 
allowlisted scheme URL from metadata if available."

Output format (JSON):
{
  "answer": "Your factual answer (max 3 sentences)",
  "citation_url": "The exact source URL from context",
  "footer": "Last updated from sources: <date>"
}"""


@dataclass
class GenerationResult:
    """Result from LLM generation."""
    answer: str
    citation_url: str
    footer: str
    raw_response: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "citation_url": self.citation_url,
            "footer": self.footer,
            "latency_ms": self.latency_ms,
            "error": self.error
        }


class GroqGenerator:
    """
    LLM answer generator using Groq API.
    
    Model: llama-3.1-8b-instant
    Temperature: 0.1-0.3
    Max tokens: 200
    Timeout: 10 seconds
    """
    
    def __init__(
        self,
        model: str = "llama-3.1-8b-instant",
        temperature: float = 0.2,
        max_tokens: int = 200,
        timeout: int = 10,
        api_key: Optional[str] = None
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required. Set GROQ_API_KEY environment variable.")
        
        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"GroqGenerator initialized (model: {model})")
    
    def _package_context(self, chunks: List[RetrievedChunk]) -> str:
        """
        Package retrieved chunks into context string with source headers.
        
        Format:
        ---
        Source URL: <url>
        Scheme: <name>
        Content: <text>
        ---
        """
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            part = f"""---
Source {i}:
URL: {chunk.source_url}
Scheme: {chunk.scheme_name}
Date: {chunk.fetched_at}
Content: {chunk.text}
---"""
            context_parts.append(part)
        
        return "\n\n".join(context_parts)
    
    def _build_prompt(self, query: str, chunks: List[RetrievedChunk]) -> str:
        """Build the user prompt with query and context."""
        context = self._package_context(chunks)
        
        prompt = f"""USER QUERY: {query}

CONTEXT (retrieved from indexed sources):
{context}

Based on the CONTEXT above, provide a factual answer following the system rules.
Output your response as valid JSON with fields: answer, citation_url, footer."""
        
        return prompt
    
    def generate(
        self,
        query: str,
        chunks: List[RetrievedChunk]
    ) -> GenerationResult:
        """
        Generate answer from query and retrieved chunks.
        
        Args:
            query: User question
            chunks: Retrieved context chunks
        
        Returns:
            GenerationResult with answer, citation, and footer
        """
        import time
        start_time = time.time()
        
        if not chunks:
            logger.warning("No chunks provided for generation")
            return GenerationResult(
                answer="I cannot find information about that in the indexed sources.",
                citation_url="",
                footer="Last updated from sources: N/A",
                error="No context retrieved"
            )
        
        # Build prompt
        user_prompt = self._build_prompt(query, chunks)
        
        # Prepare request
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"}
        }
        
        try:
            logger.info(f"Calling Groq API (model: {self.model})")
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            raw_content = result["choices"][0]["message"]["content"]
            
            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"Groq API responded in {latency_ms:.0f}ms")
            
            # Parse JSON response
            try:
                parsed = json.loads(raw_content)
                return GenerationResult(
                    answer=parsed.get("answer", "").strip(),
                    citation_url=parsed.get("citation_url", "").strip(),
                    footer=parsed.get("footer", "").strip(),
                    raw_response=raw_content,
                    latency_ms=round(latency_ms, 2)
                )
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                # Try to extract from non-JSON response
                return GenerationResult(
                    answer=raw_content[:200],
                    citation_url=chunks[0].source_url if chunks else "",
                    footer=f"Last updated from sources: {chunks[0].fetched_at}" if chunks else "N/A",
                    raw_response=raw_content,
                    latency_ms=round(latency_ms, 2),
                    error=f"JSON parse error: {e}"
                )
                
        except requests.exceptions.Timeout:
            logger.error("Groq API timeout")
            return GenerationResult(
                answer="",
                citation_url="",
                footer="",
                error="API timeout (10s exceeded)"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API error: {e}")
            return GenerationResult(
                answer="",
                citation_url="",
                footer="",
                error=f"API error: {e}"
            )
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return GenerationResult(
                answer="",
                citation_url="",
                footer="",
                error=str(e)
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test generator
    generator = GroqGenerator()
    
    # Create dummy chunks
    test_chunks = [
        RetrievedChunk(
            chunk_id="test_001",
            text="HDFC ELSS Tax Saver has an expense ratio of 1.23%. It is an equity-linked savings scheme.",
            score=0.95,
            source_url="https://www.hdfcfund.com/hdfc-elss-taxsaver",
            scheme_id="hdfc_elss",
            scheme_name="HDFC ELSS Tax Saver",
            amc="HDFC",
            source_type="factsheet",
            fetched_at="2026-04-23",
            chunk_index=0,
            section_title="Overview"
        )
    ]
    
    result = generator.generate("What is the expense ratio of HDFC ELSS?", test_chunks)
    
    print(f"\nAnswer: {result.answer}")
    print(f"Citation: {result.citation_url}")
    print(f"Footer: {result.footer}")
