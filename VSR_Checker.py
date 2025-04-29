import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import re
import requests
from io import BytesIO
from packaging import version

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
        return pd.DataFrame(columns=["ECU", "Part #", "SW Version", "Priority", "FI Owner", "Subsystem Owner"])


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


def compare_sw_versions_advanced(reported_sw, expected_sw):
    if pd.isna(expected_sw) or pd.isna(reported_sw) or expected_sw == "N/A" or reported_sw == "N/A":
        return "❌ Not Found"
    try:
        reported_sw = str(reported_sw)
        expected_sw = str(expected_sw)
        reported_match = re.search(r'\d+\.\d+\.\d+', reported_sw)
        expected_match = re.search(r'\d+\.\d+\.\d+', expected_sw)
        reported_sw_clean = reported_match.group(0) if reported_match else reported_sw
        expected_sw_clean = expected_match.group(0) if expected_match else expected_sw
        if version.parse(reported_sw_clean) == version.parse(expected_sw_clean):
            return "✅ Match"
        elif version.parse(reported_sw_clean) > version.parse(expected_sw_clean):
            return "💜 Newer"
        else:
            return "⚠️ Older"
    except version.InvalidVersion:
        # Assuming invalid version format might imply older or non-standard
        return "⚠️ Older"


def get_part_suffix(pn):
    return pn.strip()[-2:].upper() if isinstance(pn, str) and len(pn.strip()) >= 2 else ""


def compare_part_numbers(reported, expected):
    if expected == "N/A" or reported == "N/A":
        return "❌ Not Found"
    suffix_r = get_part_suffix(reported)
    suffix_e = get_part_suffix(expected)
    if suffix_r == suffix_e:
        return "✅ Match"
    elif suffix_r > suffix_e:
        return "💜 Newer"
    else:
        return "⚠️ Older"


def compare_to_master(vsr_df, master_df):
    results = []
    for _, row in vsr_df.iterrows():
        ecu = row["ECU"]
        reported_part = row.get("Part #")  # Use .get() to handle potential missing keys
        reported_sw = row.get("SW Version") # Use .get()
        match = master_df[master_df["ECU"] == ecu]
        if not match.empty:
            expected_part = match.iloc[0].get("Part #", "N/A")
            expected_sw = match.iloc[0].get("SW Version", "N/A")
            priority = match.iloc[0].get("Priority", "N/A")
            fi_owner = match.iloc[0].get("FI Owner", "N/A")
            subsystem_owner = match.iloc[0].get("Subsystem Owner", "N/A")

            if reported_part is None or pd.isna(reported_part) or str(reported_part).strip() == "":
                part_status = "❌ Not Found"
            else:
                part_status = compare_part_numbers(reported_part, expected_part)

            if reported_sw is None or pd.isna(reported_sw) or str(reported_sw).strip() == "":
                sw_status = "❌ Not Found"
            else:
                sw_status = compare_sw_versions_advanced(reported_sw, expected_sw)

        else:
            expected_part = "N/A"
            expected_sw = "N/A"
            priority = "N/A"
            fi_owner = "N/A"
            subsystem_owner = "N/A"
            part_status = "❌ Not Found"
            sw_status = "❌ Not Found"

        results.append({
            "ECU": ecu,
            "🚗Reported Part #": reported_part,
            "📒Expected Part #": expected_part,
            "Part Status": part_status,
            "🚗Reported SW": reported_sw,
            "📒Expected SW": expected_sw,
            "SW Status": sw_status,
            "Priority": priority,
            "FI Owner": fi_owner,
            "Subsystem Owner": subsystem_owner
        })
    return pd.DataFrame(results)


def highlight_status(val):
    if "✅" in val:
        return 'background-color: #d4edda; color: #155724'  # Light green, dark green
    elif "⚠️" in val:
        return 'background-color: #fff3cd; color: #856404'  # Light yellow, dark yellow
    elif "❌" in val:
        return 'background-color: #f8d7da; color: #721c24'  # Light red, dark red
    elif "💜" in val:  # Add this condition for "Newer"
        return 'background-color: #e0b0ff; color: #4b0082'  # Light purple, dark purple
    return ''


