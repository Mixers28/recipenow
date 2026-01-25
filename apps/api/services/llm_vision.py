"""
LLM Vision service for structured recipe extraction using vision LLM fallback.

Uses Ollama + LLaVA-7B for offline vision-based text reading from recipe media.
Serves as fallback when OCR extraction is insufficient (missing critical fields).

Design principles:
- Vision reader, not inference engine (reads visible text from media, not guesses)
- Offline-first (Ollama + LLaVA) with optional cloud fallback (Claude 3 Haiku, GPT-4V)
- Triggered only when critical fields missing after deterministic OCR parsing
- All extractions tagged with source_method="llm-vision" for audit trail
"""

import json
import logging
import os
from io import BytesIO
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class LLMVisionService:
    """
    Vision-based recipe field extraction using LLM.
    
    Reads visible text from recipe media (images/PDFs) to fill missing critical fields
    when OCR extraction is insufficient. Not for inference or guessing.
    
    Configuration:
    - OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)
    - OLLAMA_MODEL: LLaVA model identifier (default: llava:7b)
    - LLM_FALLBACK_ENABLED: Enable fallback extraction (default: true)
    - LLM_FALLBACK_PROVIDER: Cloud provider if Ollama unavailable (claude|openai)
    - LLM_FALLBACK_API_KEY: API key for cloud provider fallback
    """
    
    # Structured extraction prompt - requests reading visible text, not inference
    EXTRACTION_PROMPT = """You are a recipe data extractor. Your task is to READ VISIBLE TEXT from this recipe image and extract structured data.

IMPORTANT: Only extract visible text that you can read from the image. Do NOT guess, infer, or make up values.

Extract the following fields if visible in the image:
1. title: The recipe name/title if visible
2. ingredients: List of ingredients with quantities if visible (format as array)
3. steps: Cooking/preparation steps if visible (format as array)
4. servings: Number of servings if visible
5. prep_time: Preparation time if visible
6. cook_time: Cooking time if visible
7. total_time: Total time if visible
8. cuisine: Cuisine type if visible
9. dietary_notes: Any dietary restrictions/notes if visible

Return ONLY a JSON object with these fields. Only include fields where you can clearly read the text from the image.
If a field is not visible or readable, omit it from the response.

Response format:
{
    "title": "...",
    "ingredients": ["...", "..."],
    "steps": ["...", "..."],
    "servings": "...",
    ...
}
"""

    def __init__(
        self,
        ollama_host: Optional[str] = None,
        ollama_model: Optional[str] = None,
        enable_fallback: bool = True,
        fallback_provider: Optional[str] = None,
        fallback_api_key: Optional[str] = None,
    ):
        """
        Initialize LLM Vision service.
        
        Args:
            ollama_host: Ollama server URL
            ollama_model: Model identifier for Ollama
            enable_fallback: Enable cloud provider fallback
            fallback_provider: Cloud provider ("claude" or "openai")
            fallback_api_key: API key for cloud provider
        """
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", "llava:7b")
        self.enable_fallback = enable_fallback and os.getenv("LLM_FALLBACK_ENABLED", "true").lower() == "true"
        self.fallback_provider = fallback_provider or os.getenv("LLM_FALLBACK_PROVIDER")
        self.fallback_api_key = fallback_api_key or os.getenv("LLM_FALLBACK_API_KEY")
        
        logger.info(
            f"LLMVisionService initialized: ollama_host={self.ollama_host}, "
            f"model={self.ollama_model}, fallback_enabled={self.enable_fallback}"
        )
    
    def extract_recipe_from_image(self, image_data: bytes) -> dict:
        """
        Extract recipe structure from image using vision LLM.
        
        Attempts Ollama first, falls back to cloud provider if configured and Ollama unavailable.
        
        Args:
            image_data: Binary image data (JPEG, PNG, etc.)
        
        Returns:
            Dict with extracted fields: title, ingredients, steps, servings, times, etc.
            Only includes fields that were clearly readable from image.
        
        Raises:
            Exception: If all extraction methods fail
        """
        # Try Ollama first
        try:
            logger.debug(f"Attempting Ollama extraction using {self.ollama_model}")
            return self._extract_via_ollama(image_data)
        except Exception as e:
            logger.warning(f"Ollama extraction failed: {e}")
            
            if not self.enable_fallback:
                logger.error("Ollama failed and fallback disabled")
                raise
            
            # Try cloud fallback
            if self.fallback_provider == "claude":
                try:
                    logger.debug("Falling back to Claude 3 Haiku vision")
                    return self._extract_via_claude(image_data)
                except Exception as e2:
                    logger.error(f"Claude fallback also failed: {e2}")
                    raise
            
            elif self.fallback_provider == "openai":
                try:
                    logger.debug("Falling back to GPT-4 Vision")
                    return self._extract_via_openai(image_data)
                except Exception as e2:
                    logger.error(f"OpenAI fallback also failed: {e2}")
                    raise
            
            else:
                logger.error(f"No fallback provider configured; Ollama failed")
                raise
    
    def _extract_via_ollama(self, image_data: bytes) -> dict:
        """
        Extract recipe using Ollama + LLaVA.
        
        Args:
            image_data: Binary image data
        
        Returns:
            Extracted recipe fields dict
        
        Raises:
            Exception: If Ollama request fails
        """
        import base64
        
        # Encode image as base64 for Ollama API
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        
        ollama_payload = {
            "model": self.ollama_model,
            "prompt": self.EXTRACTION_PROMPT,
            "images": [image_b64],
            "stream": False,
        }
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.ollama_host}/api/generate",
                    json=ollama_payload,
                )
                response.raise_for_status()
        
            ollama_result = response.json()
            response_text = ollama_result.get("response", "")
            
            logger.debug(f"Ollama response (first 500 chars): {response_text[:500]}")
            
            # Extract JSON from response
            extracted = self._parse_json_response(response_text)
            logger.info(f"Ollama extraction successful: {list(extracted.keys())}")
            return extracted
        
        except httpx.ConnectError as e:
            logger.warning(f"Ollama connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama extraction error: {e}", exc_info=True)
            raise
    
    def _extract_via_claude(self, image_data: bytes) -> dict:
        """
        Extract recipe using Claude 3 Haiku vision (cloud fallback).
        
        Requires ANTHROPIC_API_KEY environment variable.
        
        Args:
            image_data: Binary image data
        
        Returns:
            Extracted recipe fields dict
        
        Raises:
            Exception: If Claude API request fails or no API key configured
        """
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("Claude fallback requires 'anthropic' package")
        
        if not self.fallback_api_key:
            raise RuntimeError("Claude fallback requires LLM_FALLBACK_API_KEY")
        
        import base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        
        client = anthropic.Anthropic(api_key=self.fallback_api_key)
        
        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": self.EXTRACTION_PROMPT,
                            },
                        ],
                    }
                ],
            )
            
            response_text = response.content[0].text
            logger.debug(f"Claude response (first 500 chars): {response_text[:500]}")
            
            extracted = self._parse_json_response(response_text)
            logger.info(f"Claude extraction successful: {list(extracted.keys())}")
            return extracted
        
        except Exception as e:
            logger.error(f"Claude extraction error: {e}", exc_info=True)
            raise
    
    def _extract_via_openai(self, image_data: bytes) -> dict:
        """
        Extract recipe using GPT-4 Vision (cloud fallback).
        
        Requires OPENAI_API_KEY environment variable.
        
        Args:
            image_data: Binary image data
        
        Returns:
            Extracted recipe fields dict
        
        Raises:
            Exception: If OpenAI API request fails or no API key configured
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("OpenAI fallback requires 'openai' package")
        
        if not self.fallback_api_key:
            raise RuntimeError("OpenAI fallback requires LLM_FALLBACK_API_KEY")
        
        import base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        
        client = OpenAI(api_key=self.fallback_api_key)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}",
                                },
                            },
                            {
                                "type": "text",
                                "text": self.EXTRACTION_PROMPT,
                            },
                        ],
                    }
                ],
            )
            
            response_text = response.choices[0].message.content
            logger.debug(f"OpenAI response (first 500 chars): {response_text[:500]}")
            
            extracted = self._parse_json_response(response_text)
            logger.info(f"OpenAI extraction successful: {list(extracted.keys())}")
            return extracted
        
        except Exception as e:
            logger.error(f"OpenAI extraction error: {e}", exc_info=True)
            raise
    
    @staticmethod
    def _parse_json_response(response_text: str) -> dict:
        """
        Extract JSON object from LLM response text.
        
        Handles responses with surrounding text by finding JSON block.
        
        Args:
            response_text: Raw response from LLM
        
        Returns:
            Parsed JSON dict
        
        Raises:
            ValueError: If no valid JSON found
        """
        # Try direct JSON parse first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Look for JSON block in response
        import re
        
        json_pattern = r"\{[^{}]*\}"
        match = re.search(json_pattern, response_text, re.DOTALL)
        
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
        logger.error(f"Could not parse JSON from response: {response_text[:200]}")
        raise ValueError(f"No valid JSON found in LLM response")


def get_llm_vision_service() -> LLMVisionService:
    """Factory function to get LLM Vision service instance."""
    return LLMVisionService()
