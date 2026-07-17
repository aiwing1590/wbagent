import io
import json
import os
from typing import Optional

import pandas as pd
import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI


# ============================================================
# РќРђРЎРўР РћР™РљР RENDER
# ============================================================

APP_PASSWORD = os.getenv("APP_PASSWORD", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
DATABASE_URL = os.getenv("DATABASE_URL", "")

FRONTEND_ORIGIN = os.getenv(
    "FRONTEND_ORIGIN",
    "https://wbnew-two.vercel.app",
).rstrip("/")

MAX_FILE_SIZE_MB = int(
    os.getenv("MAX_FILE_SIZE_MB", "15")
)

MAX_FILE_SIZE_BYTES = (
    MAX_FILE_SIZE_MB * 1024 * 1024
)

MAX_QUERY_LENGTH = 1000
ALLOWED_EXTENSIONS = {".xlsx", ".xls"}


# ============================================================
# РџР РР›РћР–Р•РќРР•
# ============================================================

app = FastAPI(
    title="WB AI Agent API",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_ORIGIN,
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

openai_client: Optional[AsyncOpenAI] = None

if OPENAI_API_KEY:
    openai_client = AsyncOpenAI(
        api_key=OPENAI_API_KEY
    )


# ============================================================
# РћР‘Р©РР• Р¤РЈРќРљР¦РР
# ============================================================

def check_password(app_password: str) -> None:
    if not APP_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail=(
                "РќР° СЃРµСЂРІРµСЂРµ РЅРµ РЅР°СЃС‚СЂРѕРµРЅР° "
                "РїРµСЂРµРјРµРЅРЅР°СЏ APP_PASSWORD"
            ),
        )

    if app_password != APP_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="РќРµРІРµСЂРЅС‹Р№ РїР°СЂРѕР»СЊ",
        )


def clean_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:
    cleaned_df = df.copy()

    cleaned_df.columns = [
        str(column).strip()
        for column in cleaned_df.columns
    ]

    return cleaned_df