def generate_action_plan(results_df):
    priority_1_ecus = []
    priority_2_ecus = []
    priority_3_ecus = []
    other_ecus_no_update = []
    missing_ecus = []

    for _, row in results_df.iterrows():
        needs_update = "⚠️ Older" in [row["Part Status"], row["SW Status"]] or "❌ Not Found" in [row["Part Status"], row["SW Status"]]

        if needs_update:
            ecu_info = {
                "ECU": row["ECU"],
                "Reported Part #": row["🚗Reported Part #"],
                "Expected Part #": row["📒Expected Part #"],
                "Reported SW": row["🚗Reported SW"],
                "Expected SW": row["📒Expected SW"],
                "FI Owner": row["FI Owner"],
                "Subsystem Owner": row["Subsystem Owner"]
            }
            if row["Priority"] == 1:
                priority_1_ecus.append(ecu_info)
            elif row["Priority"] == 2:
                priority_2_ecus.append(ecu_info)
            elif row["Priority"] == 3:
                priority_3_ecus.append(ecu_info)
            elif pd.isna(row["Priority"]):
                priority_1_ecus.append(ecu_info) # Treat missing priority as critical for now - adjust as needed
            else:
                # Consider ECUs needing update with other priorities
                pass # Decide how to handle or categorize these
        elif "❌ Not Found" in [row["Part Status"], row["SW Status"]]:
            missing_ecus.append(row["ECU"])
        elif row["Priority"] == 0:
            other_ecus_no_update.append(row["ECU"])

    action_plan = {}
    action_plan["priority_1"] = pd.DataFrame(priority_1_ecus)
    action_plan["priority_2"] = pd.DataFrame(priority_2_ecus)
    action_plan["priority_3"] = pd.DataFrame(priority_3_ecus)
    action_plan["other_no_update"] = other_ecus_no_update
    action_plan["missing"] = missing_ecus

    return action_plan


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

        # Count Part Statuses
        part_counts = results_df["Part Status"].value_counts()
        sw_counts = results_df["SW Status"].value_counts()

        def count(label, counts):
            return counts.get(label, 0)

        # === FILTERING ===
        with st.expander("🧮 Filter Results", expanded=False):
            search = st.text_input("🔍 Search ECU Name")

            # --- Part Status Filters ---
            st.markdown("**Part Status:**")
            select_all_part = st.checkbox("Select All (Part)", value=True, key="select_all_part")

            cols_part = st.columns(4)
            with cols_part[0]: part_match = st.checkbox(f"✅ Match ({count('✅ Match', part_counts)})", select_all_part, key="part_match")
            with cols_part[1]: part_older = st.checkbox(f"⚠️ Older ({count('⚠️ Older', part_counts)})", select_all_part, key="part_old")
            with cols_part[2]: part_newer = st.checkbox(f"💜 Newer ({count('💜 Newer', part_counts)})", select_all_part, key="part_newer")
            with cols_part[3]: part_notfound = st.checkbox(f"❌ Not Found ({count('❌ Not Found', part_counts)})", select_all_part, key="part_notfound")

            # --- SW Status Filters ---
            st.markdown("**SW Status:**")
            select_all_sw = st.checkbox("Select All (SW)", value=True, key="select_all_sw")

            cols_sw = st.columns(4)
            with cols_sw[0]: sw_match = st.checkbox(f"✅ Match ({count('✅ Match', sw_counts)})", select_all_sw, key="sw_match")
            with cols_sw[1]: sw_older = st.checkbox(f"⚠️ Older ({count('⚠️ Older', sw_counts)})", select_all_sw, key="sw_old")
            with cols_sw[2]: sw_newer = st.checkbox(f"💜 Newer ({count('💜 Newer', sw_counts)})", select_all_sw, key="sw_newer")
            with cols_sw[3]: sw_notfound = st.checkbox(f"❌ Not Found ({count('❌ Not Found', sw_counts)})", select_all_sw, key="sw_notfound")

            # --- Priority Filter ---
            st.markdown("**ECU Filtering – by Priority:**")
            priority_values = results_df["Priority"].dropna().unique()
            priority_values = [int(p) for p in priority_values if str(p).isdigit()]
            # Define possible priorities explicitly for consistent ordering/display
            possible_priorities = {0, 1, 2, 3}
            priority_values_to_show = sorted(set(priority_values) & possible_priorities)

            if priority_values_to_show:
                cols_priority = st.columns(len(priority_values_to_show))
                priority_selected = []
                for i, p in enumerate(priority_values_to_show):
                    with cols_priority[i]:
                        if st.checkbox(f"Priority {p}", value=True, key=f"priority_{p}"):
                            priority_selected.append(p)
            else:
                st.caption("No priorities (0-3) found in results for filtering.")
                priority_selected = [] # Ensure it's defined even if no checkboxes shown


        # === ECU HIDING SYSTEM ===
        with st.sidebar.expander("👁️‍🗨️ Hide / Show ECUs", expanded=False):
            st.markdown("**Toggle ECUs you want to display:**")
            all_ecus = sorted(results_df["ECU"].unique())

            # Master toggle to show all if everything hidden
            if st.button("🔄 Show All ECUs"):
                st.session_state.hidden_ecus.clear()
                st.rerun() # Added rerun for immediate effect

            for ecu in all_ecus:
                # Determine current state based on session state
                is_visible = ecu not in st.session_state.hidden_ecus

                # Create checkbox, default value reflects current visibility
                if st.checkbox(ecu, value=is_visible, key=f"ecu_checkbox_{ecu}"):
                    # If checkbox is checked, ensure ECU is NOT in the hidden set
                    st.session_state.hidden_ecus.discard(ecu)
                else:
                    # If checkbox is unchecked, ensure ECU IS in the hidden set
                    st.session_state.hidden_ecus.add(ecu)


        # === APPLY FILTERS ===
        filtered_df = results_df.copy()

        part_status_filters = []
        if part_match: part_status_filters.append("✅ Match")
        if part_older: part_status_filters.append("⚠️ Older")
        if part_newer: part_status_filters.append("💜 Newer")
        if part_notfound: part_status_filters.append("❌ Not Found")

        sw_status_filters = []
        if sw_match: sw_status_filters.append("✅ Match")
        if sw_older: sw_status_filters.append("⚠️ Older")
        if sw_newer: sw_status_filters.append("💜 Newer")
        if sw_notfound: sw_status_filters.append("❌ Not Found")

        filtered_df = filtered_df[filtered_df["Part Status"].isin(part_status_filters)]
        filtered_df = filtered_df[filtered_df["SW Status"].isin(sw_status_filters)]

        if search:
            filtered_df = filtered_df[filtered_df["ECU"].str.contains(search, case=False, na=False)]

        # Check if priority_selected exists and is not empty before filtering
        if 'priority_selected' in locals() and priority_selected:
            filtered_df = filtered_df[filtered_df["Priority"].isin(priority_selected)]

        # Apply ECU hiding filter
        if st.session_state.hidden_ecus:
            filtered_df = filtered_df[~filtered_df["ECU"].isin(st.session_state.hidden_ecus)]

        # === DISPLAY RESULTS ===
        st.subheader("📋 Comparison Results")
        styled_df = filtered_df.style.applymap(highlight_status, subset=["Part Status", "SW Status"])

        # Dynamically calculate height based on the number of rows
        max_rows = 50
        row_height = 36  # Approximate height for each row in pixels + header
        num_rows_to_display = len(filtered_df)
        # Calculate height: base height for header + height per row, capped by max_rows
        container_height = min( (num_rows_to_display + 1) * row_height , max_rows * row_height + row_height)


        # Display the table with dynamic height
        st.dataframe(styled_df, use_container_width=True, height=container_height)

        # === DOWNLOAD CSV ===
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇️ Download CSV",
            data=csv,
            file_name="vsr_comparison.csv",
            mime="text/csv"
        )

