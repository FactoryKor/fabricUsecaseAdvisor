# Fabric UseCase Advisor

**Language: [한국어](README.md) | English**

Prototype pipeline for "Data sources → Use-case recommendations → Gap analysis" + an introductory slide deck.

## Folder contents

| File | Description |
|---|---|
| `usecase_advisor.ipynb` | Runnable pipeline notebook (data profiling → business concept mapping → scenario recommendation → gap analysis → dashboard) |
| `build_notebook.py` | Script that generates the notebook above (edit this script and re-run it if you want to change the notebook's content) |
| `Fabric_UseCase_Advisor_소개.pptx` | Introductory slide deck (12 slides) |
| `build_ppt.py` | Script that generates the PPT above (edit this script and re-run it to change text/design) |

`.ipynb`/`.pptx` are **generated outputs** of `build_notebook.py`/`build_ppt.py` respectively — don't edit the generated files directly; edit the script and re-run it (re-running overwrites the same filename).

---

## 1. Installation

Python 3.10+ is required.

```powershell
cd "Fabric-UseCase-Advisor"
pip install pandas numpy psycopg2-binary pymysql pyodbc hdbcli azure-identity "openai>=1.30.0" python-dotenv matplotlib python-pptx jupyter
```

- To actually connect to SQL Server via `pyodbc`, **ODBC Driver 17 or 18 for SQL Server** must be installed on the system (if missing, that source alone falls back to synthetic data automatically and the rest still works).
- The notebook's first cell (`%pip install ...`) installs the packages above automatically, so if you're opening the notebook directly in Jupyter/Fabric you don't need to do this step beforehand.

---

## 2. Using the notebook (`usecase_advisor.ipynb`)

### 2-1. Open it
```powershell
jupyter notebook usecase_advisor.ipynb
```
Or open the file in VS Code and select a local Python kernel (or a Fabric Notebook kernel).

### 2-2. Choose the runtime environment
Change the `RUNTIME_ENV` value in the "1. Settings" cell directly.

| Value | Meaning |
|---|---|
| `local` (default) | Local Jupyter/VS Code. OneLake is replaced with synthetic data |
| `fabric` | Microsoft Fabric Notebook. If `ONELAKE_LAKEHOUSE_PATH` is set, real Delta tables are read via PySpark |

### 2-3. LLM (Azure OpenAI) settings — optional
If left blank, the entire pipeline runs on rule-based logic only. To enable it, fill in the following environment variables (or a `.env` file).

| Environment variable | Description | Default |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | e.g. `https://<resource>.openai.azure.com/` | (none → LLM disabled) |
| `AZURE_OPENAI_DEPLOYMENT` | The **deployment name** you want (not the model name). e.g. `gpt-4o-mini`, `gpt-5.6-sol` — check the "Deployments" list in Azure AI Foundry | (none) |
| `AZURE_OPENAI_AUTH_MODE` | `aad` (Windows/Entra ID account auth, for when company policy blocks API keys) or `key` | `aad` |
| `AZURE_OPENAI_API_KEY` | Only needed when `AZURE_OPENAI_AUTH_MODE=key` | (none) |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-08-01-preview` |

With `AZURE_OPENAI_AUTH_MODE=aad` (default), a sign-in prompt may appear on first run (Azure CLI `az login` or a browser sign-in). The account must already have the **`Cognitive Services OpenAI User`** role on that Azure OpenAI resource.

### 2-4. Connecting data sources — optional
If nothing is configured, the whole pipeline runs on **synthetic (fake) data**. To connect real data, fill in the environment variables below per source (passwords are only ever passed via environment variables, never hardcoded in the code/notebook).

**PostgreSQL**
```powershell
$env:PG_HOST = "myserver.postgres.database.azure.com"
$env:PG_PORT = "5432"          # optional (default shown)
$env:PG_DBNAME = "appdb"       # defaults to postgres if omitted
$env:PG_USER = "diag_reader"
$env:PG_DIAGNOSE_PASSWORD = "..."   # if not set, you'll be prompted interactively
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

**SAP HANA** (same approach as `hana_diagnose.py` — using an `hdbuserstore` key is recommended)
```powershell
$env:HANA_USERKEY = "MYHANAKEY"     # hdbuserstore SET MYHANAKEY <host>:<port> <user> <password>
# or specify host/user/password directly:
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
Install `pip install databricks-sql-connector` if you want to use the Databricks connection.

**OneLake / Lakehouse**
Only active when `RUNTIME_ENV=fabric` and running inside a Fabric Notebook.
```powershell
$env:ONELAKE_LAKEHOUSE_PATH = "abfss://<workspace>@onelake.dfs.fabric.microsoft.com/<lakehouse>.Lakehouse"
```

> Any source that fails to connect or has no environment variables set automatically falls back to synthetic data, so the **notebook always runs to completion** (it never stops on an error).

### 2-5. Running it
Run the cells in order from top to bottom (each cell relies on variables defined in earlier cells).

1. Install packages
2. Settings (runtime environment / LLM / data sources)
3. Initialize the LLM client (prints a connectivity test message)
4. Define data source connectors
5. Define synthetic data
6. Load sources (tries real connections first, falls back to synthetic data on failure)
7. Data profiling
8. Business concept mapping
9. Define use-case scenario templates
10. Scenario recommendation scoring
11. Print the gap-analysis checklist
12. Dashboard (bar chart + scenario cards)

### 2-6. Customization
- **Add/change business scenarios**: add entries to the `USE_CASE_TEMPLATES` list in the "8. Business scenario template library" cell (no code logic changes needed).
- **Add business-concept mapping rules**: add keywords to the `BUSINESS_CONCEPT_RULES` dictionary in the "7. Metadata + business concept mapping" cell.
- **Swap in real tables/queries**: edit queries like `SELECT * FROM orders LIMIT 2000` in the "5. Source loading" cell to match your actual schema.

---

## 3. Using the PPT (`Fabric_UseCase_Advisor_소개.pptx`)

### 3-1. Just viewing it
Open `Fabric_UseCase_Advisor_소개.pptx` with PowerPoint (or a compatible viewer). No extra installation needed.

### 3-2. Editing and regenerating it
```powershell
pip install python-pptx
python build_ppt.py
```
Edit the slide text/tables/colors inside `build_ppt.py` and re-run it — it overwrites the same filename.

---

## 4. Security notes

- All DB passwords are passed **only via environment variables** (never hardcode them in code/notebooks). If unset, you'll be prompted interactively.
- For production use, it's recommended to move away from environment variables toward **Azure Key Vault** or Fabric's own data-source credential features.
- This prototype only performs **read-only (SELECT)** queries against every source and never writes to any of them.
