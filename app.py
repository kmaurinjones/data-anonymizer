import modules
import streamlit as st
from streamlit_extras.let_it_rain import rain

# Options
DISCLAIMER = """
    *This app processes data using 2-anonymity, an implementation of the k-anonymity framework. While this is a great start to anonymizing your data, it is by no means perfect, and should be used with caution. For example, some sets of sensitive features which may clearly be identified by a human could be missed by our algorithm. Please keep this in mind.*
    """
K = 2

# Page Config
st.set_page_config(layout="wide")

### FILE LOADER for sidebar
with st.sidebar:
    st.header("🕵️ 2anonymity")
    st.markdown("*Clean and anonymize data*")
    with st.container() as upload:
        file = st.file_uploader(f"Upload dataset:", type=modules.SUPPORTED_TYPES, label_visibility="collapsed")
        df, (filename, extension), result = modules.load_file(file)

### MAIN
if df is None: # Await file to be uploaded
    rain("🤠")
else:
    ### PRE-TRANSFORM features for sidebar
    with st.sidebar:
        # Options for data loading
        with st.container() as loading_options:
            st.markdown("### Data loading options:")
            remove_duplicates = st.checkbox("Remove duplicate rows", value=True)
            drop_missing = st.checkbox("Remove rows with missing values", value=False)

        # Options for data optimization
        with st.container() as anonymizing_options:
            st.markdown("### Anonymizing options:")
            max_categorical_size = st.slider("Categorical Variable Threshold", min_value=2, max_value=200, value=50, step=1)
            bin_size = st.slider("Bin Size", min_value=2, max_value=200, value=20, step=1)
            redaction_selection = st.selectbox("Redaction strength", ["Low", "Medium", "High", "Extreme"])
            sensitivity_minimum = {"Low": 2, "Medium": 4, "High": 6, "Extreme": 12}[redaction_selection]
    
    
    ### DATA PREVIEW AND TRANSFORM
    # Preview data before transform
    with st.container() as before_data:
        s = df.style
        s = s.set_properties(**{'background-color': '#fce4e4'})
        st.dataframe(s)

    # Transform data
    df = modules.data_cleaner(df, drop_missing, remove_duplicates)
    df, unprocessed = modules.data_anonymizer(df, K, max_categorical_size, bin_size, sensitivity_minimum)

    # Preview data after before_data
    with st.container() as after_data:
        s = df.style
        s = s.set_properties(**{'background-color': '#e4fce4'})
        st.dataframe(s)


    ### POST-TRANSFORM features for sidebar
    with st.sidebar:
        # Options for download
        with st.container() as download_header:
            st.markdown("### Download options:")
            output_extension = st.selectbox("File type", [".csv", ".json", ".xlsx"])
            if unprocessed: st.markdown(f"Error encountered when processing columns {str(unprocessed)}")
 
        # Prepare file for download
        with st.container() as downloader:
            if output_extension == ".csv": output_file = df.to_csv().encode("utf-8")
            elif output_extension == ".json": output_file = df.to_json().encode("utf-8")
            elif output_extension == ".xlsx": output_file = df.to_excel().encode("utf-8")
            output_filename = f"""{filename.split(".")[:-1][0]}-clean{output_extension}"""
            st.download_button("Download", output_file, file_name=output_filename)
        
        # Add a disclaimer for data security
        with st.container() as disclaimer:
            st.markdown(
                f"""
                Disclaimer:  
                {DISCLAIMER}
                """
                )
        
# Attribution
st.sidebar.markdown("Created by team #2hack2furious for the hackthethreat2023")