# BrightLife Care — Cohort & Retention Studio

A self-contained web application that ingests an orders dataset and produces a cohort retention, lifetime value, and channel performance dashboard.

**Live in one command. No database. No paid services.**

---

## Setup & Run

### Prerequisites
- Python 3.9+
- pip

### Install & Launch

```bash
git clone <your-repo-url>
cd brightlife_app
pip install -r requirements.txt
streamlit run app.py
```

App opens automatically at `http://localhost:8501`

### Use your own data

Upload any CSV via the sidebar file uploader — or replace `data/orders.csv` with your own file matching the schema below.

---

## Schema Assumptions

| Column | Type | Notes |
|---|---|---|
| `order_id` | string | Unique per order; duplicates are deduplicated (first kept) |
| `customer_id` | string | Used to define cohorts by first purchase month |
| `order_date` | datetime | Mixed formats and timezone offsets (e.g. `+05:30`) are normalised to UTC |
| `gross_revenue` | float | Negative values (refunds) are excluded; missing values are dropped |
| `channel` | string | Missing values filled as `unknown`; lowercased and trimmed |
| `product_category` | string | Used for filtering; no imputation applied |

---

## Data Cleaning Applied

- **Timezone normalisation:** Both naive datetimes and ISO 8601 timestamps with offsets are parsed and converted to UTC
- **Duplicate order IDs:** 9 duplicates found in sample data — first occurrence retained
- **Missing revenue:** 30 rows with null `gross_revenue` dropped
- **Negative revenue:** Excluded (treated as refunds / data errors)
- **Missing channel:** 12 rows — filled with `"unknown"`
- **Deterministic output:** `@st.cache_data` ensures identical inputs always produce identical outputs

---

## Dashboard Views

| Tab | Description |
|---|---|
| Cohort Retention Heatmap | % of each monthly cohort returning in subsequent months |
| Lifetime Value by Channel | Average and total LTV grouped by acquisition channel |
| Cumulative Revenue per Cohort | Revenue accumulated per customer over time, by cohort |
| Channel Comparison | Orders, revenue, AOV, and repeat purchase rate per channel |

---

## LTV Definition & Limitations

See `ltv_note.md` for the full written note on how the LTV definition could mislead stakeholders and how to mitigate it.

---

## Known Limitations

- **No statistical significance testing** — retention and LTV differences between channels are descriptive, not tested
- **LTV is historical only** — it reflects observed revenue, not predicted future revenue
- **Single-touch attribution** — channel is assigned based on the customer's first order only; cross-channel journeys are not modelled
- **Cohort size varies** — newer cohorts have fewer months of data, making their cumulative revenue curves appear lower; this is a data maturity effect, not performance

---

## License

MIT License — free to use, modify, and distribute.
