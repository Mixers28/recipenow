/**
 * API client for RecipeNow backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

export interface Recipe {
  id: string
  user_id: string
  title?: string
  servings?: number
  ingredients?: Ingredient[]
  steps?: Step[]
  tags?: string[]
  nutrition?: Nutrition
  status: 'draft' | 'needs_review' | 'verified'
  created_at?: string
  updated_at?: string
}

export interface Ingredient {
  id?: string
  original_text: string
  name_norm?: string
  quantity?: number
  unit?: string
  optional?: boolean
}

export interface Step {
  id?: string
  text: string
}

export interface Nutrition {
  calories?: number
  estimated?: boolean
  approved_by_user?: boolean
}

export interface SourceSpan {
  id: string
  recipe_id: string
  field_path: string
  asset_id: string
  page: number
  bbox: [number, number, number, number] // [x, y, w, h]
  ocr_confidence: number
  extracted_text: string
  created_at?: string
}

export interface FieldStatus {
  id: string
  recipe_id: string
  field_path: string
  status: 'missing' | 'extracted' | 'user_entered' | 'verified'
  notes?: string
  created_at?: string
}

export interface RecipeListResponse {
  recipes: Recipe[]
  total: number
  skip: number
  limit: number
}

export interface VerifyResponse {
  recipe_id: string
  status: string
  errors: string[]
}

// Recipe endpoints
export async function listRecipes(
  userId: string,
  options?: {
    query?: string
    status?: string
    tags?: string[]
    skip?: number
    limit?: number
  }
): Promise<RecipeListResponse> {
  const params = new URLSearchParams({
    user_id: userId,
    skip: String(options?.skip || 0),
    limit: String(options?.limit || 50),
  })

  if (options?.query) params.append('query', options.query)
  if (options?.status) params.append('status', options.status)
  if (options?.tags?.length) params.append('tags', options.tags.join(','))

  const res = await fetch(`${API_BASE}/recipes?${params}`, {
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to list recipes: ${res.statusText}`)
  return res.json()
}

export async function getRecipe(userId: string, recipeId: string): Promise<Recipe> {
  const res = await fetch(`${API_BASE}/recipes/${recipeId}?user_id=${userId}`, {
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to get recipe: ${res.statusText}`)
  return res.json()
}

export async function createRecipe(userId: string, data: Partial<Recipe>): Promise<Recipe> {
  const res = await fetch(`${API_BASE}/recipes?user_id=${userId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

  if (!res.ok) throw new Error(`Failed to create recipe: ${res.statusText}`)
  return res.json()
}

export async function updateRecipe(
  userId: string,
  recipeId: string,
  data: Partial<Recipe>
): Promise<Recipe> {
  const res = await fetch(`${API_BASE}/recipes/${recipeId}?user_id=${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

  if (!res.ok) throw new Error(`Failed to update recipe: ${res.statusText}`)
  return res.json()
}

export async function deleteRecipe(userId: string, recipeId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/recipes/${recipeId}?user_id=${userId}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to delete recipe: ${res.statusText}`)
}

export async function verifyRecipe(userId: string, recipeId: string): Promise<VerifyResponse> {
  const res = await fetch(`${API_BASE}/recipes/${recipeId}/verify?user_id=${userId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to verify recipe: ${res.statusText}`)
  return res.json()
}

// SourceSpan endpoints
export async function listSpans(userId: string, recipeId: string): Promise<SourceSpan[]> {
  const res = await fetch(`${API_BASE}/recipes/${recipeId}/spans?user_id=${userId}`, {
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to list spans: ${res.statusText}`)
  return res.json()
}

export async function createSpan(
  userId: string,
  recipeId: string,
  span: Omit<SourceSpan, 'id' | 'recipe_id' | 'created_at'>
): Promise<SourceSpan> {
  const res = await fetch(`${API_BASE}/recipes/${recipeId}/spans?user_id=${userId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(span),
  })

  if (!res.ok) throw new Error(`Failed to create span: ${res.statusText}`)
  return res.json()
}

export async function deleteSpan(
  userId: string,
  recipeId: string,
  spanId: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/recipes/${recipeId}/spans/${spanId}?user_id=${userId}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to delete span: ${res.statusText}`)
}

// FieldStatus endpoints
export async function listFieldStatuses(userId: string, recipeId: string): Promise<FieldStatus[]> {
  const res = await fetch(`${API_BASE}/recipes/${recipeId}/field-status?user_id=${userId}`, {
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to list field statuses: ${res.statusText}`)
  return res.json()
}

// Asset endpoints (for image retrieval)
export async function getAsset(assetId: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/assets/${assetId}`)

  if (!res.ok) throw new Error(`Failed to get asset: ${res.statusText}`)
  return res.blob()
}

// Pantry interfaces
export interface PantryItem {
  id: string
  user_id: string
  name_original: string
  name_norm: string
  quantity?: number
  unit?: string
  created_at?: string
}

export interface PantryListResponse {
  items: PantryItem[]
  total: number
  skip: number
  limit: number
}

export interface PantryItemRequest {
  name_original: string
  quantity?: number
  unit?: string
}

// Pantry endpoints
export async function listPantryItems(
  userId: string,
  options?: {
    query?: string
    skip?: number
    limit?: number
  }
): Promise<PantryListResponse> {
  const params = new URLSearchParams({
    user_id: userId,
    skip: String(options?.skip || 0),
    limit: String(options?.limit || 100),
  })

  if (options?.query) params.append('query', options.query)

  const res = await fetch(`${API_BASE}/pantry?${params}`, {
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to list pantry items: ${res.statusText}`)
  return res.json()
}

export async function createPantryItem(
  userId: string,
  item: PantryItemRequest
): Promise<PantryItem> {
  const params = new URLSearchParams({ user_id: userId })

  const res = await fetch(`${API_BASE}/pantry/items?${params}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(item),
  })

  if (!res.ok) throw new Error(`Failed to create pantry item: ${res.statusText}`)
  return res.json()
}

export async function getPantryItem(userId: string, itemId: string): Promise<PantryItem> {
  const params = new URLSearchParams({ user_id: userId })

  const res = await fetch(`${API_BASE}/pantry/items/${itemId}?${params}`, {
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to get pantry item: ${res.statusText}`)
  return res.json()
}

export async function updatePantryItem(
  userId: string,
  itemId: string,
  item: PantryItemRequest
): Promise<PantryItem> {
  const params = new URLSearchParams({ user_id: userId })

  const res = await fetch(`${API_BASE}/pantry/items/${itemId}?${params}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(item),
  })

  if (!res.ok) throw new Error(`Failed to update pantry item: ${res.statusText}`)
  return res.json()
}

export async function deletePantryItem(userId: string, itemId: string): Promise<void> {
  const params = new URLSearchParams({ user_id: userId })

  const res = await fetch(`${API_BASE}/pantry/items/${itemId}?${params}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to delete pantry item: ${res.statusText}`)
}

// Match interfaces
export interface IngredientMatch {
  original_text: string
  name_norm: string
  quantity?: number
  unit?: string
  found: boolean
}

export interface RecipeMatchResult {
  recipe_id: string
  recipe_title: string
  match_percentage: number
  total_ingredients: number
  matched_ingredients: number
  ingredient_matches: IngredientMatch[]
  missing_ingredients: IngredientMatch[]
}

export interface RecipeMatchListResponse {
  recipes: RecipeMatchResult[]
  total: number
}

export interface ShoppingListItem {
  original_text: string
  name_norm: string
  total_quantity: number
  unit?: string
  count: number
  recipes: string[]
}

export interface ShoppingListResponse {
  recipe_count: number
  missing_items: ShoppingListItem[]
  total_missing: number
}

// Match endpoints
export async function matchRecipe(userId: string, recipeId: string): Promise<RecipeMatchResult> {
  const params = new URLSearchParams({ user_id: userId })

  const res = await fetch(`${API_BASE}/match/recipe/${recipeId}?${params}`, {
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to match recipe: ${res.statusText}`)
  return res.json()
}

export async function matchAllRecipes(
  userId: string,
  options?: {
    status?: string
    min_match?: number
  }
): Promise<RecipeMatchListResponse> {
  const params = new URLSearchParams({ user_id: userId })

  if (options?.status) params.append('status', options.status)
  if (options?.min_match !== undefined) params.append('min_match', String(options.min_match))

  const res = await fetch(`${API_BASE}/match/all?${params}`, {
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to match recipes: ${res.statusText}`)
  return res.json()
}

export async function generateShoppingList(
  userId: string,
  recipeIds?: string[]
): Promise<ShoppingListResponse> {
  const params = new URLSearchParams({ user_id: userId })

  if (recipeIds?.length) {
    params.append('recipe_ids', recipeIds.join(','))
  }

  const res = await fetch(`${API_BASE}/match/shopping-list?${params}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })

  if (!res.ok) throw new Error(`Failed to generate shopping list: ${res.statusText}`)
  return res.json()
}
