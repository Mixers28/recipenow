"""
Vision API service for structured recipe extraction (vision-primary).

Uses OpenAI vision models as the primary extractor while OCR supplies
line IDs + bboxes for provenance. The model must return strict JSON
with evidence_ocr_line_ids for each extracted field.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMVisionService:
    """
    Vision-based recipe field extraction using OpenAI.

    Reads visible text from recipe media and references OCR line IDs as evidence.

    Configuration:
    - VISION_MODEL: OpenAI model identifier (default: gpt-4o-mini)
    - VISION_MAX_OUTPUT_TOKENS: max tokens (default: 1024)
    - VISION_STRICT_JSON: enforce strict JSON (default: true)
    - VISION_RETRY_COUNT: retries per provider (default: 1)
    - OPENAI_API_KEY: OpenAI API key
    """

    BASE_PROMPT = (
        "You are a recipe data extractor. READ VISIBLE TEXT from the image. "
        "Do NOT guess or infer missing values. Use OCR line IDs as evidence."
    )

    def __init__(
        self,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        strict_json: Optional[bool] = None,
        retry_count: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        self.model = model or os.getenv("VISION_MODEL", "gpt-4o-mini")
        self.max_tokens = max_tokens or int(os.getenv("VISION_MAX_OUTPUT_TOKENS", "2048"))
        self.strict_json = (
            strict_json
            if strict_json is not None
            else os.getenv("VISION_STRICT_JSON", "true").lower() == "true"
        )
        self.retry_count = retry_count or int(os.getenv("VISION_RETRY_COUNT", "1"))
        self.max_ocr_lines = int(os.getenv("VISION_MAX_OCR_LINES", "400"))

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for vision extraction")

        logger.info(
            "Vision service initialized: provider=openai model=%s strict_json=%s",
            self.model,
            self.strict_json,
        )

    def extract_with_evidence(self, image_data: bytes, ocr_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract recipe structure with OCR evidence IDs.

        Args:
            image_data: Binary image bytes
            ocr_lines: List of OCR line dicts with id/text/page
        Returns:
            Normalized extraction dict following SPEC.md
        """
        prompt = self._build_prompt(ocr_lines)
        response_text = self._extract_via_openai(image_data, prompt)
        parsed = self._parse_json_response(response_text)
        return self._normalize_vision_result(parsed)

    def extract_recipe_from_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        Backwards-compatible wrapper: extract without OCR evidence payload.
        """
        return self.extract_with_evidence(image_data, [])

    def _build_prompt(self, ocr_lines: List[Dict[str, Any]]) -> str:
        lines = ocr_lines[: self.max_ocr_lines]
        ocr_payload = [
            {"id": str(line.get("id")), "text": line.get("text"), "page": line.get("page", 0)}
            for line in lines
        ]
        ocr_json = json.dumps(ocr_payload, ensure_ascii=True)

        schema = (
            "Return ONLY JSON in this exact shape. Use evidence_ocr_line_ids for all fields:\n"
            "{\n"
            "  \"title\": { \"text\": \"...\", \"evidence_ocr_line_ids\": [\"...\"], \"confidence\": 0.0 },\n"
            "  \"ingredients\": [\n"
            "    { \"text\": \"...\", \"evidence_ocr_line_ids\": [\"...\"], \"confidence\": 0.0 }\n"
            "  ],\n"
            "  \"steps\": [\n"
            "    { \"text\": \"...\", \"evidence_ocr_line_ids\": [\"...\"], \"confidence\": 0.0 }\n"
            "  ],\n"
            "  \"servings\": { \"value\": 4, \"evidence_ocr_line_ids\": [\"...\"], \"confidence\": 0.0, \"is_estimate\": false },\n"
            "  \"servings_estimate\": { \"value\": 4, \"confidence\": 0.0, \"basis\": \"...\", \"is_estimate\": true },\n"
            "  \"times\": {\n"
            "    \"prep_min\": { \"value\": 10, \"evidence_ocr_line_ids\": [\"...\"], \"confidence\": 0.0 },\n"
            "    \"cook_min\": { \"value\": 20, \"evidence_ocr_line_ids\": [\"...\"], \"confidence\": 0.0 }\n"
            "  },\n"
            "  \"unreadable_regions\": [{ \"note\": \"...\" }]\n"
            "}\n"
            "If a field is not visible, return null for that field or omit it."
        )

        return (
            f"{self.BASE_PROMPT}\n\n"
            f"OCR_LINES_JSON={ocr_json}\n\n"
            f"{schema}"
        )

    def _extract_via_openai(self, image_data: bytes, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("OpenAI provider requires 'openai' package")

        import base64

        image_b64 = base64.b64encode(image_data).decode("utf-8")
        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
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
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return response.choices[0].message.content

    @staticmethod
    def _parse_json_response(response_text: str) -> dict:
        import re

        # Try direct parse first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Extract JSON block from markdown or surrounding text
        json_pattern = r"\{[\s\S]*\}"
        match = re.search(json_pattern, response_text)
        if match:
            json_str = match.group()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try fixing common issues
                json_str = LLMVisionService._fix_json_string(json_str)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

        raise ValueError("No valid JSON found in vision response")

    @staticmethod
    def _fix_json_string(json_str: str) -> str:
        """Attempt to fix common JSON formatting issues from LLM responses."""
        import re

        # Remove trailing commas before ] or }
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        # Fix unescaped quotes inside strings (common LLM issue)
        # This is a simplified fix - replace smart quotes with regular quotes
        json_str = json_str.replace('"', '"').replace('"', '"')
        json_str = json_str.replace(''', "'").replace(''', "'")

        # Remove any control characters except newlines and tabs
        json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', json_str)

        # Try to fix truncated JSON by closing brackets
        open_braces = json_str.count('{') - json_str.count('}')
        open_brackets = json_str.count('[') - json_str.count(']')

        if open_braces > 0 or open_brackets > 0:
            # Remove any trailing partial content after last complete value
            # Look for last complete string or number
            last_good = max(
                json_str.rfind('",'),
                json_str.rfind('"]'),
                json_str.rfind('"}'),
                json_str.rfind('null'),
                json_str.rfind('true'),
                json_str.rfind('false'),
            )
            if last_good > 0:
                # Find end of that value
                if json_str[last_good:last_good+2] == '",':
                    json_str = json_str[:last_good+2]
                elif json_str[last_good:last_good+2] in ['"]', '"}']:
                    json_str = json_str[:last_good+2]

            # Close any unclosed brackets
            json_str += ']' * open_brackets + '}' * open_braces

        return json_str

    @staticmethod
    def _normalize_vision_result(data: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}

        def normalize_item(item: Any) -> Dict[str, Any]:
            if isinstance(item, str):
                return {"text": item, "evidence_ocr_line_ids": [], "confidence": None}
            if isinstance(item, dict):
                return {
                    "text": item.get("text") or item.get("value") or "",
                    "evidence_ocr_line_ids": item.get("evidence_ocr_line_ids") or [],
                    "confidence": item.get("confidence"),
                }
            return {"text": "", "evidence_ocr_line_ids": [], "confidence": None}

        title = data.get("title")
        if title is not None:
            normalized["title"] = normalize_item(title)

        ingredients = data.get("ingredients") or []
        normalized["ingredients"] = [normalize_item(item) for item in ingredients]

        steps = data.get("steps") or []
        normalized["steps"] = [normalize_item(item) for item in steps]

        servings = data.get("servings")
        if servings is not None:
            if isinstance(servings, dict):
                value = servings.get("value")
                if isinstance(value, str) and value.isdigit():
                    value = int(value)
                normalized["servings"] = {
                    "value": value,
                    "evidence_ocr_line_ids": servings.get("evidence_ocr_line_ids") or [],
                    "confidence": servings.get("confidence"),
                    "is_estimate": bool(servings.get("is_estimate", False)),
                }
            else:
                normalized["servings"] = {
                    "value": servings,
                    "evidence_ocr_line_ids": [],
                    "confidence": None,
                    "is_estimate": False,
                }

        servings_estimate = data.get("servings_estimate")
        if servings_estimate is not None and isinstance(servings_estimate, dict):
            normalized["servings_estimate"] = {
                "value": servings_estimate.get("value"),
                "confidence": servings_estimate.get("confidence"),
                "basis": servings_estimate.get("basis"),
                "is_estimate": True,
            }

        times = data.get("times") or {}
        if isinstance(times, dict):
            normalized_times: Dict[str, Any] = {}
            for key in ["prep_min", "cook_min", "total_min"]:
                entry = times.get(key)
                if entry is None:
                    continue
                if isinstance(entry, dict):
                    normalized_times[key] = {
                        "value": entry.get("value"),
                        "evidence_ocr_line_ids": entry.get("evidence_ocr_line_ids") or [],
                        "confidence": entry.get("confidence"),
                    }
                else:
                    normalized_times[key] = {
                        "value": entry,
                        "evidence_ocr_line_ids": [],
                        "confidence": None,
                    }
            normalized["times"] = normalized_times

        if data.get("unreadable_regions") is not None:
            normalized["unreadable_regions"] = data.get("unreadable_regions")

        return normalized


def get_llm_vision_service() -> LLMVisionService:
    """Factory function to get vision service instance."""
    return LLMVisionService()
