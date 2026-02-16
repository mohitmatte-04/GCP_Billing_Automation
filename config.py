# GCP Project Configuration

# Your Google Cloud Project ID
PROJECT_ID = "YOUR_PROJECT_NAME"

# Look back period in days for Audit Logs
DAYS_BACK = 30

# Mapping from Billing Report 'Service description' to Cloud Logging 'serviceName'
# This maps the human-readable name in your CSV to the internal API name.
SERVICE_MAPPING = {
    "Cloud Run": "run.googleapis.com",
    "Cloud SQL": "sqladmin.googleapis.com", 
    "Vertex AI": "aiplatform.googleapis.com",
    "App Engine": "appengine.googleapis.com",
    "Compute Engine": "compute.googleapis.com",
    "Cloud Run Functions": "cloudfunctions.googleapis.com",
    "Cloud Workstations": "workstations.googleapis.com",
    "Notebooks": "notebooks.googleapis.com",
    "Cloud Spanner": "spanner.googleapis.com",
    "Kubernetes Engine": "container.googleapis.com",
    "Integration Connectors": "connectors.googleapis.com",
    "Gemini API": "aiplatform.googleapis.com", # Often under AI Platform types
    "Networking": "compute.googleapis.com",    # Networking resources like LBs are usually under Compute
    "Artifact Registry": "artifactregistry.googleapis.com",
    "Cloud Monitoring": "monitoring.googleapis.com",
    "Secret Manager": "secretmanager.googleapis.com",
    "BigQuery": "bigquery.googleapis.com",
    "Cloud Storage": "storage.googleapis.com",
    "Dataplex": "dataplex.googleapis.com",
    "Cloud DNS": "dns.googleapis.com",
    "Cloud Build": "cloudbuild.googleapis.com",
    "Firebase App Hosting": "firebaseapphosting.googleapis.com",
    "Cloud Pub/Sub": "pubsub.googleapis.com",
    "VM Manager": "compute.googleapis.com",
    "Cloud Logging": "logging.googleapis.com"
}
