# Fabric UseCase Advisor

"데이터 소스 → 활용 시나리오 추천 → 갭 분석" 파이프라인 프로토타입 + 소개 PPT.

## 폴더 구성

| 파일 | 설명 |
|---|---|
| `usecase_advisor.ipynb` | 실행 가능한 파이프라인 노트북(데이터 프로파일링 → 비즈니스 개념 매핑 → 시나리오 추천 → 갭 분석 → 대시보드) |
| `build_notebook.py` | 위 노트북을 생성하는 스크립트(노트북 내용을 고치고 싶으면 이 스크립트를 수정 후 재실행) |
| `Fabric_UseCase_Advisor_소개.pptx` | 개념 설명용 발표자료(12장) |
| `build_ppt.py` | 위 PPT를 생성하는 스크립트(문구/디자인 수정 시 이 스크립트를 수정 후 재실행) |

`.ipynb`/`.pptx`는 각각 `build_notebook.py`/`build_ppt.py`의 **산출물**입니다 — 내용을 바꾸고 싶으면 결과 파일을 직접 편집하지 말고 스크립트를 고친 뒤 다시 실행하세요(재실행 시 같은 파일명으로 덮어씁니다).

---

## 1. 설치

Python 3.10+ 가 설치되어 있어야 합니다.

```powershell
cd "Fabric-UseCase-Advisor"
pip install pandas numpy psycopg2-binary pymysql pyodbc hdbcli azure-identity "openai>=1.30.0" python-dotenv matplotlib python-pptx jupyter
```

- `pyodbc`로 SQL Server에 실제 연결하려면 시스템에 **ODBC Driver 17 또는 18 for SQL Server**가 설치되어 있어야 합니다(미설치 시 해당 소스만 자동으로 합성 데이터로 대체되고 나머지는 정상 동작).
- 노트북의 첫 셀(`%pip install ...`)이 위 패키지를 자동으로 설치해주므로, Jupyter/Fabric에서 노트북을 열어 실행할 경우 이 단계를 미리 안 해도 됩니다.

---

## 2. 노트북 사용법 (`usecase_advisor.ipynb`)

### 2-1. 열기
```powershell
jupyter notebook usecase_advisor.ipynb
```
또는 VS Code에서 파일을 열고 커널로 로컬 Python(또는 Fabric Notebook)을 선택합니다.

### 2-2. 실행 환경 선택
"1. 설정" 셀의 `RUNTIME_ENV` 값을 직접 바꿉니다.

| 값 | 의미 |
|---|---|
| `local`(기본값) | 로컬 Jupyter/VS Code. OneLake는 합성 데이터로 대체됨 |
| `fabric` | Microsoft Fabric Notebook. `ONELAKE_LAKEHOUSE_PATH`를 채우면 실제 Delta 테이블을 PySpark로 읽음 |

### 2-3. LLM(Azure OpenAI) 설정 — 선택 사항
비워두면 규칙 기반만으로 전체 파이프라인이 동작합니다. 사용하려면 아래 환경변수(또는 `.env` 파일)를 채우세요.

| 환경변수 | 설명 | 기본값 |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | 예: `https://<resource>.openai.azure.com/` | (없음 → LLM 비활성) |
| `AZURE_OPENAI_DEPLOYMENT` | **원하는 배포 이름**(모델 이름 아님). 예: `gpt-4o-mini`, `gpt-5.6-sol` 등 Azure AI Foundry의 "배포" 목록에서 확인 | (없음) |
| `AZURE_OPENAI_AUTH_MODE` | `aad`(Windows/Entra ID 계정 인증, 회사 정책으로 API 키가 막힌 경우) 또는 `key` | `aad` |
| `AZURE_OPENAI_API_KEY` | `AZURE_OPENAI_AUTH_MODE=key`일 때만 필요 | (없음) |
| `AZURE_OPENAI_API_VERSION` | API 버전 | `2024-08-01-preview` |

`AZURE_OPENAI_AUTH_MODE=aad`(기본값)로 실행하면 최초 실행 시 로그인 창이 뜰 수 있습니다(Azure CLI `az login` 또는 브라우저 로그인). 사전에 해당 Azure OpenAI 리소스에 대해 **`Cognitive Services OpenAI User`** 역할이 계정에 부여되어 있어야 합니다.

### 2-4. 데이터 소스 연결 — 선택 사항
아무 것도 설정하지 않으면 **합성(가짜) 데이터**로 전체 파이프라인이 실행됩니다. 실제 데이터를 연결하려면 소스별로 아래 환경변수를 채우세요(비밀번호는 코드/노트북에 직접 쓰지 않고 환경변수로만 전달합니다).

