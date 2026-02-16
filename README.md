# GCP Billing & Resource Creation Report Generator

This tool generates a report identifying the top 10 cost-consuming services on Google Cloud Platform (GCP) and lists the resources created for those services in the last 365 days, including the creator's email and timestamp.

## Prerequisites

1.  **Python 3.7+** installed.
2.  **Google Cloud SDK** installed and initialized.
3.  **BigQuery Export for Billing** enabled in your GCP project.
4.  **BigQuery Export for Audit Logs** enabled in your GCP project (specifically for Admin Activity logs).

## Setup

1.  **Install Dependencies**:
    Open a terminal in this folder and run:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Your Project**:
    Open `config.py` and update the following variables with your specific GCP details:
    *   `PROJECT_ID`: Your Google Cloud Project ID.
    *   `DATASET_ID`: The dataset ID containing your billing and audit log tables.
    *   `BILLING_TABLE_ID`: The table ID for your billing export (e.g., `gcp_billing_export_v1_...`).
    *   `AUDIT_LOG_TABLE_ID`: The table ID for your audit logs (e.g., `cloudaudit_googleapis_com_activity`).

3.  **Authenticate**:
    Run the following command to authenticate your local environment with GCP:
    ```bash
    gcloud auth application-default login
    ```

## Usage

Run the script to generate the report:

```bash
python generate_report.py
```

## Output

The script will generate two files:
1.  `top_10_costs.csv`: A list of the top 10 services and SKUs by cost.
2.  `gcp_resource_creation_report.csv` (and `.xlsx`): A detailed list of resources created in the last 365 days for those top services, including:
    *   Timestamp
    *   Service Category
    *   Created By (Principal Email)
    *   Resource Name
    *   Method Used (e.g., `v1.compute.instances.insert`)
