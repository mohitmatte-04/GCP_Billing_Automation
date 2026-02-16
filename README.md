# 💰 GCP Resource-Level Cost Attribution Tool

> Automatically break down your GCP bill to **individual resources** and **attribute costs to the person who created them**.

---

## 🎯 Problem

GCP billing reports only show **total cost per SKU** — e.g., *"Cloud Run Memory = $204"*. But you don't know:
- **Which** Cloud Run service is costing the most?
- **Who** deployed it?
- **How much** is each person's infrastructure costing?

This tool answers all three.

---

## 🏗️ Architecture

### High-Level Design

```
┌─────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  Billing CSV     │     │  GCP APIs             │     │  Output Reports  │
│  (downloaded     │────▶│  (gcloud CLI +        │────▶│  (Excel + CSV)   │
│   from Console)  │     │   Cloud Monitoring +  │     │                  │
│                  │     │   Audit Logs)         │     │                  │
│  "WHAT was       │     │  "WHICH resource      │     │  "WHO spent      │
│   spent"         │     │   used HOW MUCH"      │     │   HOW MUCH"      │
└─────────────────┘     └──────────────────────┘     └──────────────────┘
```

### Low-Level Design

```
                        ┌─────────────────────────────┐
                        │      Billing CSV (Input)     │
                        │  Service | SKU | Cost | Usage│
                        └──────────────┬──────────────┘
                                       │
                              ┌────────▼────────┐
                              │  Top 10 SKUs by  │
                              │  Cost (sorted)   │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                   │
              ┌─────▼─────┐    ┌──────▼──────┐    ┌──────▼──────┐
              │  gcloud    │    │  Cloud       │    │  Fallback   │
              │  CLI       │    │  Monitoring  │    │  (Audit     │
              │  Commands  │    │  API         │    │   Logs)     │
              └─────┬─────┘    └──────┬──────┘    └──────┬──────┘
              Cloud SQL         Cloud Run          Unmapped
              Compute Engine    Cloud Functions    Services
              App Engine                              │
              Vertex AI              │                │
                    │                │                 │
                    └────────────────┼─────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  Per-Resource Usage  │
                          │  + Cost Share        │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  Audit Logs API      │
                          │  → Creator per       │
                          │    Resource           │
                          └──────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                                  │
          ┌────────▼─────────┐            ┌───────────▼──────────┐
          │ resource_cost_   │            │ person_cost_         │
          │ breakdown.xlsx   │            │ summary.xlsx         │
          │ (Detailed)       │            │ (Per Person)         │
          └──────────────────┘            └──────────────────────┘
```

---

## 📊 Cost Calculation Methods Per Service

| Service | Method | Data Source | What We Measure | Accuracy |
|:--------|:-------|:-----------|:----------------|:---------|
| ☁️ **Cloud SQL** | `gcloud` CLI | `gcloud sql instances list` | CPU count & RAM from machine tier | ~100% |
| 🖥️ **Compute Engine (VMs)** | `gcloud` CLI | `gcloud compute instances list` | Machine type of RUNNING VMs | ~100% |
| 💾 **Compute Engine (Disks)** | `gcloud` CLI | `gcloud compute disks list` | Disk size in GB | ~100% |
| 🚀 **App Engine Flex** | `gcloud` CLI | `gcloud app versions describe` | CPU & RAM per SERVING version | ~90% |
| 🏃 **Cloud Run** | Cloud Monitoring API | `billable_instance_time` metric | Actual billed seconds per service | ~95% |
| ⚡ **Cloud Functions** | Cloud Monitoring API | `execution_times` / `execution_count` | Execution duration per function | ~90% |
| 🤖 **Vertex AI** | `gcloud` CLI | `gcloud ai endpoints list` | Machine type × replica count | ~95% |
| ❓ **Other Services** | Audit Logs (fallback) | `cloudaudit.googleapis.com` | Resource count per creator | ~60% |

---

## 🔧 gcloud Commands Used

| Command | Purpose | Key Output Fields |
|:--------|:--------|:-----------------|
| `gcloud sql instances list --format=json` | Get all Cloud SQL instances | `name`, `settings.tier`, `region`, `state` |
| `gcloud compute instances list --format=json` | Get all VMs | `name`, `machineType`, `zone`, `status` |
| `gcloud compute disks list --format=json` | Get all persistent disks | `name`, `sizeGb`, `type`, `zone` |
| `gcloud app versions list --format=json` | List App Engine versions | `service`, `id`, `environment` |
| `gcloud app versions describe <id> --service=<svc>` | Get version details | `servingStatus`, `resources.cpu`, `resources.memoryGb` |
| `gcloud ai endpoints list --region=<r> --format=json` | Get Vertex AI endpoints | `displayName`, `deployedModels.machineSpec`, `minReplicaCount` |