**PostgreSQL**
```powershell
$env:PG_HOST = "myserver.postgres.database.azure.com"
$env:PG_PORT = "5432"          # 생략 가능(기본값)
$env:PG_DBNAME = "appdb"       # 생략 시 postgres
$env:PG_USER = "diag_reader"
$env:PG_DIAGNOSE_PASSWORD = "..."   # 미설정 시 실행 중 프롬프트로 입력받음
```

**MySQL**
```powershell
$env:MYSQL_HOST = "myserver.mysql.database.azure.com"
$env:MYSQL_DATABASE = "appdb"
$env:MYSQL_USER = "diag_reader"
$env:MYSQL_DIAGNOSE_PASSWORD = "..."
```

**SQL Server (MSSQL)**
```powershell
$env:MSSQL_HOST = "sqlsrv01.corp.local"
$env:MSSQL_DATABASE = "appdb"
$env:MSSQL_USER = "diag_reader"
$env:MSSQL_DIAGNOSE_PASSWORD = "..."
```

**SAP HANA** (`hana_diagnose.py`와 동일한 방식 — `hdbuserstore` 키 권장)
```powershell
$env:HANA_USERKEY = "MYHANAKEY"     # hdbuserstore SET MYHANAKEY <host>:<port> <user> <password>
# 또는 host/user/password 직접 지정:
$env:HANA_HOST = "hana01.corp.local"
$env:HANA_USER = "diag_reader"
$env:HANA_DIAGNOSE_PASSWORD = "..."
```

**Databricks**
```powershell
$env:DATABRICKS_HOST = "adb-xxxx.azuredatabricks.net"
$env:DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/xxxx"
$env:DATABRICKS_TOKEN = "..."
```
Databricks 연결을 쓰려면 `pip install databricks-sql-connector`를 추가로 설치하세요.

**OneLake / Lakehouse**
`RUNTIME_ENV=fabric`이고 Fabric Notebook에서 실행 중일 때만 동작합니다.
```powershell
$env:ONELAKE_LAKEHOUSE_PATH = "abfss://<workspace>@onelake.dfs.fabric.microsoft.com/<lakehouse>.Lakehouse"
```

> 연결이 실패하거나 환경변수를 설정하지 않은 소스는 자동으로 합성 데이터로 대체되어 **노트북이 항상 끝까지 실행**됩니다(오류로 멈추지 않음).

### 2-5. 실행
셀을 위에서부터 순서대로 실행합니다(각 셀이 이전 셀의 변수를 그대로 사용).

1. 패키지 설치
2. 설정(실행 환경/LLM/데이터 소스)
3. LLM 클라이언트 초기화(연결 테스트 메시지 출력)
4. 데이터 소스 커넥터 정의
5. 합성 데이터 정의
6. 소스 로딩(실제 연결 우선 시도 → 실패 시 합성 데이터)
7. 데이터 프로파일링
8. 비즈니스 개념 매핑
9. 업무 시나리오 템플릿 정의
10. 시나리오 추천 스코어링
11. 갭 분석 체크리스트 출력
12. 대시보드(막대그래프 + 시나리오 카드)

### 2-6. 커스터마이징
- **업무 시나리오 추가/변경**: "8. 업무 시나리오 템플릿 라이브러리" 셀의 `USE_CASE_TEMPLATES` 리스트에 항목을 추가하면 됩니다(코드 로직 변경 불필요).
- **비즈니스 개념 매핑 규칙 추가**: "7. 메타데이터 + 비즈니스 개념 매핑" 셀의 `BUSINESS_CONCEPT_RULES` 딕셔너리에 키워드를 추가하세요.
- **실제 테이블/쿼리로 교체**: "5. 소스 로딩" 셀의 `SELECT * FROM orders LIMIT 2000` 같은 쿼리를 실제 스키마에 맞게 수정하세요.

---

## 3. PPT 사용법 (`Fabric_UseCase_Advisor_소개.pptx`)

### 3-1. 보기만 할 경우
PowerPoint(또는 호환 뷰어)로 `Fabric_UseCase_Advisor_소개.pptx`를 열면 됩니다. 추가 설치가 필요 없습니다.

### 3-2. 내용을 수정하고 재생성할 경우
```powershell
pip install python-pptx
python build_ppt.py
```
`build_ppt.py` 안의 슬라이드 텍스트/표/색상을 수정한 뒤 다시 실행하면 같은 파일명으로 덮어씁니다.

---

## 4. 보안 참고

- 모든 DB 비밀번호는 **환경변수로만** 전달합니다(코드/노트북에 하드코딩하지 마세요). 미설정 시 대화형 프롬프트로 입력받습니다.
- 실제 운영 전환 시에는 환경변수 대신 **Azure Key Vault** 또는 Fabric의 자체 데이터 소스 자격 증명 기능으로 이전하는 것을 권장합니다.
- 이 프로토타입은 모든 데이터 조회가 **읽기 전용(SELECT)**이며, 어떤 소스에도 쓰기 작업을 하지 않습니다.
