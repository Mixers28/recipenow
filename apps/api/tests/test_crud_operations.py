"""
Integration tests for Recipe CRUD operations and repository layer.
Tests user isolation, field updates, and verification logic.
"""
import pytest
from uuid import uuid4
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base, Recipe, SourceSpan, FieldStatus, PantryItem
from repositories.recipes import RecipeRepository
from repositories.spans import SourceSpanRepository
from repositories.pantry import PantryRepository


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


class TestRecipeRepository:
    """Test RecipeRepository CRUD operations."""

    def test_create_recipe(self, test_db, user_ids):
        """Test creating a recipe."""
        repo = RecipeRepository(test_db)

        recipe = repo.create(
            user_id=user_ids["user1"],
            title="Pasta Carbonara",
            servings=4,
            ingredients=[
                {"original_text": "400g spaghetti", "quantity": 400, "unit": "g"},
                {"original_text": "200g pancetta", "quantity": 200, "unit": "g"},
            ],
            steps=[
                {"text": "Boil water and cook pasta"},
                {"text": "Fry pancetta until crispy"},
            ],
            tags=["italian", "pasta"],
        )

        assert recipe.id is not None
        assert recipe.title == "Pasta Carbonara"
        assert recipe.servings == 4
        assert len(recipe.ingredients) == 2
        assert len(recipe.steps) == 2
        assert recipe.status == "draft"

    def test_get_by_id_user_isolation(self, test_db, user_ids):
        """Test that get_by_id enforces user isolation."""
        repo = RecipeRepository(test_db)

        recipe = repo.create(
            user_id=user_ids["user1"],
            title="User 1 Recipe",
        )

        # User 1 can access their recipe
        result = repo.get_by_id(user_ids["user1"], recipe.id)
        assert result is not None
        assert result.title == "User 1 Recipe"

        # User 2 cannot access User 1's recipe
        result = repo.get_by_id(user_ids["user2"], recipe.id)
        assert result is None

    def test_get_all_with_filters(self, test_db, user_ids):
        """Test get_all with status and tag filters."""
        repo = RecipeRepository(test_db)

        # Create recipes with different statuses
        draft = repo.create(
            user_id=user_ids["user1"],
            title="Draft Recipe",
            status="draft",
            tags=["italian"],
        )
        verified = repo.create(
            user_id=user_ids["user1"],
            title="Verified Recipe",
            status="verified",
            tags=["italian"],
        )
        other_tag = repo.create(
            user_id=user_ids["user1"],
            title="Asian Recipe",
            status="draft",
            tags=["asian"],
        )

        # Filter by status
        drafts, total = repo.get_all(user_ids["user1"], status="draft")
        assert total == 2
        assert any(r.title == "Draft Recipe" for r in drafts)

        verified_recipes, total = repo.get_all(user_ids["user1"], status="verified")
        assert total == 1
        assert verified_recipes[0].title == "Verified Recipe"

        # Filter by tag
        italian_recipes, total = repo.get_all(user_ids["user1"], tags=["italian"])
        assert total == 2

    def test_get_all_search(self, test_db, user_ids):
        """Test get_all with search query."""
        repo = RecipeRepository(test_db)

        repo.create(user_id=user_ids["user1"], title="Pasta Carbonara")
        repo.create(user_id=user_ids["user1"], title="Pasta Marinara")
        repo.create(user_id=user_ids["user1"], title="Chicken Teriyaki")

        results, total = repo.get_all(user_ids["user1"], query="pasta")
        assert total == 2
        assert all("pasta" in r.title.lower() for r in results)

    def test_update_recipe(self, test_db, user_ids):
        """Test updating a recipe."""
        repo = RecipeRepository(test_db)

        recipe = repo.create(
            user_id=user_ids["user1"],
            title="Original Title",
            servings=2,
        )

        updated = repo.update(
            user_id=user_ids["user1"],
            recipe_id=recipe.id,
            title="Updated Title",
            servings=6,
        )

        assert updated.title == "Updated Title"
        assert updated.servings == 6

    def test_delete_recipe_soft_delete(self, test_db, user_ids):
        """Test soft delete recipe."""
        repo = RecipeRepository(test_db)

        recipe = repo.create(
            user_id=user_ids["user1"],
            title="To Delete",
        )

        deleted = repo.delete(user_ids["user1"], recipe.id)
        assert deleted is True

        # Recipe should be soft-deleted (deleted_at set)
        result = repo.get_by_id(user_ids["user1"], recipe.id)
        # get_all filters out deleted recipes by default
        recipes, _ = repo.get_all(user_ids["user1"])
        assert len(recipes) == 0

    def test_verify_recipe_validation(self, test_db, user_ids):
        """Test recipe verification with validation."""
        repo = RecipeRepository(test_db)

        # Recipe without title, ingredients, steps
        incomplete = repo.create(user_id=user_ids["user1"])
        result = repo.verify(user_ids["user1"], incomplete.id)
        assert result is None  # Verification failed

        # Recipe with all required fields
        complete = repo.create(
            user_id=user_ids["user1"],
            title="Complete Recipe",
            ingredients=[{"original_text": "flour"}],
            steps=[{"text": "Mix"}],
        )
        result = repo.verify(user_ids["user1"], complete.id)
        assert result is not None
        assert result.status == "verified"


