#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""usecase_advisor.ipynb를 생성한다(plain json, nbformat 패키지 불필요). 실행: python build_notebook.py"""
import json


def md(src: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": src}


def code(src: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src}


cells = [
md('''# 데이터 소스 → 활용 시나리오 추천 → 갭 분석 파이프라인 (프로토타입)

**핵심 흐름**

```mermaid
flowchart LR
  A[데이터 소스\\nOneLake/Databricks/PostgreSQL/MySQL/MSSQL/SAP HANA] --> B[프로파일링\\nnull비율/카디널리티/시계열/PII]
  B --> C[비즈니스 개념 매핑\\n규칙 기반 + LLM 보완]
  C --> D[시나리오 추천 엔진\\n규칙 스코어링 + LLM 하이브리드]
  D --> E[갭 분석\\n부족한 데이터 제안]
  E --> F[대시보드\\n추천 카드 + 체크리스트]
```

## 사용 방법
- **실행 환경 선택**: 아래 설정 셀의 `RUNTIME_ENV`를 `"local"`(로컬 Jupyter/VS Code) 또는 `"fabric"`(Microsoft Fabric Notebook, OneLake 실제 연결)로 직접 선택하세요.
- **LLM 모델 선택**: `AZURE_OPENAI_DEPLOYMENT`에 사용하려는 배포 이름(예: `gpt-4o-mini`, `gpt-5.6-sol` 등 보유한 아무 배포)을 넣으면 됩니다. 비워두면 자동으로 규칙 기반만 동작합니다.
- **데이터 소스**: PostgreSQL/MySQL/MSSQL/SAP HANA는 환경변수(`PG_HOST`, `MYSQL_HOST`, `MSSQL_HOST`, `HANA_HOST`/`HANA_USERKEY`)를 채우면 실제 연결을 시도하고, 미설정이거나 연결 실패 시 자동으로 합성 데이터로 대체되어 파이프라인이 항상 끝까지 실행됩니다. OneLake/Databricks는 지금은 커넥터 스텁(합성 데이터)이며, 실제 연결로 그대로 교체 가능한 동일한 인터페이스로 작성했습니다.'''),

md('## 0. 패키지 설치'),

code('''# Fabric/로컬 Jupyter 공통 — 이미 설치된 패키지는 자동으로 건너뜁니다.
# pyodbc(MSSQL)는 시스템에 ODBC Driver 17/18이 설치돼 있어야 실제 연결이 됩니다(미설치면 합성 데이터로 자동 대체).
%pip install -q pandas numpy psycopg2-binary pymysql pyodbc hdbcli azure-identity "openai>=1.30.0" python-dotenv matplotlib'''),

md('## 1. 설정 — 실행 환경 / LLM 모델 / 데이터 소스 접속 정보'),

code('''import os
from typing import Optional

from dotenv import load_dotenv
load_dotenv()  # 로컬 Jupyter에서 .env 파일을 쓰는 경우

# ── 실행 환경 ────────────────────────────────────────────────────────────
# "local" : 로컬 Jupyter/VS Code (합성 데이터 + 실제 DB 드라이버 연결)
# "fabric": Microsoft Fabric Notebook (추가로 OneLake/Lakehouse를 PySpark로 실제 연결)
RUNTIME_ENV = os.getenv("RUNTIME_ENV", "local")  # 직접 "local" 또는 "fabric"으로 바꿔서 실행하세요.

# ── LLM(Azure OpenAI) 설정 — 어떤 모델/배포를 쓸지 여기서 직접 선택 ────────
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")       # 예: https://<resource>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")  # 예: gpt-4o-mini, gpt-5.6-sol 등 원하는 배포 이름
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
AZURE_OPENAI_AUTH_MODE = os.getenv("AZURE_OPENAI_AUTH_MODE", "aad")  # "aad"(기본, 키 발급 막힌 회사에 적합) 또는 "key"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")         # auth_mode=key 일 때만 사용

# 엔드포인트/배포가 비어있으면 자동으로 규칙 기반만 동작(파이프라인은 항상 끝까지 실행됨).
LLM_ENABLED = bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT)
print(f"실행 환경: {RUNTIME_ENV} | LLM 사용: {LLM_ENABLED} (모델: {AZURE_OPENAI_DEPLOYMENT or '(미설정)'})")

# ── 데이터 소스 접속 정보(환경변수로 설정 — 미설정 시 해당 소스는 합성 데이터로 자동 대체) ──
DATA_SOURCES = {
    "postgres": {
        "enabled": bool(os.getenv("PG_HOST")),
        "host": os.getenv("PG_HOST", ""), "port": int(os.getenv("PG_PORT", "5432")),
        "dbname": os.getenv("PG_DBNAME", "postgres"), "user": os.getenv("PG_USER", ""),
        "password_env": "PG_DIAGNOSE_PASSWORD",
    },
    "mysql": {
        "enabled": bool(os.getenv("MYSQL_HOST")),
        "host": os.getenv("MYSQL_HOST", ""), "port": int(os.getenv("MYSQL_PORT", "3306")),
        "database": os.getenv("MYSQL_DATABASE", ""), "user": os.getenv("MYSQL_USER", ""),
        "password_env": "MYSQL_DIAGNOSE_PASSWORD",
    },
    "mssql": {
        "enabled": bool(os.getenv("MSSQL_HOST")),
        "host": os.getenv("MSSQL_HOST", ""), "port": int(os.getenv("MSSQL_PORT", "1433")),
        "database": os.getenv("MSSQL_DATABASE", ""), "user": os.getenv("MSSQL_USER", ""),
        "password_env": "MSSQL_DIAGNOSE_PASSWORD",
    },
    "hana": {
        "enabled": bool(os.getenv("HANA_HOST") or os.getenv("HANA_USERKEY")),
        "host": os.getenv("HANA_HOST", ""), "port": int(os.getenv("HANA_PORT", "30015")),
        "user": os.getenv("HANA_USER", ""), "userkey": os.getenv("HANA_USERKEY", ""),
        "password_env": "HANA_DIAGNOSE_PASSWORD",
    },
    "onelake": {"enabled": RUNTIME_ENV == "fabric", "lakehouse_path": os.getenv("ONELAKE_LAKEHOUSE_PATH", "")},
    "databricks": {
        "enabled": bool(os.getenv("DATABRICKS_HOST")),
        "host": os.getenv("DATABRICKS_HOST", ""), "http_path": os.getenv("DATABRICKS_HTTP_PATH", ""),
        "token_env": "DATABRICKS_TOKEN",
    },
}'''),

md('## 2. LLM 클라이언트 (Azure OpenAI, chat.completions ↔ responses API 자동 폴백)'),

code('''"""Azure OpenAI 호출 헬퍼.
chat.completions를 우선 시도하고, 배포(모델)가 이를 지원하지 않으면(최신 reasoning 모델 등)
자동으로 responses API로 폴백한다 — 사용자가 어떤 배포를 골라도 동일한 call_llm()으로 동작."""
from openai import AzureOpenAI

_llm_client = None


def _get_llm_client():
    global _llm_client
    if _llm_client is not None or not LLM_ENABLED:
        return _llm_client
    if AZURE_OPENAI_AUTH_MODE == "key":
        _llm_client = AzureOpenAI(azure_endpoint=AZURE_OPENAI_ENDPOINT, api_key=AZURE_OPENAI_API_KEY,
                                   api_version=AZURE_OPENAI_API_VERSION)
    else:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
        _llm_client = AzureOpenAI(azure_endpoint=AZURE_OPENAI_ENDPOINT,
                                   azure_ad_token_provider=token_provider,
                                   api_version=AZURE_OPENAI_API_VERSION)
    return _llm_client


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 400) -> str:
    """LLM 미설정이거나 호출 실패 시 빈 문자열 반환(파이프라인은 규칙 기반으로 계속 동작)."""
    client = _get_llm_client()
    if client is None:
        return ""
    try:
        resp = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}],
            max_tokens=max_tokens, temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as chat_err:  # noqa: BLE001 — 일부 배포는 chat.completions 미지원
        try:
            resp = client.responses.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                input=f"{system_prompt}\\n\\n{user_prompt}",
            )
            return (getattr(resp, "output_text", "") or "").strip()
        except Exception as responses_err:  # noqa: BLE001
            print(f"[llm] 호출 실패 (chat: {chat_err}) (responses: {responses_err})")
            return ""


if LLM_ENABLED:
    _test = call_llm("You are a helpful assistant.", "한 문장으로 자기소개 해줘.", max_tokens=50)
    print(f"[llm] 연결 테스트: {_test or '(응답 없음 — 설정을 확인하세요)'}")
else:
    print("[llm] LLM 미설정 — 규칙 기반 엔진만 사용합니다. (AZURE_OPENAI_ENDPOINT/DEPLOYMENT를 설정하면 자동 활성화)")'''),

md('''## 3. 데이터 소스 커넥터 계층
실제 연결이 안 되면(미설정/실패) `None`을 반환해 파이프라인이 합성 데이터로 자동 대체합니다.'''),

code('''"""데이터 소스 커넥터 — 각 함수는 (DataFrame, source_type, table_name) 튜플 또는 None을 반환한다."""
import pandas as pd
import numpy as np
import getpass
import sys
from datetime import datetime, timedelta


def _resolve_pwd(env_name: str) -> str:
    pwd = os.environ.get(env_name, "")
    if pwd:
        return pwd
    if sys.stdin.isatty():
        return getpass.getpass(f"{env_name} 미설정 — 비밀번호 직접 입력: ")
    return ""


def connect_postgres(cfg: dict, query: str, table_name: str):
    if not cfg.get("enabled"):
        return None
    try:
        import psycopg2
        pwd = _resolve_pwd(cfg["password_env"])
        conn = psycopg2.connect(host=cfg["host"], port=cfg["port"], dbname=cfg["dbname"],
                                 user=cfg["user"], password=pwd, connect_timeout=10)
        df = pd.read_sql(query, conn)
        conn.close()
        return df, "postgres", table_name
    except Exception as e:  # noqa: BLE001
        print(f"[postgres] 연결/조회 실패, 합성 데이터로 대체: {e}")
        return None


def connect_mysql(cfg: dict, query: str, table_name: str):
    if not cfg.get("enabled"):
        return None
    try:
        import pymysql
        pwd = _resolve_pwd(cfg["password_env"])
        conn = pymysql.connect(host=cfg["host"], port=cfg["port"], db=cfg["database"],
                                user=cfg["user"], password=pwd, connect_timeout=10)
        df = pd.read_sql(query, conn)
        conn.close()
        return df, "mysql", table_name
    except Exception as e:  # noqa: BLE001
        print(f"[mysql] 연결/조회 실패, 합성 데이터로 대체: {e}")
        return None


def connect_mssql(cfg: dict, query: str, table_name: str):
    if not cfg.get("enabled"):
        return None
    try:
        import pyodbc
        pwd = _resolve_pwd(cfg["password_env"])
        drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
        driver = drivers[0] if drivers else "ODBC Driver 17 for SQL Server"
        conn_str = (f"DRIVER={{{driver}}};SERVER={cfg['host']},{cfg['port']};"
                    f"DATABASE={cfg['database']};UID={cfg['user']};PWD={pwd};Encrypt=yes;")
        conn = pyodbc.connect(conn_str, timeout=10)
        df = pd.read_sql(query, conn)
        conn.close()
        return df, "mssql", table_name
    except Exception as e:  # noqa: BLE001
        print(f"[mssql] 연결/조회 실패, 합성 데이터로 대체: {e}")
        return None


def connect_hana(cfg: dict, query: str, table_name: str):
    """hana_diagnose.py와 동일한 hdbcli 연결 방식(userkey 우선, 없으면 host/user/password) 재사용."""
    if not cfg.get("enabled"):
        return None
    try:
        from hdbcli import dbapi
        if cfg.get("userkey"):
            conn = dbapi.connect(userkey=cfg["userkey"], encrypt=True, sslValidateCertificate=True)
        else:
            pwd = _resolve_pwd(cfg["password_env"])
            conn = dbapi.connect(address=cfg["host"], port=cfg["port"], user=cfg["user"],
                                  password=pwd, encrypt=True, sslValidateCertificate=True)
        cur = conn.cursor()
        cur.execute(query)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        conn.close()
        return pd.DataFrame(rows, columns=cols), "hana", table_name
    except Exception as e:  # noqa: BLE001
        print(f"[hana] 연결/조회 실패, 합성 데이터로 대체: {e}")
        return None


def read_onelake_table(lakehouse_path: str, table_name: str):
    """Fabric 환경에서만 실제 Delta 테이블을 PySpark로 읽는다(로컬/경로 미지정이면 None)."""
    if RUNTIME_ENV != "fabric" or not lakehouse_path:
        return None
    try:
        df_spark = spark.read.format("delta").load(f"{lakehouse_path}/Tables/{table_name}")  # noqa: F821 — Fabric 커널 내장 spark 세션
        return df_spark.limit(2000).toPandas(), "onelake", table_name
    except Exception as e:  # noqa: BLE001
        print(f"[onelake] 읽기 실패, 합성 데이터로 대체: {e}")
        return None


def read_databricks_table(cfg: dict, query: str, table_name: str):
    if not cfg.get("enabled"):
        return None
    try:
        from databricks import sql as dbsql
        token = os.environ.get(cfg["token_env"], "")
        conn = dbsql.connect(server_hostname=cfg["host"], http_path=cfg["http_path"], access_token=token)
        df = pd.read_sql(query, conn)
        conn.close()
        return df, "databricks", table_name
    except Exception as e:  # noqa: BLE001
        print(f"[databricks] 연결/조회 실패, 합성 데이터로 대체: {e}")
        return None'''),

md('## 4. 합성 데이터 (실제 연결이 없을 때의 대체 데이터)'),

code('''"""실제 연결과 동일한 (DataFrame, source_type, table_name) 형태를 반환 — 나중에 그대로 실제 연결로 교체 가능."""
def _synthetic_orders(n=500):
    rng = np.random.default_rng(42)
    base = datetime(2026, 1, 1)
    return pd.DataFrame({
        "order_id": np.arange(1, n + 1),
        "customer_id": rng.integers(1000, 1200, n),
        "order_date": [base + timedelta(days=int(d)) for d in rng.integers(0, 240, n)],
        "order_amount": rng.normal(85000, 30000, n).round(0),
        "shipping_delay_days": rng.integers(0, 10, n),
        "product_category": rng.choice(["전자", "의류", "식품", "생활용품"], n),
    })


def _synthetic_customers(n=1200):
    rng = np.random.default_rng(7)
    base = datetime(2026, 1, 1)
    return pd.DataFrame({
        "customer_id": np.arange(1000, 1000 + n),
        "signup_date": [base - timedelta(days=int(d)) for d in rng.integers(30, 900, n)],
        "email": [f"user{i}@example.com" for i in range(n)],
        "last_login_at": [base - timedelta(days=int(d)) for d in rng.integers(0, 200, n)],
        "total_spend": rng.normal(500000, 150000, n).round(0),
        "region": rng.choice(["서울", "부산", "대구", "경기"], n),
    })


def _synthetic_inventory(n=300):
    rng = np.random.default_rng(21)
    return pd.DataFrame({
        "sku": [f"SKU-{i:05d}" for i in range(n)],
        "warehouse_id": rng.integers(1, 6, n),
        "stock_qty": rng.integers(0, 500, n),
        "reorder_point": rng.integers(20, 100, n),
        "unit_cost": rng.normal(12000, 4000, n).round(0),
    })


SYNTHETIC_SOURCES = {
    "orders": (_synthetic_orders(), "onelake", "orders"),
    "customers": (_synthetic_customers(), "onelake", "customers"),
    "inventory": (_synthetic_inventory(), "databricks", "inventory"),
}'''),

md('''## 5. 소스 로딩 — 실제 연결 우선 시도, 실패/미설정 시 합성 데이터로 자동 대체
필요한 실제 테이블/쿼리로 아래 후보 목록을 그대로 교체하세요.'''),

code('''loaded_sources = {}

_orders_candidates = [
    connect_postgres(DATA_SOURCES["postgres"], "SELECT * FROM orders LIMIT 2000", "orders"),
    connect_mysql(DATA_SOURCES["mysql"], "SELECT * FROM orders LIMIT 2000", "orders"),
    connect_mssql(DATA_SOURCES["mssql"], "SELECT TOP 2000 * FROM orders", "orders"),
    read_onelake_table(DATA_SOURCES["onelake"]["lakehouse_path"], "orders"),
]
loaded_sources["orders"] = next((c for c in _orders_candidates if c is not None), SYNTHETIC_SOURCES["orders"])

_customers_candidates = [
    connect_postgres(DATA_SOURCES["postgres"], "SELECT * FROM customers LIMIT 2000", "customers"),
    read_onelake_table(DATA_SOURCES["onelake"]["lakehouse_path"], "customers"),
]
loaded_sources["customers"] = next((c for c in _customers_candidates if c is not None), SYNTHETIC_SOURCES["customers"])

_inventory_candidates = [
    connect_hana(DATA_SOURCES["hana"], "SELECT * FROM INVENTORY", "inventory"),
    read_databricks_table(DATA_SOURCES["databricks"], "SELECT * FROM inventory LIMIT 2000", "inventory"),
]
loaded_sources["inventory"] = next((c for c in _inventory_candidates if c is not None), SYNTHETIC_SOURCES["inventory"])

for name, (df, source_type, table_name) in loaded_sources.items():
    print(f"[load] {name}: {source_type}.{table_name} — {len(df)}행 x {len(df.columns)}열")'''),

md('''## 6. 데이터 프로파일링 엔진
null 비율, 카디널리티, 시계열/PII/ID 추정을 컬럼 단위로 계산합니다.'''),

code('''import re as _re

_PII_NAME_PATTERNS = _re.compile(r"(email|e-mail|phone|tel|ssn|rrn|주민|address|주소|name|이름)", _re.IGNORECASE)
_TIME_NAME_PATTERNS = _re.compile(r"(date|time|_at$|_dt$|일시|일자|날짜)", _re.IGNORECASE)
_ID_NAME_PATTERNS = _re.compile(r"(_id$|^id$|_no$|_key$|번호)", _re.IGNORECASE)


def profile_dataframe(df: pd.DataFrame, source_name: str, source_type: str, table_name: str) -> pd.DataFrame:
    rows = []
    n = len(df)
    for col in df.columns:
        series = df[col]
        null_ratio = float(series.isna().mean()) if n else 0.0
        nunique = int(series.nunique(dropna=True))
        cardinality_ratio = (nunique / n) if n else 0.0
        is_datetime = pd.api.types.is_datetime64_any_dtype(series) or bool(_TIME_NAME_PATTERNS.search(col))
        is_id = bool(_ID_NAME_PATTERNS.search(col)) or (cardinality_ratio > 0.95 and nunique > 20)
        is_pii = bool(_PII_NAME_PATTERNS.search(col))
        sample_values = series.dropna().astype(str).unique()[:3].tolist()
        rows.append({
            "source_name": source_name, "source_type": source_type, "table_name": table_name,
            "column": col, "dtype": str(series.dtype), "null_ratio": round(null_ratio, 3),
            "cardinality_ratio": round(cardinality_ratio, 3), "is_probable_datetime": is_datetime,
            "is_probable_id": is_id, "is_probable_pii": is_pii, "sample_values": sample_values,
        })
    return pd.DataFrame(rows)


profiles = pd.concat(
    [profile_dataframe(df, name, source_type, table_name)
     for name, (df, source_type, table_name) in loaded_sources.items()],
    ignore_index=True,
)
profiles'''),

md('## 7. 메타데이터 + 비즈니스 개념 매핑 (규칙 기반 + LLM 보완)'),

code('''"""컬럼 → 비즈니스 개념 매핑 — 규칙 기반 우선, 미매칭 컬럼은(LLM 사용 시) LLM에게 추정 요청."""
BUSINESS_CONCEPT_RULES = {
    "customer_id": ["customer_id", "cust_id", "고객id", "고객번호"],
    "order_date": ["order_date", "주문일", "주문일자"],
    "order_amount": ["order_amount", "amount", "금액", "매출"],
    "shipping_delay": ["shipping_delay", "delay", "배송지연"],
    "product_category": ["product_category", "category", "카테고리", "상품군"],
    "signup_date": ["signup_date", "가입일"],
    "last_login_at": ["last_login", "last_login_at", "최근로그인"],
    "customer_support_history": ["support", "ticket", "문의", "상담"],
    "total_spend": ["total_spend", "누적", "총구매", "ltv"],
    "region": ["region", "지역"],
    "stock_qty": ["stock_qty", "재고", "inventory_qty"],
    "reorder_point": ["reorder_point", "재주문", "안전재고"],
    "transaction_id": ["transaction_id", "거래id", "결제id"],
    "email": ["email", "이메일"],
}


def _rule_match_concept(column_name: str):
    col_lower = column_name.lower()
    for concept, keywords in BUSINESS_CONCEPT_RULES.items():
        if any(kw.lower() in col_lower for kw in keywords):
            return concept
    return None


def _llm_guess_concept(column_name: str, sample_values: list) -> str:
    if not LLM_ENABLED:
        return ""
    prompt = (f"컬럼명: {column_name}\\n샘플 값: {sample_values}\\n"
              "이 컬럼이 나타내는 비즈니스 개념을 영문 snake_case 한 단어(예: customer_id, order_amount)로만 답하라. "
              "설명 없이 단어만 출력하라.")
    return call_llm("You classify database columns into business concepts.", prompt, max_tokens=20)


def map_columns_to_concepts(profiles_df: pd.DataFrame, use_llm: bool = True) -> pd.DataFrame:
    concepts, matched_by_list = [], []
    for _, row in profiles_df.iterrows():
        concept = _rule_match_concept(row["column"])
        matched_by = "rule" if concept else ""
        if not concept and use_llm and LLM_ENABLED:
            guess = _llm_guess_concept(row["column"], row["sample_values"])
            if guess:
                concept, matched_by = guess.strip(), "llm"
        concepts.append(concept or None)
        matched_by_list.append(matched_by or "unmatched")
    result = profiles_df.copy()
    result["business_concept"] = concepts
    result["matched_by"] = matched_by_list
    return result


concept_map = map_columns_to_concepts(profiles, use_llm=True)
available_concepts = set(concept_map.loc[concept_map["business_concept"].notna(), "business_concept"])
concept_map'''),

md('## 8. 업무 시나리오 템플릿 라이브러리'),

code('''USE_CASE_TEMPLATES = [
    {"name": "수요 예측", "description": "과거 주문 추이로 향후 수요를 예측",
     "required_concepts": ["order_date", "order_amount", "product_category"],
     "nice_to_have_concepts": ["region"]},
    {"name": "고객 이탈 예측", "description": "이탈 가능성이 높은 고객을 사전에 식별",
     "required_concepts": ["customer_id", "last_login_at", "total_spend"],
     "nice_to_have_concepts": ["customer_support_history"]},
    {"name": "배송 지연 예측", "description": "주문 데이터로 배송 지연 가능성을 사전에 예측",
     "required_concepts": ["order_date", "shipping_delay", "region"],
     "nice_to_have_concepts": ["product_category"]},
    {"name": "이상 거래 탐지", "description": "비정상적인 결제/거래 패턴 탐지",
     "required_concepts": ["transaction_id", "order_amount", "customer_id"],
     "nice_to_have_concepts": []},
    {"name": "재고 최적화", "description": "재고 수준과 재주문 시점을 최적화",
     "required_concepts": ["stock_qty", "reorder_point"],
     "nice_to_have_concepts": ["order_date"]},
    {"name": "고객 세그멘테이션", "description": "구매 패턴 기반 고객 그룹화 및 맞춤 마케팅",
     "required_concepts": ["customer_id", "total_spend", "region"],
     "nice_to_have_concepts": ["signup_date"]},
]'''),

md('## 9. 시나리오 추천 엔진 (규칙 스코어링 + LLM 설명/브레인스토밍)'),

code('''def score_use_case(template: dict, available: set) -> dict:
    required = set(template["required_concepts"])
    nice = set(template["nice_to_have_concepts"])
    matched_required = required & available
    missing_required = required - available
    matched_nice = nice & available
    coverage = len(matched_required) / len(required) * 100 if required else 100.0
    return {
        "name": template["name"], "description": template["description"],
        "coverage_pct": round(coverage, 1),
        "matched_required": sorted(matched_required), "missing_required": sorted(missing_required),
        "matched_nice": sorted(matched_nice),
        "readiness": "즉시 구현 가능" if coverage >= 100 else
                     "데이터 보강 시 가능" if coverage >= 50 else "데이터 대폭 보강 필요",
    }


def generate_llm_explanation(scored: dict) -> str:
    if not LLM_ENABLED:
        return ""
    prompt = (f"시나리오: {scored['name']} ({scored['description']})\\n"
              f"보유 개념: {scored['matched_required']}\\n부족한 개념: {scored['missing_required']}\\n"
              "이 시나리오를 지금 데이터로 구현할 수 있는지, 부족한 부분은 무엇을 추가하면 되는지 "
              "한국어 2~3문장으로 실무자에게 설명하라.")
    return call_llm("You are a data strategy consultant explaining feasibility to a business stakeholder.",
                     prompt, max_tokens=250)


def brainstorm_additional_scenarios(available: set) -> str:
    """고정 템플릿 외에, 보유 개념만으로 LLM이 추가 시나리오를 자유롭게 제안."""
    if not LLM_ENABLED:
        return ""
    prompt = (f"보유한 비즈니스 데이터 개념 목록: {sorted(available)}\\n"
              "이 데이터만으로 시도해볼 수 있는 참신한 분석/업무 활용 시나리오를 한국어로 3개, "
              "각 1문장으로 제안하라.")
    return call_llm("You are a creative data product strategist.", prompt, max_tokens=300)


scored_scenarios = [score_use_case(t, available_concepts) for t in USE_CASE_TEMPLATES]
for s in scored_scenarios:
    s["llm_explanation"] = generate_llm_explanation(s)

scenario_df = pd.DataFrame(scored_scenarios).sort_values("coverage_pct", ascending=False)
scenario_df[["name", "coverage_pct", "readiness", "missing_required"]]'''),

md('## 10. 갭 분석 — 부족한 데이터 체크리스트'),

code('''def gap_report(scored: dict) -> str:
    if not scored["missing_required"]:
        return f"[{scored['name']}] 필요한 핵심 데이터가 모두 확보되어 있습니다."
    missing_str = ", ".join(scored["missing_required"])
    return f"[{scored['name']}] '{missing_str}' 데이터가 추가로 필요합니다."


print("=== 갭 분석 체크리스트 ===")
for s in scored_scenarios:
    print(gap_report(s))

extra_ideas = brainstorm_additional_scenarios(available_concepts)
if extra_ideas:
    print("\\n=== LLM 추가 시나리오 제안 ===")
    print(extra_ideas)
else:
    print("\\n(LLM 미설정 — AZURE_OPENAI_ENDPOINT/DEPLOYMENT를 채우면 추가 시나리오 브레인스토밍이 활성화됩니다)")'''),

md('## 11. 결과 대시보드'),

code('''import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(scenario_df["name"], scenario_df["coverage_pct"], color="#3a7bd9")
ax.set_xlabel("커버리지 (%)")
ax.set_xlim(0, 100)
ax.set_title("보유 데이터 기반 업무 시나리오 준비도")
plt.tight_layout()
plt.show()

print("\\n=== 시나리오 카드 ===")
for s in scored_scenarios:
    print(f"\\n### {s['name']} — {s['coverage_pct']}% ({s['readiness']})")
    print(s["description"])
    if s["llm_explanation"]:
        print(f"[LLM] {s['llm_explanation']}")
    print(gap_report(s))'''),

md('''## 12. 다음 단계 (해커톤 → 실제 배포)

- **OneLake 실제 연결**: `read_onelake_table()`은 이미 Fabric 커널의 내장 `spark` 세션으로 Delta 테이블을 읽도록 작성돼 있습니다 — Fabric Notebook에서 `RUNTIME_ENV="fabric"` + `ONELAKE_LAKEHOUSE_PATH`만 채우면 자동으로 실제 데이터로 전환됩니다.
- **Databricks 실제 연결**: `DATABRICKS_HOST`/`DATABRICKS_HTTP_PATH`/`DATABRICKS_TOKEN`(환경변수)을 채우면 `databricks-sql-connector`로 실제 조회됩니다(`pip install databricks-sql-connector` 필요).
- **자격 증명 보안**: 지금은 환경변수/`.env` 방식이지만, 실제 배포 시에는 Azure Key Vault 또는 Fabric 자체 연결(데이터 소스 자격 증명) 기능으로 이전하는 것을 권장합니다.
- **Power BI 연동**: `scenario_df`를 Fabric Lakehouse 테이블로 저장(`df.to_parquet` 또는 Fabric의 `write.format("delta")`)하면 Power BI에서 바로 "추천 유스케이스 카드" 리포트로 연결할 수 있습니다.
- **시나리오 템플릿 확장**: `USE_CASE_TEMPLATES`에 항목을 추가하기만 하면 되고, 코드 변경은 필요 없습니다.'''),
]

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

with open("usecase_advisor.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("저장 완료: usecase_advisor.ipynb")
