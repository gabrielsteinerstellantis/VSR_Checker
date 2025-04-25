import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
import requests
from io import BytesIO
from datetime import datetime
import json
import base64

# GitHub config
GITHUB_REPO = "gabrielsteinerstellantis/VSR_Checker"
MASTER_LIST_PATH = "data/Master_SW_List.xlsx"

# Load the master list from GitHub
@st.cache_data
def load_master_list():
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{MASTER_LIST_PATH}"
    try:
        df = pd.read_excel(url, sheet_name="Master SW List", engine="openpyxl")
        return df
    except Exception as e:
        st.error(f"Error loading master SW list: {e}")
        return pd.DataFrame(columns=["ECU", "Part #", "SW Version"])

# Push updated master list to GitHub
def push_to_github(df, token):
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{MASTER_LIST_PATH}"
    headers = {"Authorization": f"token {token}"}
    
    # Get SHA of existing file
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        st.error("Failed to retrieve file metadata from GitHub.")
        return

    sha = response.json()["sha"]

    # Convert Excel to bytes
    excel_bytes = BytesIO()
    df.to_excel(excel_bytes, index=False, sheet_name="Master SW List", engine="openpyxl")
    encoded = base64.b64encode(excel_bytes.getvalue()).decode()

    commit_msg = f"Update Master SW List via Streamlit on {datetime.now().isoformat()}"
    payload = {
        "message": commit_msg,
        "content": encoded,
        "sha": sha
    }

    put = requests.put(api_url, headers=headers, data=json.dumps(payload))
    if put.status_code == 200 or put.status_code == 201:
        st.success("Master list updated on GitHub!")
    else:
        st.error(f"GitHub update failed: {put.text}")

# Dark mode toggle
st.sidebar.title("Settings")
dark_mode = st.sidebar.toggle("Dark Mode")

# Apply light/dark theme override
if dark_mode:
    st.markdown("""<style>
    body { background-color: #0e1117; color: white; }
    .stDataFrame { background-color: #1c1f26 !important; }
    </style>""", unsafe_allow_html=True)

# Main UI
st.title("Vehicle Scan Report Checker")
uploaded_file = st.file_uploader("Upload VSR HTML file", type="htm")

def parse_vsr_html(html):
    soup = BeautifulSoup(html, "html.parser")
    ecu_data = []

    ecu_table = soup.find("table", {"id": "ecuInformationTable"})
    if ecu_table:
        rows = ecu_table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue

            # No positive response
            if len(cells) == 2 and "No positive response" in cells[1].get_text():
                ecu = cells[0].get_text(strip=True)
                ecu_data.append({"ECU": ecu, "Part #": "N/A", "SW Version": "N/A"})
                continue

            if len(cells) >= 8:
                ecu = cells[0].get_text(strip=True)
                part_number = cells[3].get_text(strip=True)
                sw_version = cells[7].get_text(strip=True)
                sw_version = re.split(r'(#[0-9]+: [0-9.]+)', sw_version)
                sw_version = ''.join(sw_version[:2]) if len(sw_version) > 1 else sw_version[0]

                ecu_data.append({
                    "ECU": ecu,
                    "Part #": part_number,
                    "SW Version": sw_version
                })

    return pd.DataFrame(ecu_data)

def compare_to_master(vsr_df, master_df):
    results = []
    for _, row in vsr_df.iterrows():
        ecu = row["ECU"]
        reported_part = row["Part #"]
        reported_sw = row["SW Version"]

        match = master_df[master_df["ECU"] == ecu]
        if not match.empty:
            expected_part = match.iloc[0]["Part #"]
            expected_sw = match.iloc[0]["SW Version"]

            part_status = "✅ Match" if reported_part == expected_part else "⚠️ Mismatch"
            sw_status = "✅ Match" if expected_sw in reported_sw else "⚠️ Mismatch"
        else:
            expected_part = "N/A"
            expected_sw = "N/A"
            part_status = "❌ Not Found"
            sw_status = "❌ Not Found"

        results.append({
            "ECU": ecu,
            "Reported Part #": reported_part,
            "Expected Part #": expected_part,
            "Part Status": part_status,
            "Reported SW": reported_sw,
            "Expected SW": expected_sw,
            "SW Status": sw_status
        })
    return pd.DataFrame(results)

def highlight_status(val):
    if "✅" in val:
        return 'background-color: #d4edda; color: #155724'
    elif "⚠️" in val:
        return 'background-color: #fff3cd; color: #856404'
    elif "❌" in val:
        return 'background-color: #f8d7da; color: #721c24'
    return ''

# File processing
if uploaded_file:
    try:
        with st.spinner("Processing VSR file..."):
            html_content = uploaded_file.read()
            vsr_df = parse_vsr_html(html_content)
            if vsr_df.empty:
                st.error("No ECU data found in the HTML file.")
            else:
                master_df = load_master_list()
                results_df = compare_to_master(vsr_df, master_df)

                st.subheader("Comparison Results")
                search = st.text_input("Search ECU")
                if search:
                    results_df = results_df[results_df["ECU"].str.contains(search, case=False)]

                styled_df = results_df.style.applymap(highlight_status, subset=["Part Status", "SW Status"])
                st.dataframe(styled_df, use_container_width=True)

                csv = results_df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", data=csv, file_name="vsr_comparison.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Failed to process HTML file: {e}")

# Config: Master List Editor
st.sidebar.markdown("---")
st.sidebar.subheader("Master SW List Editor")

if "edit_df" not in st.session_state:
    st.session_state.edit_df = load_master_list()

editable_df = st.sidebar.data_editor(
    st.session_state.edit_df,
    use_container_width=True,
    num_rows="dynamic",
    key="editor"
)

github_token = st.sidebar.text_input("GitHub Token", type="password")
if st.sidebar.button("💾 Save to GitHub"):
    if github_token:
        push_to_github(editable_df, github_token)
    else:
        st.sidebar.error("Please enter your GitHub token to save changes.")
