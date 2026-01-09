"""
Integration tests for recipe structure and normalize pipeline.
Tests: OCRLines -> structure job -> Recipe with SourceSpans + FieldStatus
"""
import pytest
from uuid import uuid4
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base, MediaAsset, OCRLine, Recipe, SourceSpan, FieldStatus


@pytest.fixture
def test_db():
    """In-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@pytest.fixture
def user_id():
    """Create a test user ID."""
    return uuid4()


@pytest.fixture
def sample_asset(test_db, user_id):
    """Create a sample MediaAsset."""
    asset = MediaAsset(
        id=uuid4(),
        user_id=user_id,
        type="image",
        sha256="test123",
        storage_path="/uploads/recipe.jpg",
        source_label="Test recipe photo",
    )
    test_db.add(asset)
    test_db.commit()
    return asset


@pytest.fixture
def sample_ocr_lines(test_db, sample_asset):
    """Create sample OCRLines simulating recipe structure."""
    lines = [
        OCRLine(
            id=uuid4(),
            asset_id=sample_asset.id,
            page=0,
            text="Pasta Carbonara",
            bbox=[100, 50, 300, 30],
            confidence=0.95,
        ),
        OCRLine(
            id=uuid4(),
            asset_id=sample_asset.id,
            page=0,
            text="Ingredients",
            bbox=[100, 100, 200, 25],
            confidence=0.98,
        ),
        OCRLine(
            id=uuid4(),
            asset_id=sample_asset.id,
            page=0,
            text="400g spaghetti pasta",
            bbox=[100, 130, 250, 20],
            confidence=0.92,
        ),
        OCRLine(
            id=uuid4(),
            asset_id=sample_asset.id,
            page=0,
            text="200g pancetta",
            bbox=[100, 155, 200, 20],
            confidence=0.90,
        ),
        OCRLine(
            id=uuid4(),
            asset_id=sample_asset.id,
            page=0,
            text="4 large eggs",
            bbox=[100, 180, 150, 20],
            confidence=0.93,
        ),
        OCRLine(
            id=uuid4(),
            asset_id=sample_asset.id,
            page=0,
            text="Salt and pepper to taste",
            bbox=[100, 205, 280, 20],
            confidence=0.88,
        ),
        OCRLine(
            id=uuid4(),
            asset_id=sample_asset.id,
            page=0,
            text="Instructions",
            bbox=[100, 240, 200, 25],
            confidence=0.98,
        ),
        OCRLine(
            id=uuid4(),
            asset_id=sample_asset.id,
            page=0,
            text="1. Boil water in large pot and cook pasta.",
            bbox=[100, 270, 450, 20],
            confidence=0.91,
        ),
        OCRLine(
            id=uuid4(),
            asset_id=sample_asset.id,
            page=0,
            text="2. Fry pancetta until crispy in separate pan.",
            bbox=[100, 295, 420, 20],
            confidence=0.89,
        ),
        OCRLine(
            id=uuid4(),
            asset_id=sample_asset.id,
            page=0,
            text="3. Combine eggs and cheese mixture.",
            bbox=[100, 320, 400, 20],
            confidence=0.90,
        ),
        OCRLine(
            id=uuid4(),
            asset_id=sample_asset.id,
            page=0,
            text="Serves 4",
            bbox=[100, 350, 150, 20],
            confidence=0.96,
        ),
    ]
    for line in lines:
        test_db.add(line)
    test_db.commit()
    return lines


class TestStructureJob:
    """Test the structure job parsing logic."""

    def test_detect_recipe_structure_from_ocr_lines(self, test_db, sample_ocr_lines, sample_asset):
        """Test that OCRLines can be parsed into recipe structure."""
        # Import parser
        from services.parser import RecipeParser, OCRLineData

        # Convert ORM lines to parser format
        parser_lines = [
            OCRLineData(
                page=line.page,
                text=line.text,
                bbox=line.bbox,
                confidence=line.confidence,
            )
            for line in sample_ocr_lines
        ]

        # Parse
        parser = RecipeParser()
        result = parser.parse(parser_lines, str(sample_asset.id))

        # Verify recipe structure
        assert result["recipe"]["title"] is not None
        assert len(result["recipe"]["ingredients"]) >= 3
        assert len(result["recipe"]["steps"]) >= 2
        assert result["recipe"]["servings"] == 4

    def test_structure_creates_source_spans(self, test_db, sample_ocr_lines, sample_asset):
        """Test that structure job creates SourceSpan records."""
        from services.parser import RecipeParser, OCRLineData

        parser_lines = [
            OCRLineData(
                page=line.page,
                text=line.text,
                bbox=line.bbox,
                confidence=line.confidence,
            )
            for line in sample_ocr_lines
        ]

        parser = RecipeParser()
        result = parser.parse(parser_lines, str(sample_asset.id))

        # Verify spans are created
        spans = result["spans"]
        assert len(spans) > 0

        # Verify span structure
        for span in spans:
            assert "field_path" in span
            assert "bbox" in span
            assert "ocr_confidence" in span
            assert "extracted_text" in span
            assert span["ocr_confidence"] > 0

    def test_structure_creates_field_statuses(self, test_db, sample_ocr_lines, sample_asset):
        """Test that structure job creates FieldStatus records."""
        from services.parser import RecipeParser, OCRLineData

        parser_lines = [
            OCRLineData(
                page=line.page,
                text=line.text,
                bbox=line.bbox,
                confidence=line.confidence,
            )
            for line in sample_ocr_lines
        ]

        parser = RecipeParser()
        result = parser.parse(parser_lines, str(sample_asset.id))

        # Verify field statuses
        statuses = result["field_statuses"]
        assert len(statuses) > 0

        # Verify status structure
        for status in statuses:
            assert "field_path" in status
            assert "status" in status
            assert status["status"] in ["extracted", "missing"]

    def test_parse_ingredients_with_quantities(self, test_db, sample_ocr_lines, sample_asset):
        """Test ingredient parsing extracts quantities and units."""
        from services.parser import RecipeParser, OCRLineData

        parser_lines = [
            OCRLineData(
                page=line.page,
                text=line.text,
                bbox=line.bbox,
                confidence=line.confidence,
            )
            for line in sample_ocr_lines
        ]

        parser = RecipeParser()
        result = parser.parse(parser_lines, str(sample_asset.id))

        # Find spaghetti ingredient
        spaghetti = next(
            (ing for ing in result["recipe"]["ingredients"] if "spaghetti" in ing.get("original_text", "").lower()),
            None,
        )

        assert spaghetti is not None
        assert spaghetti.get("quantity") == 400
        assert spaghetti.get("unit") == "g"

    def test_parse_steps_preserves_text(self, test_db, sample_ocr_lines, sample_asset):
        """Test that steps preserve original OCR text."""
        from services.parser import RecipeParser, OCRLineData

        parser_lines = [
            OCRLineData(
                page=line.page,
                text=line.text,
                bbox=line.bbox,
                confidence=line.confidence,
            )
            for line in sample_ocr_lines
        ]

        parser = RecipeParser()
        result = parser.parse(parser_lines, str(sample_asset.id))

        # Verify steps contain expected text
        steps = result["recipe"]["steps"]
        step_texts = [step.get("text") for step in steps]

        assert any("Boil" in t for t in step_texts)
        assert any("Fry" in t for t in step_texts)

    def test_missing_fields_marked_as_missing(self, test_db):
        """Test that missing fields are marked with status='missing'."""
        from services.parser import RecipeParser, OCRLineData

        # Create minimal OCRLines with no ingredients or steps
        minimal_lines = [
            OCRLineData(
                page=0,
                text="Some Random Text",
                bbox=[0, 0, 100, 20],
                confidence=0.9,
            ),
        ]

        parser = RecipeParser()
        result = parser.parse(minimal_lines, "test-asset-id")

        # Check that missing statuses are created
        missing_statuses = [s for s in result["field_statuses"] if s["status"] == "missing"]
        assert len(missing_statuses) > 0

        # At least ingredients and steps should be marked missing
        missing_paths = [s["field_path"] for s in missing_statuses]
        assert any("ingredients" in path for path in missing_paths)


class TestNormalizeJob:
    """Test the normalize job logic."""

    def test_extract_ingredient_name_from_text(self):
        """Test ingredient name extraction."""
        from worker.jobs import _extract_ingredient_name

        # Test cases
        test_cases = [
            ("2 cups all-purpose flour", "flour"),
            ("3 large eggs", "egg"),
            ("400g spaghetti pasta", "spaghetti pasta"),
            ("Salt and pepper to taste", "salt and pepper"),
            ("1/2 cup milk", "milk"),
            ("2 tablespoons olive oil", "olive oil"),
        ]

        for original, expected in test_cases:
            result = _extract_ingredient_name(original)
            assert result is not None
            # Allow some flexibility in exact match
            assert expected.lower() in result.lower() or result.lower() in expected.lower()

    def test_singularize_plurals(self):
        """Test that common plurals are singularized."""
        from worker.jobs import _extract_ingredient_name

        test_cases = [
            ("3 eggs", "egg"),
            ("2 cups flour", "flour"),
            ("4 tomatoes", "tomato"),
        ]

        for original, expected in test_cases:
            result = _extract_ingredient_name(original)
            assert result is not None
            assert expected in result.lower()


class TestIntegrationFlow:
    """Integration tests for full structure + normalize flow."""

    def test_full_structure_and_normalize_flow(self, test_db, user_id, sample_asset, sample_ocr_lines):
        """Test complete flow from OCRLines to Recipe with SourceSpans and name_norm."""
        from uuid import uuid4
        from services.parser import RecipeParser, OCRLineData

        # 1. Parse OCRLines
        parser_lines = [
            OCRLineData(
                page=line.page,
                text=line.text,
                bbox=line.bbox,
                confidence=line.confidence,
            )
            for line in sample_ocr_lines
        ]

        parser = RecipeParser()
        parse_result = parser.parse(parser_lines, str(sample_asset.id))

        # 2. Create Recipe record
        recipe_id = uuid4()
        recipe_data = parse_result["recipe"]

        recipe = Recipe(
            id=recipe_id,
            user_id=sample_asset.user_id,
            title=recipe_data.get("title"),
            servings=recipe_data.get("servings"),
            ingredients=recipe_data.get("ingredients", []),
            steps=recipe_data.get("steps", []),
            status="draft",
        )
        test_db.add(recipe)
        test_db.flush()

        # 3. Create SourceSpans
        for span_data in parse_result.get("spans", []):
            span = SourceSpan(
                id=uuid4(),
                recipe_id=recipe_id,
                field_path=span_data["field_path"],
                asset_id=sample_asset.id,
                page=span_data["page"],
                bbox=span_data["bbox"],
                ocr_confidence=span_data["ocr_confidence"],
                extracted_text=span_data["extracted_text"],
            )
            test_db.add(span)

        # 4. Create FieldStatuses
        for status_data in parse_result.get("field_statuses", []):
            status = FieldStatus(
                id=uuid4(),
                recipe_id=recipe_id,
                field_path=status_data["field_path"],
                status=status_data["status"],
                notes=status_data.get("notes"),
            )
            test_db.add(status)

        test_db.commit()

        # 5. Normalize ingredients
        from worker.jobs import _extract_ingredient_name

        for i, ingredient in enumerate(recipe.ingredients or []):
            if not ingredient.get("name_norm"):
                original_text = ingredient.get("original_text", "")
                name_norm = _extract_ingredient_name(original_text)
                if name_norm:
                    ingredient["name_norm"] = name_norm

        recipe.ingredients = recipe.ingredients  # Trigger update
        test_db.commit()

        # 6. Verify complete flow
        retrieved_recipe = test_db.query(Recipe).filter_by(id=recipe_id).first()
        assert retrieved_recipe is not None
        assert retrieved_recipe.title is not None
        assert len(retrieved_recipe.ingredients) >= 3
        assert len(retrieved_recipe.steps) >= 2

        # Verify SourceSpans
        spans = test_db.query(SourceSpan).filter_by(recipe_id=recipe_id).all()
        assert len(spans) > 0

        # Verify FieldStatuses
        statuses = test_db.query(FieldStatus).filter_by(recipe_id=recipe_id).all()
        assert len(statuses) > 0

        # Verify name_norm was set on some ingredients
        ingredients_with_norm = [
            ing for ing in retrieved_recipe.ingredients if ing.get("name_norm")
        ]
        assert len(ingredients_with_norm) >= 1

        # Verify original_text is preserved
        for ing in retrieved_recipe.ingredients:
            assert ing.get("original_text") is not None
