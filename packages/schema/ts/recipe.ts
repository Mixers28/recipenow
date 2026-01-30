/**
 * RecipeNow Type Definitions (V1) — Matches Pydantic models
 * All user-scoped entities include userId for multi-user support
 */

export type FieldStatusType = "missing" | "extracted" | "user_entered" | "verified";
export type RecipeStatus = "draft" | "needs_review" | "verified";
export type MediaAssetType = "image" | "pdf";

export interface Times {
  prep_min?: number;
  cook_min?: number;
  total_min?: number;
}

export interface Nutrition {
  calories?: number;
  estimated: boolean;
  approved_by_user: boolean;
}

export interface ServingsEstimate {
  value?: number;
  confidence?: number;
  basis?: string;
  approved_by_user: boolean;
}

export interface Ingredient {
  id?: string;
  original_text: string;
  name_norm?: string;
  quantity?: number;
  unit?: string;
  optional?: boolean;
}

export interface Step {
  id?: string;
  text: string;
}

export interface Recipe {
  id?: string;
  userId: string;
  title?: string;
  servings?: number;
  servings_estimate?: ServingsEstimate;
  times?: Times;
  ingredients: Ingredient[];
  steps: Step[];
  tags: string[];
  nutrition?: Nutrition;
  status: RecipeStatus;
  created_at?: string;
  updated_at?: string;
  deleted_at?: string;
}

export interface MediaAsset {
  id?: string;
  userId: string;
  type: MediaAssetType;
  sha256: string;
  storage_path: string;
  source_label?: string;
  created_at?: string;
}

export interface OCRLine {
  id?: string;
  asset_id: string;
  page: number;
  text: string;
  bbox: number[];
  confidence: number;
  created_at?: string;
}

export interface SourceSpan {
  id?: string;
  recipe_id: string;
  field_path: string;
  asset_id: string;
  page: number;
  bbox: number[];
  ocr_confidence: number;
  extracted_text?: string;
  source_method?: "ocr" | "vision-api" | "user";
  evidence?: Record<string, unknown>;
  created_at?: string;
}

export interface FieldStatus {
  id?: string;
  recipe_id: string;
  field_path: string;
  status: FieldStatusType;
  notes?: string;
}

export interface PantryItem {
  id?: string;
  userId: string;
  name_original: string;
  name_norm: string;
  quantity?: number;
  unit?: string;
  created_at?: string;
}
