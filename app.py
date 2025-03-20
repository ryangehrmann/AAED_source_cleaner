import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="AAED Source Data Cleaner", layout="wide")

# App title and instructions
st.title("AAED Source Data Cleaner")
st.markdown("""
This app helps identify and classify duplicate words in linguistic databases.
1. Upload an Excel file containing word entries
2. Review duplicated word forms one by one
3. Classify them as either the same word or different homophones
4. Download the updated Excel file with homophone classifications
""")

# Helper functions
def to_excel_bytes(df):
    """Convert dataframe to Excel bytes for download"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# File uploader
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Load the data
    try:
        df = pd.read_excel(uploaded_file)
        
        # Check if required columns exist
        required_columns = ['index', 'sub_index', 'entry', 'gloss', 'word']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}")
        else:
            # Initialize or update the main dataframe
            if 'main_df' not in st.session_state:
                # First time loading this file
                st.session_state.main_df = df.copy()
                
                # Initialize homophone column if it doesn't exist
                if 'homophone' not in st.session_state.main_df.columns:
                    st.session_state.main_df['homophone'] = np.nan
            else:
                # If uploading a new file, replace main_df
                if 'file_name' not in st.session_state or st.session_state.file_name != uploaded_file.name:
                    st.session_state.main_df = df.copy()
                    
                    # Initialize homophone column if it doesn't exist
                    if 'homophone' not in st.session_state.main_df.columns:
                        st.session_state.main_df['homophone'] = np.nan
                    
                    # Remember the file name
                    st.session_state.file_name = uploaded_file.name
            
            # Use the session state dataframe for all operations
            df = st.session_state.main_df
                
            # Mark single occurrence words with homophone value of 1
            word_counts = df['word'].value_counts()
            single_words = word_counts[word_counts == 1].index
            df.loc[df['word'].isin(single_words), 'homophone'] = 1
            
            # Get only unclassified rows
            unclassified_df = df[df['homophone'].isna()].copy()
            
            # If we're just starting and haven't processed anything yet
            if 'working_df' not in st.session_state:
                st.session_state.working_df = unclassified_df.copy()
            
            # Check if there are any unclassified rows left
            if len(st.session_state.working_df) > 0:
                # Get the first word that needs classification
                current_word = st.session_state.working_df['word'].iloc[0]
                
                # Get all entries for this word
                word_entries = st.session_state.working_df[st.session_state.working_df['word'] == current_word]
                
                # Display the current word being classified
                st.header(f"Word: {current_word}")
                
                # Display entries in a table format for easier scanning
                st.subheader(f"Entries containing this word ({len(word_entries)} occurrences):")
                
                # Create a display dataframe with just the relevant columns
                display_df = word_entries[['index', 'sub_index', 'entry', 'gloss']].copy()
                display_df['index'] = display_df['index'].astype(str) + '-' + display_df['sub_index'].astype(str)
                display_df = display_df.drop('sub_index', axis=1)
                display_df.columns = ['Index', 'Entry', 'Gloss']
                
                # Display the table with wrapped text for better readability
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    column_config={
                        "Index": st.column_config.TextColumn("Index", width="small"),
                        "Entry": st.column_config.TextColumn("Entry", width="medium"),
                        "Gloss": st.column_config.TextColumn("Gloss", width="large"),
                    },
                    hide_index=True
                )
                
                # Classification section
                st.subheader("Classification")
                
                # Create three buttons for classification options
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("Just one word (mark all the same)", 
                                use_container_width=True,
                                help="Select this if all occurrences are the same word with the same meaning"):
                        # Mark all with homophone value of 1
                        for idx, row in word_entries.iterrows():
                            # Update in our main dataframe
                            st.session_state.main_df.loc[
                                (st.session_state.main_df['index'] == row['index']) & 
                                (st.session_state.main_df['sub_index'] == row['sub_index']), 
                                'homophone'
                            ] = 1
                        
                        # Remove processed words from working dataframe
                        st.session_state.working_df = st.session_state.working_df[st.session_state.working_df['word'] != current_word]
                        st.rerun()
                
                with col2:
                    if st.button("More than one word (need to classify)", 
                                use_container_width=True,
                                help="Select this if some occurrences have different meanings and need manual classification"):
                        # Toggle homophone classification visibility
                        st.session_state.show_classification = True
                
                with col3:
                    if st.button("All different words (mark all as different)", 
                                use_container_width=True,
                                help="Select this if each occurrence is a different word/meaning"):
                        # Assign sequential numbers to each occurrence
                        for i, (idx, row) in enumerate(word_entries.iterrows(), start=1):
                            # Update in our main dataframe
                            st.session_state.main_df.loc[
                                (st.session_state.main_df['index'] == row['index']) & 
                                (st.session_state.main_df['sub_index'] == row['sub_index']), 
                                'homophone'
                            ] = i
                        
                        # Remove processed words from working dataframe
                        st.session_state.working_df = st.session_state.working_df[st.session_state.working_df['word'] != current_word]
                        st.rerun()
                
                # Only show detailed classification if button is clicked
                if st.session_state.get('show_classification', False):
                    st.markdown("---")
                    st.markdown("### Homophone Group Classification")
                    st.markdown("Assign each entry to a homophone group (entries in the same group have the same meaning)")
                    
                    # Determine how many homophone groups we need
                    homophone_groups = min(5, len(word_entries))
                    
                    # Create a classification dataframe
                    classification_df = pd.DataFrame({
                        'Entry': [f"#{row['index']}-{row['sub_index']}: {row['gloss'][:50]}" 
                                for _, row in word_entries.iterrows()]
                    })
                    
                    # Create a more user-friendly selection interface with radio buttons
                    selection_values = {}
                    for i, (idx, row) in enumerate(word_entries.iterrows()):
                        st.markdown(f"**{classification_df.loc[i, 'Entry']}**")
                        
                        # Use radio buttons for mutually exclusive selection
                        selected_group = st.radio(
                            "Select group:",
                            options=list(range(1, homophone_groups + 1)),
                            horizontal=True,
                            key=f"radio_{i}",
                            index=0  # Default to group 1
                        )
                        
                        # Store the selection
                        selection_values[i] = {
                            "index": row['index'],
                            "sub_index": row['sub_index'],
                            "group": selected_group
                        }
                        
                        st.markdown("---")
                    
                    if st.button("Save Classification & Continue"):
                        # Process the selections and update the dataframe
                        for i, selection in selection_values.items():
                            # Update in our main dataframe
                            st.session_state.main_df.loc[
                                (st.session_state.main_df['index'] == selection["index"]) & 
                                (st.session_state.main_df['sub_index'] == selection["sub_index"]), 
                                'homophone'
                            ] = selection["group"]
                        
                        # Remove processed words from working dataframe
                        st.session_state.working_df = st.session_state.working_df[st.session_state.working_df['word'] != current_word]
                        
                        # Reset classification view
                        st.session_state.show_classification = False
                        st.rerun()
                
                # Show progress
                st.markdown("---")
                total_unclassified = len(st.session_state.main_df[st.session_state.main_df['homophone'].isna()])
                total_words = len(st.session_state.main_df)
                classified_words = total_words - total_unclassified
                progress = classified_words / total_words
                st.progress(progress)
                st.write(f"Progress: {classified_words}/{total_words} words classified ({progress:.1%})")
                
                # Add a skip button for troubleshooting
                if st.button("Skip this word"):
                    # Move this word to the end of the working dataframe
                    skipped_entries = st.session_state.working_df[st.session_state.working_df['word'] == current_word]
                    remaining_entries = st.session_state.working_df[st.session_state.working_df['word'] != current_word]
                    st.session_state.working_df = pd.concat([remaining_entries, skipped_entries])
                    st.rerun()
            
            else:
                # All words have been classified
                st.success("✅ All words have been classified! Download your completed Excel file below.")
            
            # Always show export button at the bottom
            st.markdown("---")
            st.markdown("### Export Database")
            st.markdown("You can export the database at any time. Simply re-upload the database the next time you run this app to continue your work on this data set.")
            
            # Make sure we're using the current state of the dataframe
            export_df = st.session_state.main_df
            
            st.download_button(
                label="Export Database",
                data=to_excel_bytes(export_df),
                file_name=f"classified_{uploaded_file.name}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # Show stats
            total_words = len(df)
            classified_words = df['homophone'].notna().sum()
            st.markdown(f"**Classification Stats:** {classified_words}/{total_words} words classified ({classified_words/total_words:.1%})")
            
    except Exception as e:
        st.error(f"Error processing file: {e}")
        st.write("Please check if the file has the required columns: 'index', 'sub_index', 'entry', 'gloss', 'word'")
else:
    st.info("""
    Please upload an Excel file to begin.
    
    Expected columns:
    - "index" - original indexing system
    - "sub_index" - order of word forms in an entry
    - "entry" - words in context from dictionary entries
    - "gloss" - corresponding English glosses
    - "word" - individual word forms (where we'll find duplicates)
    """)