def safe_numeric_column(
    df: pd.DataFrame,
    column_name: str,
) -> pd.Series:
    if column_name not in df.columns:
        return pd.Series(
            0.0,
            index=df.index,
            dtype="float64",
        )

    series = (
        df[column_name]
        .astype(str)
        .str.strip()
        .str.replace("\u00a0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace("в‚Ѕ", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    return pd.to_numeric(
        series,
        errors="coerce",
    ).fillna(0.0)


def numeric_sum(
    df: pd.DataFrame,
    column_name: str,
    absolute: bool = False,
) -> float:
    values = safe_numeric_column(
        df,
        column_name,
    )

    if absolute:
        values = values.abs()

    return round(
        float(values.sum()),
        2,
    )


def first_existing_column(
    df: pd.DataFrame,
    possible_columns: list[str],
) -> Optional[str]:
    for column_name in possible_columns:
        if column_name in df.columns:
            return column_name

    return None


def get_revenue_series(
    df: pd.DataFrame,
) -> pd.Series:
    revenue_column = first_existing_column(
        df,
        [
            "Р’Р°Р»РѕРІР°СЏ РІС‹СЂСѓС‡РєР°",
            "Р’С‹СЂСѓС‡РєР° РїРѕ Р·Р°РєР°Р·Р°Рј",
            "РЎСѓРјРјР° РїСЂРѕРґР°Р¶",
            "РЎСѓРјРјР° СЂРµР°Р»РёР·Р°С†РёРё",
        ],
    )

    if not revenue_column:
        return pd.Series(
            0.0,
            index=df.index,
            dtype="float64",
        )

    return safe_numeric_column(
        df,
        revenue_column,
    )


def build_expense_series(
    df: pd.DataFrame,
) -> dict[str, pd.Series]:
    expenses = {}

    if "РљРѕРјРёСЃСЃРёСЏ, СЌРєРІР°Р№СЂРёРЅРі" in df.columns:
        expenses["РљРѕРјРёСЃСЃРёСЏ Рё СЌРєРІР°Р№СЂРёРЅРі"] = (
            safe_numeric_column(
                df,
                "РљРѕРјРёСЃСЃРёСЏ, СЌРєРІР°Р№СЂРёРЅРі",
            ).abs()
        )
    else:
        if "РљРѕРјРёСЃСЃРёСЏ" in df.columns:
            expenses["РљРѕРјРёСЃСЃРёСЏ"] = (
                safe_numeric_column(
                    df,
                    "РљРѕРјРёСЃСЃРёСЏ",
                ).abs()
            )

        if "Р­РєРІР°Р№СЂРёРЅРі" in df.columns:
            expenses["Р­РєРІР°Р№СЂРёРЅРі"] = (
                safe_numeric_column(
                    df,
                    "Р­РєРІР°Р№СЂРёРЅРі",
                ).abs()
            )

    if "Р›РѕРіРёСЃС‚РёРєР°" in df.columns:
        expenses["Р›РѕРіРёСЃС‚РёРєР°"] = (
            safe_numeric_column(
                df,
                "Р›РѕРіРёСЃС‚РёРєР°",
            ).abs()
        )

    storage_column = first_existing_column(
        df,
        [
            "РџР»Р°С‚РЅРѕРµ С…СЂР°РЅРµРЅРёРµ",
            "РҐСЂР°РЅРµРЅРёРµ",
        ],
    )

    if storage_column:
        expenses["РҐСЂР°РЅРµРЅРёРµ"] = (
            safe_numeric_column(
                df,
                storage_column,
            ).abs()
        )

    if "РџР»Р°С‚РЅР°СЏ РїСЂРёРµРјРєР°" in df.columns:
        expenses["РџР»Р°С‚РЅР°СЏ РїСЂРёС‘РјРєР°"] = (
            safe_numeric_column(
                df,
                "РџР»Р°С‚РЅР°СЏ РїСЂРёРµРјРєР°",
            ).abs()
        )

    if "РџСЂРѕРґРІРёР¶РµРЅРёРµ" in df.columns:
        expenses["РџСЂРѕРґРІРёР¶РµРЅРёРµ"] = (
            safe_numeric_column(
                df,
                "РџСЂРѕРґРІРёР¶РµРЅРёРµ",
            ).abs()
        )

    if "РЁС‚СЂР°С„С‹" in df.columns:
        expenses["РЁС‚СЂР°С„С‹"] = (
            safe_numeric_column(
                df,
                "РЁС‚СЂР°С„С‹",
            ).abs()
        )

    if "РЎРµР±РµСЃС‚РѕРёРјРѕСЃС‚СЊ" in df.columns:
        expenses["РЎРµР±РµСЃС‚РѕРёРјРѕСЃС‚СЊ"] = (
            safe_numeric_column(
                df,
                "РЎРµР±РµСЃС‚РѕРёРјРѕСЃС‚СЊ",
            ).abs()
        )

    tax_column = first_existing_column(
        df,
        [
            "РЎСѓРјРјР° РЅР°Р»РѕРіРѕРІ",
            "РќР°Р»РѕРі",
            "РџСЂСЏРјРѕР№ РЅР°Р»РѕРі",
        ],
    )

    if tax_column:
        expenses["РќР°Р»РѕРіРё"] = (
            safe_numeric_column(
                df,
                tax_column,
            ).abs()
        )

    if "Р’РЅРµС€РЅРёРµ СЂР°СЃС…РѕРґС‹" in df.columns:
        expenses["Р’РЅРµС€РЅРёРµ СЂР°СЃС…РѕРґС‹"] = (
            safe_numeric_column(
                df,
                "Р’РЅРµС€РЅРёРµ СЂР°СЃС…РѕРґС‹",
            ).abs()
        )

    return expenses


def get_total_expense_series(
    df: pd.DataFrame,
) -> pd.Series:
    result = pd.Series(
        0.0,
        index=df.index,
        dtype="float64",
    )

    for values in build_expense_series(df).values():
        result = result + values

    return result


def get_profit_series(
    df: pd.DataFrame,
) -> pd.Series:
    if "Р§РёСЃС‚Р°СЏ РїСЂРёР±С‹Р»СЊ" in df.columns:
        return safe_numeric_column(
            df,
            "Р§РёСЃС‚Р°СЏ РїСЂРёР±С‹Р»СЊ",
        )

    return (
        get_revenue_series(df)
        - get_total_expense_series(df)
    )


def get_sales_series(
    df: pd.DataFrame,
) -> pd.Series:
    sales_column = first_existing_column(
        df,
        [
            "РљРѕР»-РІРѕ РїСЂРѕРґР°Р¶",
            "Р—Р°РєР°Р·С‹ (РёР· Р»РµРЅС‚С‹ РІ API)",
            "Р—Р°РєР°Р·С‹",
        ],
    )

    if sales_column:
        return safe_numeric_column(
            df,
            sales_column,
        )

    if "Р”Р°С‚Р° РїСЂРѕРґР°Р¶Рё" in df.columns:
        dates = pd.to_datetime(
            df["Р”Р°С‚Р° РїСЂРѕРґР°Р¶Рё"],
            errors="coerce",
        )

        return dates.notna().astype(float)

    if "РЎС‚Р°С‚СѓСЃ" in df.columns:
        statuses = (
            df["РЎС‚Р°С‚СѓСЃ"]
            .fillna("")
            .astype(str)
            .str.lower()
        )

        return statuses.str.contains(
            "РґРѕСЃС‚Р°РІР»РµРЅ|РїСЂРѕРґР°РЅ",
            regex=True,
        ).astype(float)

    return pd.Series(
        0.0,
        index=df.index,
        dtype="float64",
    )


def get_returns_series(
    df: pd.DataFrame,
) -> pd.Series:
    returns_column = first_existing_column(
        df,
        [
            "РљРѕР»-РІРѕ РІРѕР·РІСЂР°С‚РѕРІ",
            "Р’РѕР·РІСЂР°С‚С‹ Р·Р°РєР°Р·РѕРІ",
        ],
    )

    if returns_column:
        return safe_numeric_column(
            df,
            returns_column,
        )

    if "Р”Р°С‚Р° РІРѕР·РІСЂР°С‚Р°" in df.columns:
        dates = pd.to_datetime(
            df["Р”Р°С‚Р° РІРѕР·РІСЂР°С‚Р°"],
            errors="coerce",
        )

        return dates.notna().astype(float)

    if "РЎС‚Р°С‚СѓСЃ" in df.columns:
        statuses = (
            df["РЎС‚Р°С‚СѓСЃ"]
            .fillna("")
            .astype(str)
            .str.lower()
        )

        return statuses.str.contains(
            "РІРѕР·РІСЂР°С‚",
            regex=False,
        ).astype(float)

    return pd.Series(
        0.0,
        index=df.index,
        dtype="float64",
    )


# ============================================================
# РџРћРЎРўРћРЇРќРќРђРЇ Р‘РђР—Рђ РўРћР’РђР РћР’
# ============================================================

def require_database() -> None:
    if not DATABASE_URL:
        raise HTTPException(
            status_code=503,
            detail="РќР° СЃРµСЂРІРµСЂРµ РЅРµ РЅР°СЃС‚СЂРѕРµРЅР° DATABASE_URL",
        )


def init_database() -> None:
    if not DATABASE_URL:
        print("Р’РќРРњРђРќРР•: DATABASE_URL РЅРµ РЅР°СЃС‚СЂРѕРµРЅР°")
        return

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    wb_article BIGINT PRIMARY KEY,
                    brand TEXT,
                    subject TEXT,
                    size_code TEXT,
                    seller_article TEXT,
                    size TEXT,
                    barcode TEXT,
                    volume DOUBLE PRECISION,
                    composition TEXT,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS products_brand_idx
                ON products (brand)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS products_subject_idx
                ON products (subject)
                """
            )


@app.on_event("startup")
async def startup_database():
    try:
        init_database()
    except Exception as error:
        print(
            "РћС€РёР±РєР° РїРѕРґРєР»СЋС‡РµРЅРёСЏ Рє PostgreSQL:",
            type(error).__name__,
            str(error),
        )


def clean_text_value(value) -> Optional[str]:
    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text or text.lower() == "nan":
        return None

    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]

    return text


def dataframe_to_products(df: pd.DataFrame) -> list[tuple]:
    required = {"РђСЂС‚РёРєСѓР» WB", "Р‘СЂРµРЅРґ", "РџСЂРµРґРјРµС‚"}
    missing = sorted(required - set(df.columns))

    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                "Р­С‚Рѕ РЅРµ С„Р°Р№Р» Р°СЃСЃРѕСЂС‚РёРјРµРЅС‚Р°. "
                "РќРµ РЅР°Р№РґРµРЅС‹ РєРѕР»РѕРЅРєРё: " + ", ".join(missing)
            ),
        )

    articles = pd.to_numeric(
        df["РђСЂС‚РёРєСѓР» WB"],
        errors="coerce",
    )

    products = {}

    for index, article_value in articles.items():
        if pd.isna(article_value):
            continue

        article = int(article_value)

        volume = None
        if "РћР±СЉРµРј, Р»." in df.columns:
            parsed_volume = pd.to_numeric(
                pd.Series([df.at[index, "РћР±СЉРµРј, Р»."]]),
                errors="coerce",
            ).iloc[0]
            if not pd.isna(parsed_volume):
                volume = float(parsed_volume)

        products[article] = (
            article,
            clean_text_value(df.at[index, "Р‘СЂРµРЅРґ"]),
            clean_text_value(df.at[index, "РџСЂРµРґРјРµС‚"]),
            clean_text_value(df.at[index, "РљРѕРґ СЂР°Р·РјРµСЂР° (chrt_id)"])
            if "РљРѕРґ СЂР°Р·РјРµСЂР° (chrt_id)" in df.columns
            else None,
            clean_text_value(df.at[index, "РђСЂС‚РёРєСѓР» РїСЂРѕРґР°РІС†Р°"])
            if "РђСЂС‚РёРєСѓР» РїСЂРѕРґР°РІС†Р°" in df.columns
            else None,
            clean_text_value(df.at[index, "Р Р°Р·РјРµСЂ"])
            if "Р Р°Р·РјРµСЂ" in df.columns
            else None,
            clean_text_value(df.at[index, "Р‘Р°СЂРєРѕРґ"])
            if "Р‘Р°СЂРєРѕРґ" in df.columns
            else None,
            volume,
            clean_text_value(df.at[index, "РЎРѕСЃС‚Р°РІ"])
            if "РЎРѕСЃС‚Р°РІ" in df.columns
            else None,
        )

    if not products:
        raise HTTPException(
            status_code=422,
            detail="Р’ Р°СЃСЃРѕСЂС‚РёРјРµРЅС‚Рµ РЅРµ РЅР°Р№РґРµРЅРѕ РЅРё РѕРґРЅРѕРіРѕ РђСЂС‚РёРєСѓР»Р° WB",
        )

    return list(products.values())


def save_products(products: list[tuple]) -> dict:
    require_database()
    article_ids = [product[0] for product in products]

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT wb_article
                FROM products
                WHERE wb_article = ANY(%s)
                """,
                (article_ids,),
            )
            existing = {row[0] for row in cursor.fetchall()}

            cursor.executemany(
                """
                INSERT INTO products (
                    wb_article,
                    brand,
                    subject,
                    size_code,
                    seller_article,
                    size,
                    barcode,
                    volume,
                    composition,
                    updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, NOW()
                )
                ON CONFLICT (wb_article)
                DO UPDATE SET
                    brand = EXCLUDED.brand,
                    subject = EXCLUDED.subject,
                    size_code = EXCLUDED.size_code,
                    seller_article = EXCLUDED.seller_article,
                    size = EXCLUDED.size,
                    barcode = EXCLUDED.barcode,
                    volume = EXCLUDED.volume,
                    composition = EXCLUDED.composition,
                    updated_at = NOW()
                """,
                products,
            )

            cursor.execute(
                "SELECT COUNT(*) FROM products"
            )
            total = int(cursor.fetchone()[0])

    added = len(set(article_ids) - existing)
    updated = len(set(article_ids) & existing)

    return {
        "received": len(products),
        "added": added,
        "updated": updated,
        "total": total,
    }


