import pandas as pd
import streamlit as st
import plotly.express as px
import base64
import os
import hashlib
import requests
from dotenv import load_dotenv
from io import BytesIO

load_dotenv()
# Authentication configuration
VALID_USERNAME = os.getenv("USERNAMES", "thbteam")
VALID_HASHED_PASSWORD = os.getenv(
    "HASHED_PASSWORDS", "52da6833b233e0b2cc6d101c4204ff3f44f2abed3707c0fdff06abc2ef59ae6b"
)
ONEDRIVE_EXCEL_LINK = os.getenv("ONEDRIVE_EXCEL_LINK")
ONEDRIVE_LOGO_LINK = os.getenv("ONEDRIVE_LOGO_LINK")

# Authentication function
def check_password():
    """Returns True if the user has entered the correct credentials."""
    def password_entered():
        user_input = st.session_state["username"]
        pass_input = st.session_state["password"]
        hashed_input = hashlib.sha256(pass_input.encode()).hexdigest()
        if user_input == VALID_USERNAME and hashed_input == VALID_HASHED_PASSWORD:
            st.session_state["authenticated"] = True
            del st.session_state["password"]
        else:
            st.session_state["authenticated"] = False
            st.error("Incorrect username or password")

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown("<h1 style='text-align: center; color: #0c1f29;'>Login</h1>", unsafe_allow_html=True)
        with st.form(key="login_form"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button(label="Login", on_click=password_entered)
        return False
    return True

# Function to download file from OneDrive
def download_file(url, output_path=None):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        if output_path:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return output_path
        else:
            return BytesIO(response.content)
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to download file from {url}: {e}")
        return None

# Main application starts here
if check_password():
    # Set page configuration
    st.set_page_config(
        page_title="Patient Data Dashboard",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for styling with improved text visibility
    st.markdown(
        """
        <style>
        .stApp, .main {
            background-color: #0c1f29;
            color: #ffffff;
            padding: 1rem;
        }
        h1 {
            background-color: #e1faf7;
            color: #ffffff;
            text-align: center;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 2rem;
        }
        h2, h3 {
            color: #ffffff;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
        h2 {
            border-left: 5px solid #37c2d8;
            padding-left: 0.5rem;
        }
        .stButton>button {
            background-color: #37c2d8;
            color: #ffffff;
            border-radius: 5px;
            font-weight: bold;
            padding: 0.5rem 1rem;
            margin-bottom: 1rem;
        }
        .stButton>button:hover {
            background-color: #ffffff;
            color: #0c1f29;
        }
        [data-testid="stSidebar"] {
            background-color: #0c1f29;
        }
        [data-testid="stSidebar"] * {
            color: #ffffff !important;
        }
        .metric-card, .highlight {
            background-color: #0c1f29;
            border: 1px solid #37c2d8;
            border-radius: 5px;
            color: #ffffff;
            padding: 1rem;
            margin: 1rem 0;
        }
        .dataframe {
            background-color: #0c1f29;
            color: #ffffff;
            width: 100%;
            border-collapse: collapse;
        }
        .dataframe th {
            background-color: #37c2d8;
            color: #ffffff;
            padding: 0.5rem;
        }
        .dataframe td {
            border: 1px solid #37c2d8;
            padding: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Download Excel file from OneDrive
    excel_file = download_file(ONEDRIVE_EXCEL_LINK)
    if excel_file is None:
        st.stop()

    @st.cache_data
    def load_data():
        # Read Excel file from BytesIO object and fill NA values with empty strings
        return pd.read_excel(excel_file, engine="openpyxl").fillna("")

    # Download and encode logo from OneDrive
    logo_file = download_file(ONEDRIVE_LOGO_LINK)
    if logo_file is None:
        st.stop()
    encoded_svg = base64.b64encode(logo_file.read()).decode()

    st.markdown(
        f"""
        <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 1rem; background-color: #e1faf7; border: 2px solid #37c2d8; border-radius: 5px; padding: 1rem;">
            <img src="data:image/svg+xml;base64,{encoded_svg}" alt="Logo" style="width: 400px; height: 400px; margin-right: 0.5rem;" />
            <h1 style="margin: 0; color: #0c1f29;">Patient Data Dashboard</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Introduction
    with st.container():
        st.markdown(
            """
            <div class="highlight">
                <p style="text-align: center; font-size: 1.1rem;">
                    Welcome to the Patient Data Dashboard. Use the sidebar filters to analyze patient data, 
                    then click "Show Data" to view results.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Load data and display raw unique patient count
    with st.spinner("Loading data..."):
        raw_df = load_data()
    raw_unique = raw_df["Patient ID"].nunique()

    # Copy to reduce fragmentation and start cleaning
    df = raw_df.copy()

    # Parse entrydate with DD/MM/YYYY format (since Excel now uses /)
    df["entrydate"] = pd.to_datetime(df["entrydate"], format="%d/%m/%Y", errors="coerce")
    df["entry_year"] = df["entrydate"].dt.year

    # Convert Year of Birth to numeric and limit its range
    df["Year of Birth"] = pd.to_numeric(df["Year of Birth"], errors="coerce")
    df["Year of Birth"] = df["Year of Birth"].where(df["Year of Birth"].between(1886, 2100))

    # If Height_cm exists, ensure it is numeric
    if "Height_cm" in df.columns:
        df["Height_cm"] = pd.to_numeric(df["Height_cm"], errors="coerce")

    cleaned_unique = df["Patient ID"].nunique()

    # Define columns
    patient_info_cols = ["entrydate", "Patient ID", "Gender", "Year of Birth"]
    test_result_cols = df.columns[65:213].tolist()
    diagnosis_cols = [f"Diagnosis{i}" for i in range(1, 10) if f"Diagnosis{i}" in df.columns]
    medication_cols = [f"Medication{i}_Name" for i in range(1, 16) if f"Medication{i}_Name" in df.columns]
    medication_freq_cols = [f"Medication{i}_Frequency" for i in range(1, 16) if f"Medication{i}_Frequency" in df.columns]
    medication_comment_cols = [f"Medication{i}_Comment" for i in range(1, 16) if f"Medication{i}_Comment" in df.columns]
    medication_duration_cols = [f"Medication{i}_Duration" for i in range(1, 16) if f"Medication{i}_Duration" in df.columns]

    # Sidebar Filters
    with st.sidebar:
        st.markdown("<h2>Filters</h2>", unsafe_allow_html=True)

        st.markdown("### 🚻 Gender")
        if "selected_gender" not in st.session_state:
            st.session_state.selected_gender = "All"

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("All", key="all_gender", help="Show all genders", use_container_width=True):
                st.session_state.selected_gender = "All"
        with col2:
            if st.button("Male", key="male", help="Filter for male patients", use_container_width=True):
                st.session_state.selected_gender = "Male"
        with col3:
            if st.button("Female", key="female", help="Filter for female patients", use_container_width=True):
                st.session_state.selected_gender = "Female"

        st.markdown(
            f"""
            <style>
            div[data-testid="stButton"] button[title="{st.session_state.selected_gender}"] {{
                background-color: #2980b9;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
        selected_gender = st.session_state.selected_gender

        st.markdown("### 🏥 Birth Year")
        yob_min = int(df["Year of Birth"].min(skipna=True))
        yob_max = int(df["Year of Birth"].max(skipna=True))
        yob_range = st.slider(
            "Birth Year Range", yob_min, yob_max, (yob_min, yob_max), label_visibility="hidden"
        )

        st.markdown("### 🏥 Diagnosis")
        diagnosis_values = sorted(
            set(
                df[diagnosis_cols]
                .astype(str)
                .replace("", pd.NA)
                .fillna("Unknown")
                .values.ravel()
            )
        )
        diagnosis_values = [val for val in diagnosis_values if val.lower() != "nan"]
        selected_diagnosis = st.selectbox(
            "Diagnosis", ["All"] + diagnosis_values, label_visibility="hidden"
        )

        st.markdown("### 💊 Medication")
        medication_values = sorted(
            set(df[medication_cols].astype(str).replace("", pd.NA).dropna().values.ravel())
        )
        medication_values = [val for val in medication_values if val.lower() != "nan"]
        selected_medication = st.selectbox(
            "Medication", ["All"] + medication_values, label_visibility="hidden"
        )

        st.markdown("### 📅 Visit Year")
        yov_min = int(df["entry_year"].min(skipna=True) or 2000)
        yov_max = int(df["entry_year"].max(skipna=True) or 2025)
        yov_range = st.slider(
            "Visit Year Range", yov_min, yov_max, (yov_min, yov_max), label_visibility="hidden"
        )

    # Show Data Button
    if st.button("📊 Show Data Analysis"):
        # Apply Filters
        filtered_df = df.copy()
        if selected_gender != "All":
            filtered_df = filtered_df[filtered_df["Gender"] == selected_gender]
        if selected_diagnosis != "All":
            filtered_df = filtered_df[filtered_df[diagnosis_cols].apply(
                lambda row: selected_diagnosis in row.values, axis=1)]
        if selected_medication != "All":
            filtered_df = filtered_df[filtered_df[medication_cols].apply(
                lambda row: selected_medication in row.values, axis=1)]
        
        # Update filter conditions to include rows with NaN values
        filtered_df = filtered_df[
            (filtered_df["Year of Birth"].isna()) |
            ((filtered_df["Year of Birth"] >= yob_range[0]) & (filtered_df["Year of Birth"] <= yob_range[1]))
        ]
        
        filtered_df = filtered_df[
            (filtered_df["entry_year"].isna()) |
            ((filtered_df["entry_year"] >= yov_range[0]) & (filtered_df["entry_year"] <= yov_range[1]))
        ]
        
        filtered_unique = filtered_df["Patient ID"].nunique()

        # Summary Statistics
        total_patients = filtered_unique
        avg_age = int(2025 - filtered_df["Year of Birth"].mean()) if not pd.isna(filtered_df["Year of Birth"].mean()) else "N/A"
        males = filtered_df[filtered_df["Gender"] == "Male"]["Patient ID"].nunique()
        females = filtered_df[filtered_df["Gender"] == "Female"]["Patient ID"].nunique()

        st.markdown("<h2>Patient Population Overview</h2>", unsafe_allow_html=True)
        cols = st.columns(4)
        for col, (label, value) in zip(
            cols, [("Total", total_patients), ("Average Age", avg_age), ("Males", males), ("Females", females)]
        ):
            col.markdown(
                f'<div class="metric-card"><h4 style="color: #3498db;">{label}</h4><p style="font-size: 2rem; font-weight: bold; margin: 0;">{value}</p></div>',
                unsafe_allow_html=True,
            )

        # Tabs for Analysis
        tabs = st.tabs(["🧪 Test Results", "💊 Medications", "🏥 Diagnoses"])

        with tabs[0]:
            st.markdown("<h3>Test Results</h3>", unsafe_allow_html=True)
            non_empty_tests = (
                filtered_df[test_result_cols]
                .replace("", float("nan")).infer_objects(copy=False)
                .dropna(axis=1, how="all")
            )
            result_table = filtered_df[patient_info_cols + list(non_empty_tests.columns)]
            # Use column_config to display entrydate as DD/MM/YYYY
            st.dataframe(
                result_table,
                column_config={
                    "entrydate": st.column_config.DateColumn(
                        "Entry Date",
                        format="DD/MM/YYYY"  # Display as 21/12/2020
                    )
                },
                use_container_width=True,
                height=400,
                hide_index=True
            )

            st.markdown("<h3>Average Test Results</h3>", unsafe_allow_html=True)
            non_empty_tests = (
                filtered_df[test_result_cols]
                .apply(pd.to_numeric, errors="coerce")
                .dropna(axis=1, how="all")
            )
            patient_tests = filtered_df[["Patient ID"] + list(non_empty_tests.columns)].copy()
            for col in patient_tests.columns:
                if col != "Patient ID":
                    patient_tests[col] = pd.to_numeric(patient_tests[col], errors="coerce")
            patient_group_means = patient_tests.groupby("Patient ID").mean(numeric_only=True)
            avg_tests = patient_group_means.mean().reset_index()
            avg_tests.columns = ["Test Name", "Average Value"]
            # Keep table interactive
            avg_tests["Average Value"] = avg_tests["Average Value"].round(2)
            st.dataframe(
                avg_tests,
                use_container_width=True,
                height=400,
                hide_index=True
            )

        with tabs[1]:
            st.markdown("<h3>Medications Analysis</h3>", unsafe_allow_html=True)
            med_long = (
                filtered_df.melt(
                    id_vars=["Patient ID"],
                    value_vars=medication_cols,
                    var_name="Medication_Column",
                    value_name="Medication",
                ).replace("", float("nan")).infer_objects(copy=False)
                .dropna(subset=["Medication"])
            )
            freq_long = filtered_df.melt(
                id_vars=["Patient ID"],
                value_vars=medication_freq_cols,
                var_name="Frequency_Column",
                value_name="Frequency",
            ).replace("", float("nan")).infer_objects(copy=False)
            duration_long = filtered_df.melt(
                id_vars=["Patient ID"],
                value_vars=medication_duration_cols,
                var_name="Duration_Column",
                value_name="Duration",
            ).replace("", float("nan")).infer_objects(copy=False)

            med_long["Frequency"] = freq_long["Frequency"]
            med_long["Duration"] = duration_long["Duration"]

            unique_meds = med_long.groupby("Medication").agg(
                Patients_Count=("Patient ID", "nunique"),
                Most_Common_Frequency=("Frequency", lambda x: (x.dropna().mode()[0] if not x.dropna().mode().empty else None)),
                Average_Duration=("Duration", lambda x: x.dropna().mean() if not x.dropna().empty else None),
            ).reset_index()

            st.dataframe(unique_meds, use_container_width=True, height=400, hide_index=True)

            st.markdown("<h3>Top Medications by Patient Count</h3>", unsafe_allow_html=True)
            if not unique_meds.empty:
                top10_meds = unique_meds.sort_values(by="Patients_Count", ascending=False).head(10)
                fig = px.bar(
                    top10_meds,
                    x="Patients_Count",
                    y="Medication",
                    orientation="h",
                    title="Top Medications by Patient Count",
                    labels={"Patients_Count": "Number of Patients", "Medication": "Medication"},
                    color="Patients_Count",
                    color_continuous_scale="Blues",
                )
                fig.update_layout(
                    title_font_size=16,
                    xaxis_title_font_size=12,
                    yaxis_title_font_size=12,
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No medication data available.")

        with tabs[2]:
            st.markdown("<h3>Diagnoses Analysis</h3>", unsafe_allow_html=True)
            diag_long = (
                filtered_df.melt(
                    id_vars=["Patient ID"],
                    value_vars=diagnosis_cols,
                    var_name="Diagnosis Number",
                    value_name="Diagnosis",
                ).replace("", float("nan")).infer_objects(copy=False)
                .dropna(subset=["Diagnosis"])
            )
            unique_diags = diag_long.groupby("Diagnosis")["Patient ID"].nunique().reset_index(name="Patients_Count")
            st.dataframe(unique_diags.sort_values(by="Patients_Count", ascending=False),
                        use_container_width=True, height=400, hide_index=True)

            st.markdown("<h3>Top Diagnoses by Patient Count</h3>", unsafe_allow_html=True)
            if not unique_diags.empty:
                top10_diags = unique_diags.sort_values(by="Patients_Count", ascending=False).head(10)
                fig = px.bar(
                    top10_diags,
                    x="Patients_Count",
                    y="Diagnosis",
                    orientation="h",
                    title="Top Diagnoses by Patient Count",
                    labels={"Patients_Count": "Number of Patients", "Diagnosis": "Diagnosis"},
                    color="Patients_Count",
                    color_continuous_scale="Blues",
                )
                fig.update_layout(
                    title_font_size=16,
                    xaxis_title_font_size=12,
                    yaxis_title_font_size=12,
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No diagnosis data available.")

    else:
        st.markdown(
            """
            <div style="display: flex; justify-content: center; align-items: center; height: 300px; background-color: #0c1f29; border: 2px solid #37c2d8; border-radius: 10px; margin-top: 2rem;">
                <div style="text-align: center; color: #ffffff;">
                    <span style="font-size: 3rem;">📊</span>
                    <p style="font-size: 1.2rem; margin-top: 1rem;">Click "Show Data Analysis" to view patient information and statistics</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )