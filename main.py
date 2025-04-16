import requests
import yaml
import os
import time
import datetime

CONFIG_PATH = './config.yaml'

def get_base_url(region):
    region_urls = {
        "us1": "https://secure.sysdig.com/",
        "us2": "https://us2.app.sysdig.com/",
        "us4": "https://app.us4.sysdig.com/",
        "eu1": "https://eu1.app.sysdig.com/",
        "au1": "https://app.au1.sysdig.com/",
        "me2": "https://app.me2.sysdig.com/",
        "in1": "https://app.in1.sysdig.com/"
    }
    return region_urls.get(region, region_urls["us1"])

def load_config(path=CONFIG_PATH):

    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file '{path}' not found.")

    with open(path, 'r') as f:
        config = yaml.safe_load(f)

    required_keys = ['sysdig_api_token', 'fileName', 'query', 'output_path']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required key in config.yaml: {key}")

    config['region'] = config.get('region', 'us1')
    config['output_path'] = config.get('output_path', '/output')

    return config

def trigger_report(base_url, token, file_name, query):
    report_trigger_url = f"{base_url}api/query-storage/v1/reports"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "fileName": file_name,
        "query": query,
        "queryVersion": "2"
    }

    response = requests.post(report_trigger_url, headers=headers, json=payload)

    if response.status_code == 201:
        report_id = response.json().get("reportId")
        if not report_id:
            raise ValueError("No report ID returned in the response.")
        print(f"Report triggered successfully. Report file ID: {report_id}")
        return report_id
    else:
        raise RuntimeError(f"Failed to trigger report: {response.status_code} - {response.text}")

def download_report_csv(base_url, token, report_file_id, output_file):
    download_url = f"{base_url}api/query-storage/v1/report-files/{report_file_id}"
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'text/csv'
    }

    for attempt in range(5):
        response = requests.get(download_url, headers=headers)
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"CSV report downloaded successfully to '{output_file}'")
            return
        else:
            print(f"Report not ready yet (attempt {attempt + 1}/5). Retrying in 5 seconds...")
            time.sleep(5)

    raise RuntimeError(f"Failed to download CSV report after retries: {response.status_code} - {response.text}")

if __name__ == "__main__":
    config = load_config()
    token = config['sysdig_api_token']
    file_name = config['fileName']
    output_path = config['output_path']
    query = config['query']
    region = config['region']
    base_url = get_base_url(region)

    date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_name_with_date = f"{file_name}_{date_str}" + '.csv'

    try:
        report_file_id = trigger_report(base_url, token, file_name, query)
        download_report_csv(base_url, token, report_file_id, os.path.join(output_path, file_name_with_date))
    except Exception as e:
        print(f"Error: {e}")