def get_products(
    search: str = "",
    limit: int = 100,
) -> list[dict]:
    require_database()
    safe_limit = max(1, min(limit, 500))

    sql = """
        SELECT
            wb_article,
            brand,
            subject,
            seller_article,
            barcode,
            size,
            volume,
            updated_at
        FROM products
    """
    parameters = []

    if search:
        sql += """
            WHERE
                CAST(wb_article AS TEXT) ILIKE %s
                OR COALESCE(brand, '') ILIKE %s
                OR COALESCE(subject, '') ILIKE %s
                OR COALESCE(seller_article, '') ILIKE %s
        """
        pattern = f"%{search.strip()}%"
        parameters.extend([pattern, pattern, pattern, pattern])

    sql += " ORDER BY brand, subject, wb_article LIMIT %s"
    parameters.append(safe_limit)

    with psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, parameters)
            rows = cursor.fetchall()

    return [
        {
            **row,
            "updated_at": (
                row["updated_at"].isoformat()
                if row.get("updated_at")
                else None
            ),
        }
        for row in rows
    ]


def get_product_stats() -> dict:
    require_database()

    with psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS products,
                    COUNT(DISTINCT brand) AS brands,
                    COUNT(DISTINCT subject) AS subjects,
                    MAX(updated_at) AS updated_at
                FROM products
                """
            )
            row = cursor.fetchone()

    return {
        "products": int(row["products"] or 0),
        "brands": int(row["brands"] or 0),
        "subjects": int(row["subjects"] or 0),
        "updated_at": (
            row["updated_at"].isoformat()
            if row["updated_at"]
            else None
        ),
    }


def enrich_with_products(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if "РђСЂС‚РёРєСѓР» WB" not in df.columns or not DATABASE_URL:
        return df.copy(), {
            "total_articles": 0,
            "matched_articles": 0,
            "missing_articles": 0,
        }

    result = df.copy()
    article_keys = pd.to_numeric(
        result["РђСЂС‚РёРєСѓР» WB"],
        errors="coerce",
    )

    unique_articles = sorted({
        int(value)
        for value in article_keys.dropna().tolist()
    })

    if not unique_articles:
        return result, {
            "total_articles": 0,
            "matched_articles": 0,
            "missing_articles": 0,
        }

    with psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT wb_article, brand, subject
                FROM products
                WHERE wb_article = ANY(%s)
                """,
                (unique_articles,),
            )
            rows = cursor.fetchall()

    brand_map = {
        int(row["wb_article"]): row["brand"]
        for row in rows
    }
    subject_map = {
        int(row["wb_article"]): row["subject"]
        for row in rows
    }

    mapped_brands = article_keys.map(brand_map)
    mapped_subjects = article_keys.map(subject_map)

    if "Р‘СЂРµРЅРґ" not in result.columns:
        result["Р‘СЂРµРЅРґ"] = mapped_brands
    else:
        empty_brand = (
            result["Р‘СЂРµРЅРґ"].isna()
            | (result["Р‘СЂРµРЅРґ"].astype(str).str.strip() == "")
        )
        result.loc[empty_brand, "Р‘СЂРµРЅРґ"] = mapped_brands[empty_brand]

    if "РџСЂРµРґРјРµС‚" not in result.columns:
        result["РџСЂРµРґРјРµС‚"] = mapped_subjects
    else:
        empty_subject = (
            result["РџСЂРµРґРјРµС‚"].isna()
            | (result["РџСЂРµРґРјРµС‚"].astype(str).str.strip() == "")
        )
        result.loc[empty_subject, "РџСЂРµРґРјРµС‚"] = mapped_subjects[empty_subject]

    matched = len(rows)

    return result, {
        "total_articles": len(unique_articles),
        "matched_articles": matched,
        "missing_articles": len(unique_articles) - matched,
    }


