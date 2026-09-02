import base64
import io
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Bus Timings Dashboard", layout="wide")
st.title("🚌 Live Bus Timings & Location Management")

# Load credentials from .streamlit/secrets.toml
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]
FILE_PATH = st.secrets["FILE_PATH"]
BRANCH = st.secrets.get("BRANCH", "main")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}
API_URL = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"

# Columns structured as required
COLUMNS = [
    "Bus_Number",
    "Route_Name",
    "Current_Location",
    "Bus_Type",  # KSRTC or BMTC
    "Morning_Timing_1",
    "Morning_Timing_2",
    "Morning_Timing_3",
    "Afternoon_Timing_1",
    "Afternoon_Timing_2",
    "Afternoon_Timing_3",
    "Evening_Timing_1",
    "Evening_Timing_2",
    "Evening_Timing_3",
    "Night_Timing_1",
    "Night_Timing_2",
    "Night_Timing_3",
]


def fetch_data_from_github():
    """Fetch CSV file and SHA hash from GitHub."""
    response = requests.get(API_URL, headers=HEADERS, params={"ref": BRANCH})
    if response.status_code == 200:
        data = response.json()
        sha = data["sha"]
        content = base64.b64decode(data["content"]).decode("utf-8")
        df = pd.read_csv(io.StringIO(content))

        # Guarantee all required schema columns exist
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""

        return df[COLUMNS], sha
    elif response.status_code == 404:
        # Return empty dataframe if file does not exist yet
        empty_df = pd.DataFrame(columns=COLUMNS)
        return empty_df, None
    else:
        st.error(f"Failed to fetch data: {response.json().get('message')}")
        return None, None


def update_github_file(dataframe, sha):
    """Commit updated CSV data back to GitHub repository."""
    csv_data = dataframe.to_csv(index=False)
    encoded_content = base64.b64encode(csv_data.encode("utf-8")).decode("utf-8")

    payload = {
        "message": "Update bus schedule via Streamlit App",
        "content": encoded_content,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    response = requests.put(API_URL, headers=HEADERS, json=payload)
    return response.status_code in [200, 201]


# Fetch data
df, file_sha = fetch_data_from_github()

if df is not None:
    st.info(
        "💡 **Instructions:** Click on any cell to edit. Use the **+** icon at the bottom of a table to add a new bus, or select a row and press **Delete** to remove it. Click **Save All Changes** when done."
    )

    tab_ksrtc, tab_bmtc = st.tabs(["🔴 KSRTC Buses", "🔵 BMTC Buses"])

    # Separate dataframes by Bus_Type
    ksrtc_df = df[df["Bus_Type"] == "KSRTC"].copy()
    bmtc_df = df[df["Bus_Type"] == "BMTC"].copy()

    with tab_ksrtc:
        st.subheader("KSRTC Bus Schedule")
        edited_ksrtc = st.data_editor(
            ksrtc_df,
            num_rows="dynamic",
            use_container_width=True,
            key="ksrtc_editor",
        )

    with tab_bmtc:
        st.subheader("BMTC Bus Schedule")
        edited_bmtc = st.data_editor(
            bmtc_df,
            num_rows="dynamic",
            use_container_width=True,
            key="bmtc_editor",
        )

    # Force the Bus_Type flag on newly added rows inside each tab
    edited_ksrtc["Bus_Type"] = "KSRTC"
    edited_bmtc["Bus_Type"] = "BMTC"

    st.markdown("---")
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("💾 Save All Changes", type="primary"):
            # Combine modified tables into a single DataFrame
            combined_df = pd.concat(
                [edited_ksrtc, edited_bmtc], ignore_index=True
            )
            if update_github_file(combined_df, file_sha):
                st.success("Successfully updated repository!")
                st.rerun()
            else:
                st.error("Failed to commit changes to GitHub.")
    with col2:
        if st.button("🔄 Refresh Data"):
            st.rerun()