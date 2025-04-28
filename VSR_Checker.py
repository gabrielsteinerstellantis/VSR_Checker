import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
import requests
from io import BytesIO

# === CONFIGURATION ===
MASTER_LIST_PATH = r'z:\dp.staging.ah\tmp\VSR_Checker_Data\Master_SW_List.xlsx'
README_URL = "https://raw.githubusercontent.com/gabrielsteinerstellantis/VSR_Checker/main/readme.txt"

# === FUNCTIONS ===

@st.cache_data
def load_master_list():
    try:
        df = pd.read_excel(MASTER_LIST_PATH, sheet_name="Master SW List", engine="openpyxl")
        return df
    except Exception as e:
        st.error(f"Error loading master SW list: {e}")
        return pd.DataFrame(columns=["ECU", "Part #", "SW Version"])

def save_master_list(df):
    try:
        df.to_excel(MASTER_LIST_PATH, index=False, sheet_name="Master SW List", engine="openpyxl")
        st.success("Master SW List saved successfully!")
    except PermissionError:
        st.warning("Cannot save: Master SW List is open in another program! Download your changes instead below.")
        save_local(df)
    except Exception as e:
        st.error(f"Error saving master SW list: {e}")

def save_local(df):
    towrite = BytesIO()
    df.to_excel(towrite, index=False, sheet_name="Master SW List", engine="openpyxl")
    towrite.seek(0)
    st.download_button(
        label="💾 Download Master List Locally",
        data=towrite,
        file_name="Master_SW_List_backup.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def load_readme():
    try:
        response = requests.get(README_URL)
        if response.status_code == 200:
            return response.text
        else:
            return "Unable to load ReadMe from GitHub."
    except:
        return "Unable to load ReadMe from GitHub."

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

            if len(cells) == 2 and "No positive response" in cells[1].get_text():
                ecu = cells[0].get_text(strip=True)
                ecu_data.append({"ECU": ecu, "Part #": "N/A", "SW Version": "N/A"})
                continue

            if len(cells) >= 8:
                ecu = cells[0].get_text(strip=True)
                part_number = cells[3].get_text(strip=True)
                sw_version = cells[7].get_text(strip=True)

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

            part_status = "✅ Match" if str(reported_part) == str(expected_part) else "⚠️ Mismatch"
            sw_status = "✅ Match" if str(expected_sw) in str(reported_sw) else "⚠️ Mismatch"
        else:
            expected_part = "N/A"
            expected_sw = "N/A"
            part_status = "❌ Not Found"
            sw_status = "❌ Not Found"

        results.append({
            "ECU": ecu,
            "🚗Reported Part #": reported_part,
            "📒Expected Part #": expected_part,
            "Part Status": part_status,
            "🚗Reported SW": reported_sw,
            "📒Expected SW": expected_sw,
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

# === PAGE SETUP ===
st.set_page_config(page_title="Vehicle Scan Report Checker", layout="wide")
st.title("🚗 Vehicle Scan Report Checker")

# === SESSION STATE SETUP ===
if "hidden_ecus" not in st.session_state:
    st.session_state.hidden_ecus = set()

# === UPLOAD VSR FILE ===
uploaded_file = st.file_uploader("Upload VSR HTML file", type="htm")

if uploaded_file:
    with st.spinner("Processing VSR file..."):
        html_content = uploaded_file.read()
        vsr_df = parse_vsr_html(html_content)

    if vsr_df.empty:
        st.error("No ECU data found in the HTML file.")
    else:
        master_df = load_master_list()
        results_df = compare_to_master(vsr_df, master_df)

        # === FILTERING ===
        st.subheader("Filter Results")
        search = st.text_input("🔍 Search ECU Name")
        part_status_filter = st.multiselect(
            "Filter by Part Status:",
            ["✅ Match", "⚠️ Mismatch", "❌ Not Found"],
            default=["✅ Match", "⚠️ Mismatch", "❌ Not Found"]
        )
        sw_status_filter = st.multiselect(
            "Filter by SW Status:",
            ["✅ Match", "⚠️ Mismatch", "❌ Not Found"],
            default=["✅ Match", "⚠️ Mismatch", "❌ Not Found"]
        )

        # === ECU HIDING SYSTEM ===
        with st.sidebar.expander("👁️‍🗨️ Hide / Show ECUs", expanded=False):
            st.markdown("**Toggle ECUs you want to display:**")
            all_ecus = sorted(results_df["ECU"].unique())

            # Master toggle to show all if everything hidden
            if st.button("🔄 Show All ECUs"):
                st.session_state.hidden_ecus.clear()

            for ecu in all_ecus:
                if ecu not in st.session_state.hidden_ecus:
                    checked = True
                else:
                    checked = False

                if st.checkbox(ecu, value=checked, key=f"ecu_checkbox_{ecu}"):
                    st.session_state.hidden_ecus.discard(ecu)
                else:
                    st.session_state.hidden_ecus.add(ecu)

        # === APPLY FILTERS ===
        filtered_df = results_df.copy()

        if part_status_filter:
            filtered_df = filtered_df[filtered_df["Part Status"].isin(part_status_filter)]

        if sw_status_filter:
            filtered_df = filtered_df[filtered_df["SW Status"].isin(sw_status_filter)]

        if search:
            filtered_df = filtered_df[filtered_df["ECU"].str.contains(search, case=False, na=False)]

        if st.session_state.hidden_ecus:
            filtered_df = filtered_df[~filtered_df["ECU"].isin(st.session_state.hidden_ecus)]

        # === DISPLAY RESULTS ===
        st.subheader("📋 Comparison Results")
        styled_df = filtered_df.style.applymap(highlight_status, subset=["Part Status", "SW Status"])
        # Dynamically calculate height based on the number of rows
        max_rows = 50
        row_height = 36  # Approximate height for each row in pixels
        height = min(len(filtered_df) * row_height, max_rows * row_height)

        # Display the table with dynamic height
        st.dataframe(styled_df, use_container_width=True, height=height)

        # === DOWNLOAD CSV ===
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download CSV", data=csv, file_name="vsr_comparison.csv", mime="text/csv")

# === SIDEBAR TOOLS ===
st.sidebar.markdown("---")
st.sidebar.header("🛠️ Tools")

if st.sidebar.button("🔄 Reload Master List"):
    st.cache_data.clear()
    st.sidebar.success("Master List reloaded!")

st.sidebar.subheader("📝 Edit Master SW List")
raw_df = load_master_list()
columns_to_keep = ["ECU", "Part #", "SW Version"]
editable_df = raw_df[columns_to_keep].copy()

edited_df = st.sidebar.data_editor(
    editable_df,
    use_container_width=True,
    num_rows="dynamic",
    key="editor"
)

if st.sidebar.button("💾 Save Master List"):
    try:
        for idx, row in edited_df.iterrows():
            if idx < len(raw_df):
                raw_df.at[idx, "ECU"] = row["ECU"]
                raw_df.at[idx, "Part #"] = row["Part #"]
                raw_df.at[idx, "SW Version"] = row["SW Version"]
            else:
                new_row = pd.Series({**{col: "" for col in raw_df.columns}, **row.to_dict()})
                raw_df = pd.concat([raw_df, pd.DataFrame([new_row])], ignore_index=True)

        save_master_list(raw_df)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error saving edits: {e}")

# === SIDEBAR README ===
st.sidebar.markdown("---")
st.sidebar.subheader("📖 App Info")
if st.sidebar.button("View ReadMe"):
    readme_text = load_readme()
    st.sidebar.text_area("App Information", readme_text, height=300)