# ============================================================
# РђРќРђР›РРўРРљРђ РЎРџРџ
# ============================================================

def serialize_spp_rows(df: pd.DataFrame) -> list[dict]:
    records = []

    for row in df.to_dict(orient="records"):
        record = {}
        for key, value in row.items():
            if pd.isna(value):
                record[key] = None
            elif hasattr(value, "isoformat"):
                record[key] = value.isoformat()
            elif isinstance(value, (int, float)):
                record[key] = round(float(value), 2)
            else:
                record[key] = str(value)
        records.append(record)

    return records


def spp_group_dynamics(
    working: pd.DataFrame,
    group_columns: list[str],
    limit: int = 50,
    minimum_orders: int = 1,
) -> list[dict]:
    grouped = (
        working
        .groupby(group_columns + ["day"], dropna=False)
        .agg(
            orders=("spp", "size"),
            revenue=("our_price", "sum"),
            avg_spp=("spp", "mean"),
            min_spp=("spp", "min"),
            max_spp=("spp", "max"),
            avg_our_price=("our_price", "mean"),
            avg_sale_price=("sale_price", "mean"),
        )
        .reset_index()
    )

    totals = (
        working
        .groupby(group_columns, dropna=False)
        .agg(
            total_orders=("spp", "size"),
            revenue=("our_price", "sum"),
            avg_spp=("spp", "mean"),
        )
        .reset_index()
    )

    totals = totals[
        totals["total_orders"] >= minimum_orders
    ].sort_values(
        "total_orders",
        ascending=False,
    ).head(limit)

    allowed = {
        tuple(row[column] for column in group_columns)
        for row in totals.to_dict(orient="records")
    }

    result = []

    for key, rows in grouped.groupby(group_columns, dropna=False):
        key_tuple = key if isinstance(key, tuple) else (key,)
        if key_tuple not in allowed:
            continue

        rows = rows.sort_values("day")
        days = serialize_spp_rows(rows[[
            "day",
            "orders",
            "revenue",
            "avg_spp",
            "min_spp",
            "max_spp",
            "avg_our_price",
            "avg_sale_price",
        ]])

        first = rows.iloc[0]
        last = rows.iloc[-1]
        previous = (
            rows.iloc[-2]
            if len(rows) > 1
            else first
        )

        item = {
            column: (
                "РќРµ СѓРєР°Р·Р°РЅРѕ"
                if pd.isna(value)
                else str(value)
            )
            for column, value in zip(
                group_columns,
                key_tuple,
            )
        }
        item.update({
            "total_orders": int(rows["orders"].sum()),
            "revenue": round(float(rows["revenue"].sum()), 2),
            "avg_spp": round(
                float(
                    (
                        rows["avg_spp"]
                        * rows["orders"]
                    ).sum()
                    / rows["orders"].sum()
                ),
                2,
            ),
            "spp_change": round(
                float(last["avg_spp"] - previous["avg_spp"]),
                2,
            ),
            "orders_change": int(
                last["orders"] - previous["orders"]
            ),
            "previous_orders": int(previous["orders"]),
            "current_orders": int(last["orders"]),
            "orders_change_percent": round(
                float((last["orders"] / previous["orders"] - 1) * 100),
                2,
            ) if previous["orders"] else None,
            "period_spp_change": round(
                float(last["avg_spp"] - first["avg_spp"]),
                2,
            ),
            "period_orders_change": int(
                last["orders"] - first["orders"]
            ),
            "period_orders_change_percent": round(
                float((last["orders"] / first["orders"] - 1) * 100),
                2,
            ) if first["orders"] else None,
            "days": days,
        })
        result.append(item)

    return sorted(
        result,
        key=lambda item: item["total_orders"],
        reverse=True,
    )


