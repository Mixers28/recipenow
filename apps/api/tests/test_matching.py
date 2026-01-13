"""
Tests for pantry matching logic.
"""
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base
from repositories.pantry import PantryRepository
from repositories.recipes import RecipeRepository
from services.matching import RecipeMatchingService


def test_match_recipe_required_only():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    user_id = uuid4()
    recipe_repo = RecipeRepository(db)
    pantry_repo = PantryRepository(db)

    recipe = recipe_repo.create(
        user_id=user_id,
        title="Match Test",
        ingredients=[
            {"original_text": "2 cups flour", "name_norm": "flour"},
            {"original_text": "1 tsp salt", "name_norm": "salt", "optional": True},
            {"original_text": "1 cup sugar", "name_norm": "sugar"},
        ],
        steps=[{"text": "Mix"}],
    )

    pantry_repo.create(user_id=user_id, name_original="Flour", name_norm="flour")

    service = RecipeMatchingService(db)
    match = service.match_recipe(user_id, recipe.id)

    assert match is not None
    assert match.total_ingredients == 2  # required only
    assert match.matched_ingredients == 1
    assert match.match_percentage == 50.0


def test_match_recipe_fallback_to_original_text():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    user_id = uuid4()
    recipe_repo = RecipeRepository(db)
    pantry_repo = PantryRepository(db)

    recipe = recipe_repo.create(
        user_id=user_id,
        title="Fallback Test",
        ingredients=[
            {"original_text": "1 cup sugar"},
        ],
        steps=[{"text": "Mix"}],
    )

    pantry_repo.create(user_id=user_id, name_original="Sugar", name_norm="sugar")

    service = RecipeMatchingService(db)
    match = service.match_recipe(user_id, recipe.id)

    assert match is not None
    assert match.match_percentage == 100.0
