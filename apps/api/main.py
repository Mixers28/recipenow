from fastapi import FastAPI

from routers import assets, match, pantry, recipes, shopping_list

app = FastAPI(title="RecipeNow API", version="0.1.0")

app.include_router(assets.router, prefix="/assets", tags=["assets"])
app.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
app.include_router(pantry.router, prefix="/pantry", tags=["pantry"])
app.include_router(match.router, prefix="/match", tags=["match"])
app.include_router(shopping_list.router, prefix="/shopping-list", tags=["shopping-list"])


@app.get("/")
def health_check() -> dict:
    return {"status": "ok", "version": "0.1.0"}