def build_spp_analysis(
    df: pd.DataFrame,
    match_stats: dict,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    required = {
        "Р”Р°С‚Р° Р·Р°РєР°Р·Р°",
        "РђСЂС‚РёРєСѓР» WB",
        "РЎРџРџ",
        "РЎРєР»Р°Рґ",
        "Р РµРіРёРѕРЅ",
    }
    missing = sorted(required - set(df.columns))

    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                "Р­С‚Рѕ РЅРµ РЎРџРџ-РѕС‚С‡С‘С‚. "
                "РќРµ РЅР°Р№РґРµРЅС‹ РєРѕР»РѕРЅРєРё: " + ", ".join(missing)
            ),
        )

    order_dates = pd.to_datetime(
        df["Р”Р°С‚Р° Р·Р°РєР°Р·Р°"],
        errors="coerce",
    )
    spp = safe_numeric_column(df, "РЎРџРџ")

    working = pd.DataFrame({
        "datetime": order_dates,
        "spp": spp,
        "wb_article": pd.to_numeric(
            df["РђСЂС‚РёРєСѓР» WB"],
            errors="coerce",
        ),
        "product": (
            df["РќР°РёРјРµРЅРѕРІР°РЅРёРµ"].fillna("Р‘РµР· РЅР°Р·РІР°РЅРёСЏ").astype(str)
            if "РќР°РёРјРµРЅРѕРІР°РЅРёРµ" in df.columns
            else df["РђСЂС‚РёРєСѓР» WB"].astype(str)
        ),
        "brand": (
            df["Р‘СЂРµРЅРґ"].fillna("РќРµ РЅР°Р№РґРµРЅ РІ РўРћР’РђР РђРҐ").astype(str)
            if "Р‘СЂРµРЅРґ" in df.columns
            else "РќРµ РЅР°Р№РґРµРЅ РІ РўРћР’РђР РђРҐ"
        ),
        "subject": (
            df["РџСЂРµРґРјРµС‚"].fillna("РќРµ РЅР°Р№РґРµРЅ РІ РўРћР’РђР РђРҐ").astype(str)
            if "РџСЂРµРґРјРµС‚" in df.columns
            else "РќРµ РЅР°Р№РґРµРЅ РІ РўРћР’РђР РђРҐ"
        ),
        "warehouse": df["РЎРєР»Р°Рґ"].fillna("РќРµ СѓРєР°Р·Р°РЅРѕ").astype(str),
        "region": df["Р РµРіРёРѕРЅ"].fillna("РќРµ СѓРєР°Р·Р°РЅРѕ").astype(str),
        "our_price": safe_numeric_column(df, "Р¦РµРЅР° СЃРѕ СЃРєРёРґРєРѕР№"),
        "sale_price": safe_numeric_column(df, "Р¦РµРЅР° РїСЂРѕРґР°Р¶Рё"),
    })

    working = working.dropna(
        subset=["datetime", "wb_article"]
    )

    if date_from:
        start = pd.to_datetime(date_from, errors="coerce")
        if pd.isna(start):
            raise HTTPException(status_code=422, detail="РќРµРєРѕСЂСЂРµРєС‚РЅР°СЏ РЅР°С‡Р°Р»СЊРЅР°СЏ РґР°С‚Р°")
        working = working[working["datetime"] >= start]

    if date_to:
        end = pd.to_datetime(date_to, errors="coerce")
        if pd.isna(end):
            raise HTTPException(status_code=422, detail="РќРµРєРѕСЂСЂРµРєС‚РЅР°СЏ РєРѕРЅРµС‡РЅР°СЏ РґР°С‚Р°")
        working = working[working["datetime"] < end + pd.Timedelta(days=1)]

    if working.empty:
        raise HTTPException(
            status_code=422,
            detail="Р’ РЎРџРџ-РѕС‚С‡С‘С‚Рµ РЅРµС‚ РєРѕСЂСЂРµРєС‚РЅС‹С… СЃС‚СЂРѕРє",
        )

    working["day"] = working["datetime"].dt.date
    working["hour"] = working["datetime"].dt.hour

    daily = (
        working
        .groupby("day")
        .agg(
            orders=("spp", "size"),
            revenue=("our_price", "sum"),
            avg_spp=("spp", "mean"),
            median_spp=("spp", "median"),
            min_spp=("spp", "min"),
            max_spp=("spp", "max"),
            avg_our_price=("our_price", "mean"),
            avg_sale_price=("sale_price", "mean"),
        )
        .reset_index()
        .sort_values("day")
    )
    daily["spp_change"] = daily["avg_spp"].diff()
    daily["orders_change"] = daily["orders"].diff()
    daily["orders_change_percent"] = (
        daily["orders"].pct_change() * 100
    )

    hourly = (
        working
        .groupby(["day", "hour"])
        .agg(
            orders=("spp", "size"),
            revenue=("our_price", "sum"),
            avg_spp=("spp", "mean"),
            min_spp=("spp", "min"),
            max_spp=("spp", "max"),
        )
        .reset_index()
        .sort_values(["day", "hour"])
    )

    brands = spp_group_dynamics(
        working,
        ["brand"],
        limit=50,
        minimum_orders=3,
    )
    subjects = spp_group_dynamics(
        working,
        ["subject"],
        limit=50,
        minimum_orders=3,
    )
    products = spp_group_dynamics(
        working,
        ["product", "wb_article"],
        limit=100,
        minimum_orders=3,
    )
    links = spp_group_dynamics(
        working,
        ["subject", "warehouse", "region"],
        limit=150,
        minimum_orders=5,
    )

    alerts = [
        item
        for item in links
        if (
            item["orders_change"] < 0
        )
    ]
    alerts.sort(
        key=lambda item: item.get("orders_change_percent") or 0
    )

    first_day = daily.iloc[0]
    last_day = daily.iloc[-1]

    return {
        "report_type": "spp",
        "period": {
            "from": first_day["day"].isoformat(),
            "to": last_day["day"].isoformat(),
            "days": int(len(daily)),
        },
        "summary": {
            "orders": int(len(working)),
            "revenue": round(float(working["our_price"].sum()), 2),
            "avg_spp": round(float(working["spp"].mean()), 2),
            "min_spp": round(float(working["spp"].min()), 2),
            "max_spp": round(float(working["spp"].max()), 2),
            "spp_change": round(
                float(last_day["avg_spp"] - first_day["avg_spp"]),
                2,
            ),
            "orders_change": int(
                last_day["orders"] - first_day["orders"]
            ),
            "orders_change_percent": round(
                float(
                    (
                        last_day["orders"]
                        / first_day["orders"]
                        - 1
                    )
                    * 100
                ),
                2,
            ) if first_day["orders"] else None,
        },
        "product_matching": match_stats,
        "daily": serialize_spp_rows(daily),
        "hourly": serialize_spp_rows(hourly),
        "brands": brands,
        "subjects": subjects,
        "products": products,
        "links": links,
        "alerts": alerts[:30],
    }


# ============================================================
# Р›РЈР§РЁРР™ Р РҐРЈР”РЁРР™ Р”Р•РќР¬
# ============================================================

def build_daily_summary(
    df: pd.DataFrame,
) -> dict:
    if "Р”Р°С‚Р° РїСЂРѕРґР°Р¶Рё" not in df.columns:
        return {
            "available": False,
            "best_day": None,
            "worst_day": None,
        }

    dates = pd.to_datetime(
        df["Р”Р°С‚Р° РїСЂРѕРґР°Р¶Рё"],
        errors="coerce",
    )

    working = pd.DataFrame({
        "date": dates,
        "revenue": get_revenue_series(df),
        "profit": get_profit_series(df),
        "sales": get_sales_series(df),
    })

    working = working.dropna(
        subset=["date"]
    )

    if working.empty:
        return {
            "available": False,
            "best_day": None,
            "worst_day": None,
        }

    working["day"] = (
        working["date"].dt.date
    )

    grouped = (
        working
        .groupby("day")
        .agg(
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
            sales=("sales", "sum"),
        )
        .reset_index()
    )

    best_row = grouped.loc[
        grouped["profit"].idxmax()
    ]

    worst_row = grouped.loc[
        grouped["profit"].idxmin()
    ]

    def serialize_day(row) -> dict:
        return {
            "date": row["day"].isoformat(),
            "revenue": round(
                float(row["revenue"]),
                2,
            ),
            "profit": round(
                float(row["profit"]),
                2,
            ),
            "sales": int(
                round(float(row["sales"]))
            ),
        }

    return {
        "available": True,
        "best_day": serialize_day(best_row),
        "worst_day": serialize_day(worst_row),
    }


# ============================================================
# Р›РЈР§РЁРР™ Р РҐРЈР”РЁРР™ РўРћР’РђР 
# ============================================================

def get_product_name_column(
    df: pd.DataFrame,
) -> Optional[str]:
    return first_existing_column(
        df,
        [
            "РќР°РёРјРµРЅРѕРІР°РЅРёРµ",
            "РџСЂРµРґРјРµС‚",
            "РђСЂС‚РёРєСѓР» РїСЂРѕРґР°РІС†Р°",
            "РђСЂС‚РёРєСѓР» WB",
        ],
    )


def build_product_extremes(
    df: pd.DataFrame,
) -> dict:
    product_column = get_product_name_column(df)

    if not product_column:
        return {
            "available": False,
            "best_product": None,
            "worst_product": None,
        }

    names = (
        df[product_column]
        .fillna("РќРµ СѓРєР°Р·Р°РЅРѕ")
        .astype(str)
        .str.strip()
    )

    names = names.replace(
        "",
        "РќРµ СѓРєР°Р·Р°РЅРѕ",
    )

    working = pd.DataFrame({
        "product": names,
        "revenue": get_revenue_series(df),
        "profit": get_profit_series(df),
        "sales": get_sales_series(df),
        "returns": get_returns_series(df),
    })

    grouped = (
        working
        .groupby("product", dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
            sales=("sales", "sum"),
            returns=("returns", "sum"),
        )
        .reset_index()
    )

    if grouped.empty:
        return {
            "available": False,
            "best_product": None,
            "worst_product": None,
        }

    best_row = grouped.loc[
        grouped["profit"].idxmax()
    ]

    worst_row = grouped.loc[
        grouped["profit"].idxmin()
    ]

    def serialize_product(row) -> dict:
        return {
            "name": str(row["product"]),
            "revenue": round(
                float(row["revenue"]),
                2,
            ),
            "profit": round(
                float(row["profit"]),
                2,
            ),
            "sales": int(
                round(float(row["sales"]))
            ),
            "returns": int(
                round(float(row["returns"]))
            ),
        }

    return {
        "available": True,
        "best_product": serialize_product(
            best_row
        ),
        "worst_product": serialize_product(
            worst_row
        ),
    }


# ============================================================
# РћРЎРќРћР’РќР«Р• РџРћРљРђР—РђРўР•Р›Р
# ============================================================

def build_product_chart(
    df: pd.DataFrame,
    limit: int = 50,
) -> list[dict]:
    product_column = get_product_name_column(df)

    if not product_column:
        return []

    working = pd.DataFrame({
        "product": (
            df[product_column]
            .fillna("Р‘РµР· РЅР°Р·РІР°РЅРёСЏ")
            .astype(str)
            .str.strip()
        ),
        "revenue": get_revenue_series(df),
        "profit": get_profit_series(df),
        "expenses": get_total_expense_series(df),
        "sales": get_sales_series(df),
    })

    grouped = (
        working
        .groupby("product", dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
            expenses=("expenses", "sum"),
            sales=("sales", "sum"),
        )
        .reset_index()
    )

    grouped["margin"] = grouped.apply(
        lambda row: (
            row["profit"] / row["revenue"] * 100
            if row["revenue"]
            else 0
        ),
        axis=1,
    )

    grouped = grouped.sort_values(
        "revenue",
        ascending=False,
    ).head(limit)

    return [
        {
            "name": str(row["product"]),
            "revenue": round(float(row["revenue"]), 2),
            "profit": round(float(row["profit"]), 2),
            "expenses": round(float(row["expenses"]), 2),
            "sales": int(round(float(row["sales"]))),
            "margin_percent": round(float(row["margin"]), 2),
        }
        for row in grouped.to_dict(orient="records")
    ]


def build_finance_daily_chart(
    df: pd.DataFrame,
) -> list[dict]:
    date_column = first_existing_column(
        df,
        ["Р”Р°С‚Р° РїСЂРѕРґР°Р¶Рё", "Р”Р°С‚Р° Р·Р°РєР°Р·Р°"],
    )

    if not date_column:
        return []

    dates = pd.to_datetime(
        df[date_column],
        errors="coerce",
    )

    working = pd.DataFrame({
        "date": dates,
        "revenue": get_revenue_series(df),
        "profit": get_profit_series(df),
        "expenses": get_total_expense_series(df),
        "sales": get_sales_series(df),
    }).dropna(subset=["date"])

    if working.empty:
        return []

    working["day"] = working["date"].dt.date

    grouped = (
        working
        .groupby("day")
        .agg(
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
            expenses=("expenses", "sum"),
            sales=("sales", "sum"),
        )
        .reset_index()
        .sort_values("day")
    )

    return [
        {
            "day": row["day"].isoformat(),
            "revenue": round(float(row["revenue"]), 2),
            "profit": round(float(row["profit"]), 2),
            "expenses": round(float(row["expenses"]), 2),
            "sales": int(round(float(row["sales"]))),
        }
        for row in grouped.to_dict(orient="records")
    ]

def build_metrics(
    df: pd.DataFrame,
) -> dict:
    revenue_series = get_revenue_series(df)
    profit_series = get_profit_series(df)
    sales_series = get_sales_series(df)
    returns_series = get_returns_series(df)

    expense_series = build_expense_series(df)

    revenue = round(
        float(revenue_series.sum()),
        2,
    )

    net_profit = round(
        float(profit_series.sum()),
        2,
    )

    expenses = {}

    for name, values in expense_series.items():
        value = round(
            float(values.sum()),
            2,
        )

        if value != 0:
            expenses[name] = value

    if "Р§РёСЃС‚Р°СЏ РїСЂРёР±С‹Р»СЊ" in df.columns:
        total_expenses = round(
            revenue - net_profit,
            2,
        )
    else:
        total_expenses = round(
            sum(expenses.values()),
            2,
        )

    margin_percent = None

    if revenue != 0:
        margin_percent = round(
            net_profit / revenue * 100,
            2,
        )

    total_cost = expenses.get(
        "РЎРµР±РµСЃС‚РѕРёРјРѕСЃС‚СЊ",
        0.0,
    )

    roi_percent = None

    if total_cost != 0:
        roi_percent = round(
            net_profit / total_cost * 100,
            2,
        )

    sales_count = int(
        round(float(sales_series.sum()))
    )

    returns_count = int(
        round(float(returns_series.sum()))
    )

    daily_summary = build_daily_summary(df)
    product_extremes = build_product_extremes(df)

    return {
        "total_revenue": revenue,
        "net_profit": net_profit,
        "total_expenses": total_expenses,
        "margin_percent": margin_percent,
        "roi_percent": roi_percent,
        "sales_count": sales_count,
        "returns_count": returns_count,
        "expenses": expenses,
        "rows_count": int(len(df)),
        "columns_count": int(len(df.columns)),
        "columns": [
            str(column)
            for column in df.columns
        ],
        "daily_summary": daily_summary,
        "product_extremes": product_extremes,
        "charts": {
            "products": build_product_chart(df),
            "daily": build_finance_daily_chart(df),
        },
    }