class TestSourceSpanRepository:
    """Test SourceSpanRepository operations."""

    def test_create_span(self, test_db, user_ids):
        """Test creating a SourceSpan."""
        recipe_repo = RecipeRepository(test_db)
        span_repo = SourceSpanRepository(test_db)

        recipe = recipe_repo.create(user_id=user_ids["user1"], title="Test Recipe")
        asset_id = uuid4()

        span = span_repo.create(
            recipe_id=recipe.id,
            field_path="title",
            asset_id=asset_id,
            page=0,
            bbox=[100, 200, 300, 50],
            ocr_confidence=0.95,
            extracted_text="Test Recipe",
        )

        assert span.id is not None
        assert span.field_path == "title"
        assert span.ocr_confidence == 0.95

    def test_get_by_recipe(self, test_db, user_ids):
        """Test getting spans for a recipe."""
        recipe_repo = RecipeRepository(test_db)
        span_repo = SourceSpanRepository(test_db)

        recipe = recipe_repo.create(user_id=user_ids["user1"], title="Test Recipe")
        asset_id = uuid4()

        # Create multiple spans
        span_repo.create(
            recipe_id=recipe.id,
            field_path="title",
            asset_id=asset_id,
            page=0,
            bbox=[100, 200, 300, 50],
            ocr_confidence=0.95,
            extracted_text="Test Recipe",
        )
        span_repo.create(
            recipe_id=recipe.id,
            field_path="ingredients[0].original_text",
            asset_id=asset_id,
            page=0,
            bbox=[100, 300, 250, 40],
            ocr_confidence=0.90,
            extracted_text="flour",
        )

        spans = span_repo.get_by_recipe(recipe.id)
        assert len(spans) == 2

    def test_get_by_field(self, test_db, user_ids):
        """Test getting spans by field path."""
        recipe_repo = RecipeRepository(test_db)
        span_repo = SourceSpanRepository(test_db)

        recipe = recipe_repo.create(user_id=user_ids["user1"], title="Test Recipe")
        asset_id = uuid4()

        # Create spans for multiple indices of ingredients
        span_repo.create(
            recipe_id=recipe.id,
            field_path="ingredients[0].original_text",
            asset_id=asset_id,
            page=0,
            bbox=[100, 300, 250, 40],
            ocr_confidence=0.90,
            extracted_text="flour",
        )
        span_repo.create(
            recipe_id=recipe.id,
            field_path="ingredients[1].original_text",
            asset_id=asset_id,
            page=0,
            bbox=[100, 350, 250, 40],
            ocr_confidence=0.88,
            extracted_text="sugar",
        )

        spans = span_repo.get_by_field(recipe.id, "ingredients[0].original_text")
        assert len(spans) == 1
        assert spans[0].extracted_text == "flour"

    def test_delete_span(self, test_db, user_ids):
        """Test deleting a SourceSpan."""
        recipe_repo = RecipeRepository(test_db)
        span_repo = SourceSpanRepository(test_db)

        recipe = recipe_repo.create(user_id=user_ids["user1"], title="Test Recipe")
        asset_id = uuid4()

        span = span_repo.create(
            recipe_id=recipe.id,
            field_path="title",
            asset_id=asset_id,
            page=0,
            bbox=[100, 200, 300, 50],
            ocr_confidence=0.95,
            extracted_text="Test Recipe",
        )

        deleted = span_repo.delete(span.id)
        assert deleted is True

        # Verify span is deleted
        result = span_repo.get_by_id(span.id)
        assert result is None

    def test_delete_for_field(self, test_db, user_ids):
        """Test deleting all spans for a field."""
        recipe_repo = RecipeRepository(test_db)
        span_repo = SourceSpanRepository(test_db)

        recipe = recipe_repo.create(user_id=user_ids["user1"], title="Test Recipe")
        asset_id = uuid4()

        # Create multiple versions of same field (shouldn't happen normally, but test cleanup)
        for i in range(3):
            span_repo.create(
                recipe_id=recipe.id,
                field_path="title",
                asset_id=asset_id,
                page=0,
                bbox=[100 + i * 10, 200, 300, 50],
                ocr_confidence=0.95,
                extracted_text="Test Recipe",
            )

        # Delete all spans for title field
        deleted_count = span_repo.delete_for_field(recipe.id, "title")
        assert deleted_count == 3

        # Verify all deleted
        spans = span_repo.get_by_field(recipe.id, "title")
        assert len(spans) == 0


