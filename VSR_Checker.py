import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re

# Load master SW list (you can replace this with reading a CSV/Excel file)
def load_master_list():
    url = "https://raw.githubusercontent.com/gabrielsteinerstellantis/VSR_Checker/main/data/Master SW List - VSR Checker App.xlsx"
    return pd.read_excel(url, sheet_name="Master SW List", engine="openpyxl")

# Parse the uploaded VSR HTML file
def parse_vsr_html(html):
    soup = BeautifulSoup(html, "html.parser")

    # Locate the "ECU Information" section and stop before the second section
    ecu_header = soup.find("h2", string=re.compile("ECU Information", re.IGNORECASE))
    if ecu_header:
        ecu_section = []
        for sibling in ecu_header.find_next_siblings():
            if sibling.name == "h2":  # Stop at next major section header
                break
            ecu_section.append(sibling)

        # Extract only the tables within the ECU section
        tables = [s for s in ecu_section if s.name == "table"]
    else:
        tables = []

    ecu_data = []
    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if "ECU" in headers or "Part Number" in headers:
            for row in table.find_all("tr")[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) >= 8:
                    ecu = cells[0]                      # ECU name
                    part_number = cells[3]              # Part Number
                    sw_version = cells[7]               # Application SW VersionHEX

                    # Clean up the SW version (e.g., split at unexpected extra codes)
                    sw_version = re.split(r'(#[0-9]+: [0-9.]+)', sw_version)
                    sw_version = ''.join(sw_version[:2]) if len(sw_version) > 1 else sw_version[0]

                    ecu_data.append({
                        "ECU": ecu,
                        "Part #": part_number,
                        "SW Version": sw_version
                    })
    return pd.DataFrame(ecu_data)

# Compare report vs master list
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

# Apply conditional formatting to status columns
def highlight_status(val):
    if "✅" in val:
        return 'background-color: #d4edda; color: #155724'  # green
    elif "⚠️" in val:
        return 'background-color: #fff3cd; color: #856404'  # yellow
    elif "❌" in val:
        return 'background-color: #f8d7da; color: #721c24'  # red
    return ''

# Streamlit UI
st.title("Vehicle Scan Report Checker")

uploaded_file = st.file_uploader("Upload VSR HTML file", type="htm")

if uploaded_file:
    html_content = uploaded_file.read()
    vsr_df = parse_vsr_html(html_content)
    master_df = load_master_list()
    results_df = compare_to_master(vsr_df, master_df)

    st.subheader("Filter Results")
    part_statuses = ["All"] + sorted(results_df["Part Status"].unique())
    sw_statuses = ["All"] + sorted(results_df["SW Status"].unique())

    selected_part = st.radio("Part Status", part_statuses, horizontal=True)
    selected_sw = st.radio("SW Status", sw_statuses, horizontal=True)

    filtered_df = results_df.copy()
    if selected_part != "All":
        filtered_df = filtered_df[filtered_df["Part Status"] == selected_part]
    if selected_sw != "All":
        filtered_df = filtered_df[filtered_df["SW Status"] == selected_sw]

    st.subheader("Comparison Results")
    styled_df = filtered_df.style.applymap(highlight_status, subset=["Part Status", "SW Status"])
    st.dataframe(styled_df, use_container_width=True)

    # Export to CSV
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Results as CSV",
        data=csv,
        file_name="vsr_comparison_results.csv",
        mime="text/csv"
    )