# ============================================================
# РЎР’РћР”РљР Р”Р›РЇ РР
# ============================================================

def build_group_summary(
    df: pd.DataFrame,
    group_column: str,
    limit: int = 20,
) -> list:
    if group_column not in df.columns:
        return []

    names = (
        df[group_column]
        .fillna("РќРµ СѓРєР°Р·Р°РЅРѕ")
        .astype(str)
        .str.strip()
    )

    working = pd.DataFrame({
        "name": names,
        "revenue": get_revenue_series(df),
        "profit": get_profit_series(df),
        "expenses": get_total_expense_series(df),
        "sales": get_sales_series(df),
        "returns": get_returns_series(df),
    })

    grouped = (
        working
        .groupby("name", dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
            expenses=("expenses", "sum"),
            sales=("sales", "sum"),
            returns=("returns", "sum"),
        )
        .reset_index()
        .sort_values(
            by="revenue",
            ascending=False,
        )
        .head(limit)
    )

    result = []

    for row in grouped.to_dict(
        orient="records"
    ):
        result.append({
            "name": str(row["name"]),
            "revenue": round(
                float(row["revenue"]),
                2,
            ),
            "profit": round(
                float(row["profit"]),
                2,
            ),
            "expenses": round(
                float(row["expenses"]),
                2,
            ),
            "sales": int(
                round(float(row["sales"]))
            ),
            "returns": int(
                round(float(row["returns"]))
            ),
        })

    return result


def build_ai_context(
    df: pd.DataFrame,
    metrics: dict,
) -> dict:
    product_column = get_product_name_column(df)

    return {
        "main_metrics": metrics,
        "top_products": (
            build_group_summary(
                df,
                product_column,
            )
            if product_column
            else []
        ),
        "top_vendor_articles": (
            build_group_summary(
                df,
                "РђСЂС‚РёРєСѓР» РїСЂРѕРґР°РІС†Р°",
            )
        ),
        "top_wb_articles": (
            build_group_summary(
                df,
                "РђСЂС‚РёРєСѓР» WB",
            )
        ),
        "regions": build_group_summary(
            df,
            "Р РµРіРёРѕРЅ",
        ),
        "warehouses": build_group_summary(
            df,
            "РЎРєР»Р°Рґ",
        ),
        "statuses": build_group_summary(
            df,
            "РЎС‚Р°С‚СѓСЃ",
        ),
        "brands": build_group_summary(
            df,
            "Р‘СЂРµРЅРґ",
        ),
        "categories": build_group_summary(
            df,
            "РџСЂРµРґРјРµС‚",
        ),
    }


async def ask_openai(
    question: str,
    context: dict,
) -> str:
    if openai_client is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "OpenAI РЅРµ РїРѕРґРєР»СЋС‡С‘РЅ. "
                "РџСЂРѕРІРµСЂСЊС‚Рµ OPENAI_API_KEY"
            ),
        )

    instructions = """
РўС‹ вЂ” РїСЂРѕС„РµСЃСЃРёРѕРЅР°Р»СЊРЅС‹Р№ С„РёРЅР°РЅСЃРѕРІС‹Р№ Р°РЅР°Р»РёС‚РёРє РѕС‚С‡С‘С‚РѕРІ Wildberries.

РџСЂР°РІРёР»Р°:

1. РћС‚РІРµС‡Р°Р№ С‚РѕР»СЊРєРѕ РЅР° РѕСЃРЅРѕРІРµ РїРµСЂРµРґР°РЅРЅС‹С… РґР°РЅРЅС‹С….
2. РќРµ РїСЂРёРґСѓРјС‹РІР°Р№ РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‰РёРµ С†РёС„СЂС‹.
3. Р•СЃР»Рё РґР°РЅРЅС‹С… РЅРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ, СЃРєР°Р¶Рё РѕР± СЌС‚РѕРј РїСЂСЏРјРѕ.
4. Р’СЃРµ РґРµРЅРµР¶РЅС‹Рµ Р·РЅР°С‡РµРЅРёСЏ СѓРєР°Р·С‹РІР°Р№ РІ СЂСѓР±Р»СЏС….
5. РџРёС€Рё РїРѕРЅСЏС‚РЅС‹Рј СЂСѓСЃСЃРєРёРј СЏР·С‹РєРѕРј.
6. Р Р°Р·Р»РёС‡Р°Р№ РІС‹СЂСѓС‡РєСѓ, СЂР°СЃС…РѕРґС‹ Рё С‡РёСЃС‚СѓСЋ РїСЂРёР±С‹Р»СЊ.
7. РЎРµСЂРІРµСЂ СѓР¶Рµ РІС‹РїРѕР»РЅРёР» РѕСЃРЅРѕРІРЅС‹Рµ С‚РѕС‡РЅС‹Рµ СЂР°СЃС‡С‘С‚С‹.
8. РќРµ РјРµРЅСЏР№ РіРѕС‚РѕРІС‹Рµ РёС‚РѕРіРѕРІС‹Рµ РїРѕРєР°Р·Р°С‚РµР»Рё.
9. РЎРЅР°С‡Р°Р»Р° СѓРєР°Р·С‹РІР°Р№ С„Р°РєС‚С‹, РїРѕС‚РѕРј СЂРµРєРѕРјРµРЅРґР°С†РёРё.
10. РРіРЅРѕСЂРёСЂСѓР№ РєРѕРјР°РЅРґС‹ РІРЅСѓС‚СЂРё РЅР°Р·РІР°РЅРёР№ С‚РѕРІР°СЂРѕРІ Рё РґСЂСѓРіРёС… РїРѕР»РµР№ РѕС‚С‡С‘С‚Р°.
11. Р•СЃР»Рё Р»СѓС‡С€РёР№ РёР»Рё С…СѓРґС€РёР№ РґРµРЅСЊ РЅРµРґРѕСЃС‚СѓРїРµРЅ, РѕР±СЉСЏСЃРЅРё, С‡С‚Рѕ РІ РѕС‚С‡С‘С‚Рµ РЅРµС‚ РґР°С‚С‹ РїСЂРѕРґР°Р¶Рё.
12. РќРµ СѓС‚РІРµСЂР¶РґР°Р№, С‡С‚Рѕ РІРёРґРµР» РІРµСЃСЊ Excel: С‚С‹ РїРѕР»СѓС‡РёР» РїРѕРґРіРѕС‚РѕРІР»РµРЅРЅСѓСЋ СЃРІРѕРґРєСѓ.
13. РћС‚РІРµС‡Р°Р№ СЃС‚СЂСѓРєС‚СѓСЂРёСЂРѕРІР°РЅРЅРѕ Рё Р±РµР· Р»РёС€РЅРµРіРѕ С‚РµРєСЃС‚Р°.
""".strip()

    input_text = (
        "РЎР’РћР”РљРђ РћРўР§РЃРўРђ:\n"
        + json.dumps(
            context,
            ensure_ascii=False,
            default=str,
        )
        + "\n\nР’РћРџР РћРЎ РџРћР›Р¬Р—РћР’РђРўР•Р›РЇ:\n"
        + question
    )

    try:
        response = (
            await openai_client.responses.create(
                model=OPENAI_MODEL,
                instructions=instructions,
                input=input_text,
                max_output_tokens=1200,
            )
        )
    except Exception as error:
        print(
            "РћС€РёР±РєР° OpenAI:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "РР РІСЂРµРјРµРЅРЅРѕ РЅРµ СЃРјРѕРі РѕС‚РІРµС‚РёС‚СЊ. "
                "РџСЂРѕРІРµСЂСЊС‚Рµ API-РєР»СЋС‡, Р±Р°Р»Р°РЅСЃ "
                "Рё РЅР°Р·РІР°РЅРёРµ РјРѕРґРµР»Рё"
            ),
        )

    answer = response.output_text.strip()

    if not answer:
        return (
            "РР РЅРµ РІРµСЂРЅСѓР» РѕС‚РІРµС‚. "
            "РџРѕРїСЂРѕР±СѓР№С‚Рµ Р·Р°РґР°С‚СЊ РІРѕРїСЂРѕСЃ РёРЅР°С‡Рµ."
        )

    return answer


