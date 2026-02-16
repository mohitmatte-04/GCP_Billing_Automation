import os
# Force REST transport to avoid gRPC IOCP/Socket errors on Windows
os.environ["GOOGLE_CLOUD_DISABLE_GRPC"] = "true"

from google.cloud import logging
import pandas as pd
import config
from datetime import datetime, timedelta, timezone
import sys
import glob
import time

def get_logging_client():
    try:
        return logging.Client(project=config.PROJECT_ID)
    except Exception as e:
        print(f"Failed to create Logging client: {e}")
        return None

def find_billing_csv():
    """Finds the most recent Billing CSV."""
    csv_files = glob.glob("*.csv")
    input_csvs = [f for f in csv_files if "gcp_created_resources" not in f and "top_10" not in f and "gcp_creation_audit_report" not in f]
    
    if not input_csvs:
        return None
    return input_csvs[0]

def analyze_billing_data(csv_path):
    print(f"Reading billing data from: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
        if "Cost ($)" in df.columns:
            df["Cost ($)"] = df["Cost ($)"].replace(r'[$,]', '', regex=True).astype(float)
            
        # Group by Service AND SKU to get top cost drivers at SKU level
        top_sku_df = df.groupby(["Service description", "SKU description"])["Cost ($)"].sum().reset_index()
        top_sku_df = top_sku_df.sort_values(by="Cost ($)", ascending=False).head(10)
        
        print("\nTop 10 SKUs by Cost:")
        print(top_sku_df)
        
        return top_sku_df
    except Exception as e:
        print(f"Error analyzing billing CSV: {e}")
        return pd.DataFrame()

def fetch_logs_for_service(client, human_service_name, timestamp_filter):
    """Fetches logs for a single service to avoid 500 errors from complex queries."""
    
    api_service = config.SERVICE_MAPPING.get(human_service_name)
    if not api_service:
        print(f"Skipping {human_service_name} (No API mapping found)")
        return []

    print(f"Scanning logs for {human_service_name} ({api_service})...")

    # Filter for this specific service
    filter_str = f"""
        logName="projects/{config.PROJECT_ID}/logs/cloudaudit.googleapis.com%2Factivity"
        AND timestamp >= "{timestamp_filter}"
        AND protoPayload.serviceName="{api_service}"
        AND (
            protoPayload.methodName:"create" OR 
            protoPayload.methodName:"insert" OR 
            protoPayload.methodName:"deploy" OR 
            protoPayload.methodName:"build" OR
            operation.producer:"github.com"
        )
    """

    data = []
    try:
        entries = client.list_entries(filter_=filter_str, page_size=50)
        
        for entry in entries:
            payload = entry.payload
            if not payload: continue
            
            try:
                data.append({
                    'Service': human_service_name,
                    'API Service': api_service,
                    'Resource Name': payload.get('resourceName', 'Unknown'),
                    'Created By': payload.get('authenticationInfo', {}).get('principalEmail', 'Unknown'),
                    'Timestamp': entry.timestamp,
                    'Method': payload.get('methodName', 'Unknown')
                })
            except:
                continue
                
    except Exception as e:
        print(f"  Warning: Failed to query {human_service_name}: {e}")
    
    print(f"  Found {len(data)} events.")
    return data

def main():
    print(f"Target Project: {config.PROJECT_ID}")
    
    billing_csv = find_billing_csv()
    if not billing_csv:
        print("Error: No billing CSV file found.")
        return

    top_skus_df = analyze_billing_data(billing_csv)
    if top_skus_df.empty: return

    # Save Top 10 SKUs to a file for reference
    top_skus_df.to_excel("top_10_cost_skus.xlsx", index=False)
    print("Saved 'top_10_cost_skus.xlsx'")
        
    client = get_logging_client()
    if not client: return

    # Calculate timestamp once
    start_time = datetime.now(timezone.utc) - timedelta(days=config.DAYS_BACK)
    timestamp_filter = start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    
    all_data = []
    
    # Get unique services from the Top SKUs to scan
    # We scan the *Service* because Audit Logs are at the Service level, not SKU level.
    unique_services_to_scan = top_skus_df["Service description"].unique().tolist()
    
    for service_name in unique_services_to_scan:
        service_data = fetch_logs_for_service(client, service_name, timestamp_filter)
        all_data.extend(service_data)
        time.sleep(1) # Be nice to the API
        
    if not all_data:
        print("\nNo creation logs found for any of the top services.")
        # Still output the Top SKUs even if no logs found
        top_skus_df.to_excel("gcp_top_cost_skus_report.xlsx", index=False)
    else:
        creation_df = pd.DataFrame(all_data)
        creation_df['Timestamp'] = creation_df['Timestamp'].astype(str)
        
        # MERGE & AGGREGATE
        # 1. Merge the data first
        merged_df = pd.merge(
            top_skus_df, 
            creation_df, 
            left_on="Service description", 
            right_on="Service", 
            how="left"
        )

        # 2. Aggregate rows so each SKU appears only once
        # We group by the Billing Columns (Service, SKU, Cost)
        final_df = merged_df.groupby(["Service description", "SKU description", "Cost ($)"]).agg({
            "Created By": lambda x: ", ".join([f"{k}({v})" for k, v in x.value_counts().items()]), # Summarize creators: mohit(5), ahmed(2)
            "Resource Name": "count", # Count total resources created
            "Timestamp": ["min", "max"] # Show date range
        }).reset_index()

        # Flattern MultiIndex columns
        final_df.columns = ["Service", "SKU", "Total Cost", "Creators (Count)", "Total Resources Created", "First Created", "Last Created"]
        
        # Sort by Cost desc
        final_df = final_df.sort_values(by="Total Cost", ascending=False)
        
        print("\nAggregated Report Sample:")
        pd.set_option('display.max_colwidth', 50)
        print(final_df[['Service', 'SKU', 'Total Cost', 'Creators (Count)']].head())

        output_file = "gcp_sku_cost_creators_summary.xlsx"
        final_df.to_excel(output_file, index=False)
        final_df.to_csv("gcp_sku_cost_creators_summary.csv", index=False)
        print(f"\nSUCCESS: Generated Aggregated Report '{output_file}'")

if __name__ == "__main__":
    main()
