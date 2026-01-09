"""
Unit tests for SQLAlchemy ORM models (CRUD operations).
Tests Recipe and SourceSpan with user_id isolation.
"""
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base, FieldStatus, MediaAsset, OCRLine, Recipe, SourceSpan


@pytest.fixture
def test_db():
    """In-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@pytest.fixture
def user_ids():
    """Create test user IDs."""
    return {
        "user1": uuid4(),
        "user2": uuid4(),
    }


@pytest.fixture
def sample_asset(test_db, user_ids):
    """Create a sample MediaAsset."""
    asset = MediaAsset(
        id=uuid4(),
        user_id=user_ids["user1"],
        type="image",
        sha256="abc123def456",
        storage_path="/uploads/recipe1.jpg",
        source_label="Cookbook photo",
    )
    test_db.add(asset)
    test_db.commit()
    return asset


@pytest.fixture
def sample_ocr_line(test_db, sample_asset):
    """Create a sample OCRLine."""
    line = OCRLine(
        id=uuid4(),
        asset_id=sample_asset.id,
        page=0,
        text="2 cups flour",
        bbox=[100, 200, 150, 30],
        confidence=0.95,
    )
    test_db.add(line)
    test_db.commit()
    return line


class TestRecipeCRUD:
    """Test Recipe CRUD operations with user isolation."""

    def test_create_recipe(self, test_db, user_ids):
        """Test creating a recipe."""
        recipe = Recipe(
            id=uuid4(),
            user_id=user_ids["user1"],
            title="Pasta Carbonara",
            servings=4,
            status="draft",
            ingredients=[
                {
                    "original_text": "400g pasta",
                    "name_norm": "pasta",
                    "quantity": 400,
                    "unit": "g",
                }
            ],
            steps=[{"text": "Boil water"}],
            tags=["italian", "pasta"],
        )
        test_db.add(recipe)
        test_db.commit()

        assert recipe.id is not None
        assert recipe.title == "Pasta Carbonara"
        assert recipe.status == "draft"
        assert len(recipe.ingredients) == 1
        assert recipe.created_at is not None
        assert recipe.updated_at is not None

    def test_read_recipe(self, test_db, user_ids):
        """Test reading a recipe by ID."""
        recipe_id = uuid4()
        recipe = Recipe(
            id=recipe_id,
            user_id=user_ids["user1"],
            title="Pasta Carbonara",
            servings=4,
        )
        test_db.add(recipe)
        test_db.commit()

        retrieved = test_db.query(Recipe).filter_by(id=recipe_id).first()
        assert retrieved is not None
        assert retrieved.title == "Pasta Carbonara"
        assert retrieved.user_id == user_ids["user1"]

    def test_update_recipe(self, test_db, user_ids):
        """Test updating a recipe."""
        recipe_id = uuid4()
        recipe = Recipe(
            id=recipe_id,
            user_id=user_ids["user1"],
            title="Original Title",
            status="draft",
        )
        test_db.add(recipe)
        test_db.commit()

        # Update
        recipe.title = "Updated Title"
        recipe.status = "needs_review"
        test_db.commit()

        retrieved = test_db.query(Recipe).filter_by(id=recipe_id).first()
        assert retrieved.title == "Updated Title"
        assert retrieved.status == "needs_review"
        assert retrieved.updated_at > recipe.created_at

    def test_soft_delete_recipe(self, test_db, user_ids):
        """Test soft deleting a recipe."""
        recipe_id = uuid4()
        recipe = Recipe(
            id=recipe_id,
            user_id=user_ids["user1"],
            title="To Delete",
        )
        test_db.add(recipe)
        test_db.commit()

        # Soft delete
        recipe.deleted_at = datetime.utcnow()
        test_db.commit()

        retrieved = test_db.query(Recipe).filter_by(id=recipe_id).first()
        assert retrieved.deleted_at is not None

        # Should not appear in active list
        active_recipes = test_db.query(Recipe).filter_by(
            user_id=user_ids["user1"], deleted_at=None
        ).all()
        assert len(active_recipes) == 0

    def test_user_isolation(self, test_db, user_ids):
        """Test that recipes are isolated per user."""
        recipe1_id = uuid4()
        recipe1 = Recipe(
            id=recipe1_id,
            user_id=user_ids["user1"],
            title="User 1 Recipe",
        )
        recipe2_id = uuid4()
        recipe2 = Recipe(
            id=recipe2_id,
            user_id=user_ids["user2"],
            title="User 2 Recipe",
        )
        test_db.add(recipe1)
        test_db.add(recipe2)
        test_db.commit()

        user1_recipes = test_db.query(Recipe).filter_by(user_id=user_ids["user1"]).all()
        user2_recipes = test_db.query(Recipe).filter_by(user_id=user_ids["user2"]).all()

        assert len(user1_recipes) == 1
        assert user1_recipes[0].title == "User 1 Recipe"
        assert len(user2_recipes) == 1
        assert user2_recipes[0].title == "User 2 Recipe"

    def test_list_recipes_by_status(self, test_db, user_ids):
        """Test filtering recipes by status."""
        draft_recipe = Recipe(
            id=uuid4(),
            user_id=user_ids["user1"],
            title="Draft Recipe",
            status="draft",
        )
        verified_recipe = Recipe(
            id=uuid4(),
            user_id=user_ids["user1"],
            title="Verified Recipe",
            status="verified",
        )
        test_db.add(draft_recipe)
        test_db.add(verified_recipe)
        test_db.commit()

        drafts = test_db.query(Recipe).filter_by(
            user_id=user_ids["user1"], status="draft"
        ).all()
        assert len(drafts) == 1
        assert drafts[0].title == "Draft Recipe"

        verified = test_db.query(Recipe).filter_by(
            user_id=user_ids["user1"], status="verified"
        ).all()
        assert len(verified) == 1
        assert verified[0].title == "Verified Recipe"


class TestSourceSpanCRUD:
    """Test SourceSpan CRUD operations (provenance tracking)."""

    def test_create_source_span(self, test_db, user_ids, sample_asset):
        """Test creating a source span (provenance link)."""
        recipe_id = uuid4()
        recipe = Recipe(
            id=recipe_id,
            user_id=user_ids["user1"],
            title="Test Recipe",
        )
        test_db.add(recipe)
        test_db.commit()

        span = SourceSpan(
            id=uuid4(),
            recipe_id=recipe_id,
            field_path="title",
            asset_id=sample_asset.id,
            page=0,
            bbox=[100, 200, 200, 50],
            ocr_confidence=0.92,
            extracted_text="Test Recipe",
        )
        test_db.add(span)
        test_db.commit()

        assert span.id is not None
        assert span.field_path == "title"
        assert span.ocr_confidence == 0.92
        assert span.created_at is not None

    def test_read_source_span(self, test_db, user_ids, sample_asset):
        """Test reading a source span."""
        recipe_id = uuid4()
        recipe = Recipe(
            id=recipe_id,
            user_id=user_ids["user1"],
            title="Test Recipe",
        )
        test_db.add(recipe)
        test_db.commit()

        span_id = uuid4()
        span = SourceSpan(
            id=span_id,
            recipe_id=recipe_id,
            field_path="ingredients[0].original_text",
            asset_id=sample_asset.id,
            page=0,
            bbox=[100, 300, 200, 40],
            ocr_confidence=0.88,
            extracted_text="2 cups flour",
        )
        test_db.add(span)
        test_db.commit()

        retrieved = test_db.query(SourceSpan).filter_by(id=span_id).first()
        assert retrieved is not None
        assert retrieved.field_path == "ingredients[0].original_text"
        assert retrieved.extracted_text == "2 cups flour"

    def test_list_spans_for_recipe(self, test_db, user_ids, sample_asset):
        """Test listing all spans for a recipe."""
        recipe_id = uuid4()
        recipe = Recipe(
            id=recipe_id,
            user_id=user_ids["user1"],
            title="Test Recipe",
        )
        test_db.add(recipe)
        test_db.commit()

        # Create multiple spans
        span1 = SourceSpan(
            id=uuid4(),
            recipe_id=recipe_id,
            field_path="title",
            asset_id=sample_asset.id,
            page=0,
            bbox=[100, 200, 200, 50],
            ocr_confidence=0.95,
            extracted_text="Test Recipe",
        )
        span2 = SourceSpan(
            id=uuid4(),
            recipe_id=recipe_id,
            field_path="ingredients[0].original_text",
            asset_id=sample_asset.id,
            page=0,
            bbox=[100, 300, 200, 40],
            ocr_confidence=0.88,
            extracted_text="2 cups flour",
        )
        test_db.add(span1)
        test_db.add(span2)
        test_db.commit()

        spans = test_db.query(SourceSpan).filter_by(recipe_id=recipe_id).all()
        assert len(spans) == 2
        assert set(s.field_path for s in spans) == {"title", "ingredients[0].original_text"}

    def test_delete_spans_cascade(self, test_db, user_ids, sample_asset):
        """Test that deleting a recipe cascades to delete spans."""
        recipe_id = uuid4()
        recipe = Recipe(
            id=recipe_id,
            user_id=user_ids["user1"],
            title="Test Recipe",
        )
        test_db.add(recipe)
        test_db.commit()

        span = SourceSpan(
            id=uuid4(),
            recipe_id=recipe_id,
            field_path="title",
            asset_id=sample_asset.id,
            page=0,
            bbox=[100, 200, 200, 50],
            ocr_confidence=0.95,
            extracted_text="Test Recipe",
        )
        test_db.add(span)
        test_db.commit()

        # Verify span exists
        spans_before = test_db.query(SourceSpan).filter_by(recipe_id=recipe_id).all()
        assert len(spans_before) == 1

        # Delete recipe
        test_db.delete(recipe)
        test_db.commit()

        # Verify spans are deleted too
        spans_after = test_db.query(SourceSpan).filter_by(recipe_id=recipe_id).all()
        assert len(spans_after) == 0


class TestFieldStatusCRUD:
    """Test FieldStatus CRUD operations."""

    def test_create_field_status(self, test_db, user_ids):
        """Test creating a field status badge."""
        recipe_id = uuid4()
        recipe = Recipe(
            id=recipe_id,
            user_id=user_ids["user1"],
            title="Test Recipe",
        )
        test_db.add(recipe)
        test_db.commit()

        status = FieldStatus(
            id=uuid4(),
            recipe_id=recipe_id,
            field_path="title",
            status="extracted",
            notes="Extracted from OCR",
        )
        test_db.add(status)
        test_db.commit()

        assert status.status == "extracted"
        assert status.notes == "Extracted from OCR"

    def test_list_field_statuses_for_recipe(self, test_db, user_ids):
        """Test listing all field statuses for a recipe."""
        recipe_id = uuid4()
        recipe = Recipe(
            id=recipe_id,
            user_id=user_ids["user1"],
            title="Test Recipe",
        )
        test_db.add(recipe)
        test_db.commit()

        statuses = [
            FieldStatus(
                id=uuid4(),
                recipe_id=recipe_id,
                field_path="title",
                status="extracted",
            ),
            FieldStatus(
                id=uuid4(),
                recipe_id=recipe_id,
                field_path="servings",
                status="missing",
            ),
            FieldStatus(
                id=uuid4(),
                recipe_id=recipe_id,
                field_path="ingredients[0].original_text",
                status="user_entered",
            ),
        ]
        for s in statuses:
            test_db.add(s)
        test_db.commit()

        retrieved = test_db.query(FieldStatus).filter_by(recipe_id=recipe_id).all()
        assert len(retrieved) == 3
        assert set(s.status for s in retrieved) == {"extracted", "missing", "user_entered"}


class TestIntegration:
    """Integration tests: Recipe + SourceSpan + FieldStatus."""

    def test_full_recipe_workflow(self, test_db, user_ids, sample_asset):
        """Test complete recipe creation with provenance and field status."""
        recipe_id = uuid4()

        # 1. Create recipe
        recipe = Recipe(
            id=recipe_id,
            user_id=user_ids["user1"],
            title="Pasta Carbonara",
            servings=4,
            status="draft",
            ingredients=[
                {
                    "original_text": "400g pasta",
                    "name_norm": "pasta",
                    "quantity": 400,
                    "unit": "g",
                }
            ],
            steps=[{"text": "Boil water"}],
        )
        test_db.add(recipe)
        test_db.commit()

        # 2. Add provenance spans
        title_span = SourceSpan(
            id=uuid4(),
            recipe_id=recipe_id,
            field_path="title",
            asset_id=sample_asset.id,
            page=0,
            bbox=[100, 200, 200, 50],
            ocr_confidence=0.95,
            extracted_text="Pasta Carbonara",
        )
        ingredient_span = SourceSpan(
            id=uuid4(),
            recipe_id=recipe_id,
            field_path="ingredients[0].original_text",
            asset_id=sample_asset.id,
            page=0,
            bbox=[100, 300, 200, 40],
            ocr_confidence=0.88,
            extracted_text="400g pasta",
        )
        test_db.add(title_span)
        test_db.add(ingredient_span)
        test_db.commit()

        # 3. Add field statuses
        title_status = FieldStatus(
            id=uuid4(),
            recipe_id=recipe_id,
            field_path="title",
            status="extracted",
        )
        servings_status = FieldStatus(
            id=uuid4(),
            recipe_id=recipe_id,
            field_path="servings",
            status="extracted",
        )
        test_db.add(title_status)
        test_db.add(servings_status)
        test_db.commit()

        # 4. Verify everything is connected
        recipe_check = test_db.query(Recipe).filter_by(id=recipe_id).first()
        spans_check = test_db.query(SourceSpan).filter_by(recipe_id=recipe_id).all()
        statuses_check = test_db.query(FieldStatus).filter_by(recipe_id=recipe_id).all()

        assert recipe_check.title == "Pasta Carbonara"
        assert len(spans_check) == 2
        assert len(statuses_check) == 2

        # 5. Verify user isolation
        other_user_recipes = test_db.query(Recipe).filter_by(
            user_id=user_ids["user2"]
        ).all()
        assert len(other_user_recipes) == 0