---

## 📈 Cloud Monitoring Metrics Used

| Metric | Service | What It Measures |
|:-------|:--------|:-----------------|
| `run.googleapis.com/container/billable_instance_time` | Cloud Run | Seconds each service was billed (the exact data Google uses for billing) |
| `cloudfunctions.googleapis.com/function/execution_times` | Cloud Functions | Total execution time in nanoseconds per function |
| `cloudfunctions.googleapis.com/function/execution_count` | Cloud Functions (fallback) | Number of invocations per function |

**Server-side aggregation** is used to avoid downloading millions of data points:
```python
aggregation = {
    "alignment_period": 30 days,         # Treat entire period as one bucket
    "per_series_aligner": ALIGN_SUM,      # Sum all data points per series
    "cross_series_reducer": REDUCE_SUM,   # Sum across revisions
    "group_by_fields": ["service_name"],  # One result per service
}
```

---

## 📋 Output Columns

| Column | Source | Description |
|:-------|:-------|:-----------|
| **Service** | Billing CSV | GCP service name (e.g., Cloud Run, Cloud SQL) |
| **SKU** | Billing CSV | Specific billing line item |
| **Total SKU Cost** | Billing CSV | Total cost for this SKU across all resources |
| **Unit Price** | Calculated | `Total Cost ÷ Total Usage` |
| **Usage Unit** | Billing CSV | Unit of measurement (hours, GiB-seconds, etc.) |
| **Resource** | gcloud / Monitoring | Individual resource name (matches GCP Console) |
| **Resource Usage** | Calculated | `Total Usage × Share %` |
| **Usage Share %** | gcloud / Monitoring | This resource's proportion of total usage |
| **Actual Cost** | Calculated | `Total SKU Cost × Share %` |
| **Created By** | Audit Logs | Email of the person who created the resource |
| **Method** | Script | How the cost was calculated |

---

## ⚙️ Setup & Usage

### Prerequisites
- Python 3.8+
- Google Cloud SDK (`gcloud`) installed and authenticated
- Access to the GCP project

### Installation
```bash
# Clone the repo
git clone <repo-url>
cd billing_report

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Authenticate with GCP
gcloud auth application-default login
```

### Configuration
Edit `config.py`:
```python
PROJECT_ID = "your-project-id"
DAYS_BACK = 30    # Lookback period for Audit Logs
```

### Run
1. Download billing CSV from **GCP Console → Billing → Reports → Download CSV**
2. Place the CSV in the project folder
3. Run:
```bash
python resource_cost_breakdown.py
```

### Output
- `resource_cost_breakdown.xlsx` — Detailed cost per resource
- `person_cost_summary.xlsx` — Total cost per person

---

## 📁 Project Structure

```
billing_report/
├── config.py                    # Project ID, lookback period, service mappings
├── resource_cost_breakdown.py   # Main script — resource-level cost attribution
├── generate_report.py           # Legacy report generator (audit log based)
├── requirements.txt             # Python dependencies
├── .gitignore                   # Excludes .venv, output files
├── README.md                    # This file
└── Billing_report*.csv          # Input: downloaded from GCP Console
```

---

## 🔑 APIs & Permissions Required

| API | Used For |
|:----|:---------|
| Cloud Logging API (`logging.googleapis.com`) | Querying Audit Logs for resource creators |
| Cloud Monitoring API (`monitoring.googleapis.com`) | Getting usage metrics for Cloud Run & Cloud Functions |

**IAM Roles needed:**
- `roles/logging.viewer` — Read audit logs
- `roles/monitoring.viewer` — Read monitoring metrics
- `roles/viewer` — Run `gcloud` list commands

---

## 🧮 Cost Calculation Formula

```
For each Top 10 SKU:

  Unit Price = Total SKU Cost ÷ Total Usage
                (from CSV)       (from CSV)

  Resource Share = Resource Usage ÷ Sum of All Resources' Usage
                    (from gcloud       (from gcloud
                     or Monitoring)     or Monitoring)

  Actual Cost = Total SKU Cost × Resource Share
```

**Example:**
```
Cloud SQL vCPU SKU = $146.48 total

  adk-session-db:     4 CPUs → 4/7 = 57.1% → $83.70
  rdeandrade-test:    2 CPUs → 2/7 = 28.6% → $41.85
  spark-mysql-authdb: 1 CPU  → 1/7 = 14.3% → $20.93
                                      100%    $146.48 ✅
```