# === GENERATE AND DISPLAY ACTION PLAN ===
        action_plan = generate_action_plan(filtered_df)
        st.subheader("💡 Action Plan")

        if not action_plan["priority_1"].empty:
            st.subheader("Priority 1: Critical Base Vehicle ECUs")
            st.dataframe(action_plan["priority_1"], use_container_width=True)

        if not action_plan["priority_2"].empty:
            st.subheader("Priority 2: ADAS ECUs")
            st.dataframe(action_plan["priority_2"], use_container_width=True)

        if not action_plan["priority_3"].empty:
            st.subheader("Priority 3: Low Priority Base Vehicle ECUs")
            st.dataframe(action_plan["priority_3"], use_container_width=True)

        if action_plan["missing"]:
            st.subheader("Missing ECUs")
            st.markdown(f"The following ECUs were not found in the Master SW List: {', '.join(action_plan['missing'])}.")

        if action_plan["other_no_update"]:
            st.subheader("Other ECUs")
            st.markdown(f"The following ECUs do not require updates: {', '.join(action_plan['other_no_update'])}.")

# === SIDEBAR TOOLS ===
st.sidebar.markdown("---")
st.sidebar.header("🛠️ Tools")

if st.sidebar.button("🔄 Reload Master List"):
    st.cache_data.clear()
    st.sidebar.success("Master List reloaded!")
    # Consider adding st.rerun() here if you want the main page to update immediately

st.sidebar.subheader("📝 Edit Master SW List")
raw_df = load_master_list()
columns_to_keep = ["ECU", "Part #", "SW Version", "Priority", "FI Owner", "Subsystem Owner"]
# Ensure all columns exist, even if empty, before selecting
for col in columns_to_keep:
    if col not in raw_df.columns:
        raw_df[col] = None # Or appropriate default
editable_df = raw_df[columns_to_keep].copy()

edited_df = st.sidebar.data_editor(
    editable_df,
    use_container_width=True,
    num_rows="dynamic",
    key="editor"
)

if st.sidebar.button("💾 Save Master List"):
    try:
        # Create a DataFrame reflecting the edits, including additions/deletions
        # The data editor passes the *current state* of the table.
        # We need to merge this back carefully if other columns existed in raw_df.
        # Assuming columns_to_keep are the *only* ones we care about saving.
        save_master_list(edited_df) # Save the edited state directly
        st.cache_data.clear() # Clear cache after saving
        st.rerun() # Rerun script to reflect saved changes
    except Exception as e:
        st.error(f"Error saving edits: {e}")


# === SIDEBAR README ===
st.sidebar.markdown("---")
st.sidebar.subheader("📖 App Info")
if st.sidebar.button("View ReadMe"):
    readme_text = load_readme()
    st.sidebar.text_area("App Information", readme_text, height=300)