class TestPantryRepository:
    """Test PantryRepository operations."""

    def test_create_item(self, test_db, user_ids):
        """Test creating a pantry item."""
        repo = PantryRepository(test_db)

        item = repo.create(
            user_id=user_ids["user1"],
            name_original="2 cups flour",
            name_norm="flour",
            quantity=2,
            unit="cups",
        )

        assert item.id is not None
        assert item.name_original == "2 cups flour"
        assert item.name_norm == "flour"

    def test_get_all_user_isolation(self, test_db, user_ids):
        """Test that get_all enforces user isolation."""
        repo = PantryRepository(test_db)

        repo.create(user_id=user_ids["user1"], name_original="flour", name_norm="flour")
        repo.create(user_id=user_ids["user1"], name_original="sugar", name_norm="sugar")
        repo.create(user_id=user_ids["user2"], name_original="salt", name_norm="salt")

        user1_items, total1 = repo.get_all(user_ids["user1"])
        assert total1 == 2
        assert all(item.user_id == user_ids["user1"] for item in user1_items)

        user2_items, total2 = repo.get_all(user_ids["user2"])
        assert total2 == 1
        assert user2_items[0].name_norm == "salt"

    def test_search_by_name(self, test_db, user_ids):
        """Test searching pantry items by name."""
        repo = PantryRepository(test_db)

        repo.create(user_id=user_ids["user1"], name_original="all-purpose flour", name_norm="flour")
        repo.create(user_id=user_ids["user1"], name_original="whole wheat flour", name_norm="flour")
        repo.create(user_id=user_ids["user1"], name_original="sugar", name_norm="sugar")

        results = repo.search_by_name(user_ids["user1"], "flour")
        assert len(results) == 2

    def test_update_item(self, test_db, user_ids):
        """Test updating a pantry item."""
        repo = PantryRepository(test_db)

        item = repo.create(
            user_id=user_ids["user1"],
            name_original="flour",
            name_norm="flour",
            quantity=1,
            unit="cup",
        )

        updated = repo.update(
            user_id=user_ids["user1"],
            item_id=item.id,
            quantity=2,
            unit="cups",
        )

        assert updated.quantity == 2
        assert updated.unit == "cups"

    def test_delete_item(self, test_db, user_ids):
        """Test deleting a pantry item."""
        repo = PantryRepository(test_db)

        item = repo.create(
            user_id=user_ids["user1"],
            name_original="flour",
            name_norm="flour",
        )

        deleted = repo.delete(user_ids["user1"], item.id)
        assert deleted is True

        # Verify deleted
        result = repo.get_by_id(user_ids["user1"], item.id)
        assert result is None


class TestIntegrationRecipeCRUD:
    """Integration tests for complete Recipe CRUD flows."""

    def test_full_recipe_creation_and_verification_flow(self, test_db, user_ids):
        """Test creating a recipe, adding spans, and verifying."""
        recipe_repo = RecipeRepository(test_db)
        span_repo = SourceSpanRepository(test_db)

        # 1. Create recipe
        recipe = recipe_repo.create(
            user_id=user_ids["user1"],
            title="Pasta Carbonara",
            servings=4,
            ingredients=[
                {"original_text": "400g spaghetti", "quantity": 400, "unit": "g"},
                {"original_text": "200g pancetta", "quantity": 200, "unit": "g"},
            ],
            steps=[
                {"text": "Boil water and cook pasta"},
                {"text": "Fry pancetta until crispy"},
            ],
        )

        # 2. Add SourceSpans
        asset_id = uuid4()
        span_repo.create(
            recipe_id=recipe.id,
            field_path="title",
            asset_id=asset_id,
            page=0,
            bbox=[100, 200, 300, 50],
            ocr_confidence=0.95,
            extracted_text="Pasta Carbonara",
        )

        # 3. Verify recipe
        verified = recipe_repo.verify(user_ids["user1"], recipe.id)
        assert verified is not None
        assert verified.status == "verified"

        # 4. Confirm spans are preserved
        spans = span_repo.get_by_recipe(recipe.id)
        assert len(spans) == 1

    def test_update_recipe_field_status_tracking(self, test_db, user_ids):
        """Test that updating fields maintains FieldStatus tracking."""
        recipe_repo = RecipeRepository(test_db)

        recipe = recipe_repo.create(
            user_id=user_ids["user1"],
            title="Original Title",
            ingredients=[{"original_text": "flour"}],
        )

        # Update title
        updated = recipe_repo.update(
            user_id=user_ids["user1"],
            recipe_id=recipe.id,
            title="Updated Title",
        )

        assert updated.title == "Updated Title"