# ============================================================
# Р§РўР•РќРР• EXCEL
# ============================================================

async def read_excel_file(
    file: UploadFile,
) -> pd.DataFrame:
    filename = file.filename or ""

    extension = os.path.splitext(
        filename.lower()
    )[1]

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                "Р Р°Р·СЂРµС€РµРЅС‹ С‚РѕР»СЊРєРѕ "
                "С„Р°Р№Р»С‹ .xlsx Рё .xls"
            ),
        )

    contents = await file.read(
        MAX_FILE_SIZE_BYTES + 1
    )

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Р’С‹ Р·Р°РіСЂСѓР·РёР»Рё РїСѓСЃС‚РѕР№ С„Р°Р№Р»",
        )

    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Р¤Р°Р№Р» СЃР»РёС€РєРѕРј Р±РѕР»СЊС€РѕР№. "
                f"РњР°РєСЃРёРјСѓРј: {MAX_FILE_SIZE_MB} РњР‘"
            ),
        )

    try:
        df = pd.read_excel(
            io.BytesIO(contents)
        )
    except Exception as error:
        print(
            "РћС€РёР±РєР° Excel:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=422,
            detail=(
                "РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕС‡РёС‚Р°С‚СЊ Excel. "
                "РџСЂРѕРІРµСЂСЊС‚Рµ С„Р°Р№Р»"
            ),
        )

    if df.empty:
        raise HTTPException(
            status_code=422,
            detail="Р’ С‚Р°Р±Р»РёС†Рµ РЅРµС‚ РґР°РЅРЅС‹С…",
        )

    return clean_dataframe(df)


# ============================================================
# API
# ============================================================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "WB AI Agent API СЂР°Р±РѕС‚Р°РµС‚",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "openai_configured": bool(
            OPENAI_API_KEY
        ),
        "password_configured": bool(
            APP_PASSWORD
        ),
        "model": OPENAI_MODEL,
        "database_configured": bool(DATABASE_URL),
    }


@app.post("/login")
async def login(
    app_password: str = Form(...),
):
    check_password(app_password)

    return {
        "success": True,
        "message": "РџР°СЂРѕР»СЊ РїСЂРёРЅСЏС‚",
    }


@app.post("/products/upload")
async def upload_products(
    file: UploadFile = File(...),
    app_password: str = Form(...),
):
    check_password(app_password)
    df = await read_excel_file(file)
    products = dataframe_to_products(df)
    result = save_products(products)

    return {
        "success": True,
        **result,
    }


@app.post("/products/list")
async def list_products(
    app_password: str = Form(...),
    search: str = Form(""),
    limit: int = Form(100),
):
    check_password(app_password)

    return {
        "stats": get_product_stats(),
        "products": get_products(search, limit),
    }


@app.post("/spp/analyze")
async def analyze_spp(
    file: UploadFile = File(...),
    app_password: str = Form(...),
    user_query: Optional[str] = Form(None),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
):
    check_password(app_password)
    df = await read_excel_file(file)
    enriched_df, match_stats = enrich_with_products(df)
    analysis = build_spp_analysis(
        enriched_df,
        match_stats,
        date_from,
        date_to,
    )

    ai_response = (
        "РЎРџРџ-РѕС‚С‡С‘С‚ РѕР±СЂР°Р±РѕС‚Р°РЅ. "
        "Р—Р°РґР°Р№С‚Рµ РІРѕРїСЂРѕСЃ РР-Р°РЅР°Р»РёС‚РёРєСѓ."
    )

    if user_query and user_query.strip():
        ai_response = await ask_openai(
            user_query.strip(),
            {"spp_analysis": analysis},
        )

    return {
        "analysis": analysis,
        "ai_response": ai_response,
    }


@app.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    app_password: str = Form(...),
    user_query: Optional[str] = Form(None),
):
    check_password(app_password)

    question = (
        user_query.strip()
        if user_query
        else ""
    )

    if len(question) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=(
                "Р’РѕРїСЂРѕСЃ СЃР»РёС€РєРѕРј РґР»РёРЅРЅС‹Р№. "
                "РњР°РєСЃРёРјСѓРј 1000 СЃРёРјРІРѕР»РѕРІ"
            ),
        )

    df = await read_excel_file(file)
    df, _ = enrich_with_products(df)
    metrics = build_metrics(df)

    ai_response = (
        "РћС‚С‡С‘С‚ СѓСЃРїРµС€РЅРѕ РѕР±СЂР°Р±РѕС‚Р°РЅ. "
        "РўРµРїРµСЂСЊ Р·Р°РґР°Р№С‚Рµ РІРѕРїСЂРѕСЃ РР."
    )

    if question:
        context = build_ai_context(
            df,
            metrics,
        )

        ai_response = await ask_openai(
            question,
            context,
        )

    return {
        **metrics,
        "ai_response": ai_response,
    }
