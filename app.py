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
            # Initialize homophone column if it doesn't exist
            if 'homophone' not in df.columns:
                df['homophone'] = np.nan
            
            # Initialize session state for the dataframe if not already present
            if 'current_df' not in st.session_state:
                st.session_state.current_df = df.copy()
            else:
                # If we're reloading a file, update our stored dataframe
                # but preserve any classifications made in the current session
                if 'file_name' not in st.session_state or st.session_state.get('file_name') != uploaded_file.name:
                    st.session_state.current_df = df.copy()
                    st.session_state.file_name = uploaded_file.name
            
            # Use the session state dataframe for all operations
            df = st.session_state.current_df
            
            # Mark single occurrence words with homophone value of 1
            word_counts = df['word'].value_counts()
            single_words = word_counts[word_counts == 1].index
            df.loc[df['word'].isin(single_words), 'homophone'] = 1
                
            # Find duplicate words that haven't been classified yet
            duplicate_words = df[
                (df.duplicated(subset=['word'], keep=False)) & 
                (df['homophone'].isna())
            ]['word'].unique().tolist()
            
            # Check if there are any duplicates left to classify
            if len(duplicate_words) > 0:
                # Get the current word to classify
                if 'current_word_index' not in st.session_state:
                    st.session_state.current_word_index = 0
                
                current_word = duplicate_words[st.session_state.current_word_index]
                
                # Display the current word being classified
                st.header(f"Word: {current_word}")
                
                # Get all entries for this word
                word_entries = df[(df['word'] == current_word) & (df['homophone'].isna())]
                
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
                        indices = word_entries.index.tolist()
                        df.loc[indices, 'homophone'] = 1
                        
                        # Make sure we update the session state dataframe
                        st.session_state.current_df = df
                        
                        # Move to next word
                        st.session_state.current_word_index += 1
                        if st.session_state.current_word_index >= len(duplicate_words):
                            st.session_state.current_word_index = 0
                        st.experimental_rerun()
                
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
                        indices = word_entries.index.tolist()
                        for i, idx in enumerate(indices, start=1):
                            df.loc[idx, 'homophone'] = i
                        
                        # Make sure we update the session state dataframe
                        st.session_state.current_df = df
                        
                        # Move to next word
                        st.session_state.current_word_index += 1
                        if st.session_state.current_word_index >= len(duplicate_words):
                            st.session_state.current_word_index = 0
                        st.experimental_rerun()
                
                # Only show detailed classification if button is clicked
                if st.session_state.get('show_classification', False):
                    st.markdown("---")
                    st.markdown("### Homophone Group Classification")
                    st.markdown("Assign each entry to a homophone group (entries in the same group have the same meaning)")
                    
                    # Determine how many homophone groups we need
                    homophone_groups = min(5, len(word_entries))
                    
                    # Create a classification dataframe
                    classification_df = pd.DataFrame({
                        'Entry': [f"#{entry['index']}-{entry['sub_index']}: {entry['gloss'][:50]}" 
                                for _, entry in word_entries.iterrows()]
                    })
                    
                    # Create a more user-friendly selection interface with radio buttons
                    for i in range(len(classification_df)):
                        st.markdown(f"**{classification_df.loc[i, 'Entry']}**")
                        
                        # Use radio buttons for mutually exclusive selection
                        selected_group = st.radio(
                            "Select group:",
                            options=list(range(1, homophone_groups + 1)),
                            horizontal=True,
                            key=f"radio_{i}",
                            index=0  # Default to group 1
                        )
                        
                        # Store the selection in session state
                        if 'selections' not in st.session_state:
                            st.session_state.selections = {}
                        st.session_state.selections[i] = selected_group
                        
                        st.markdown("---")
                    
                    if st.button("Save Classification & Continue"):
                        # Process the selections and update the dataframe
                        for i, (idx, entry) in enumerate(word_entries.iterrows()):
                            selected_group = st.session_state.selections.get(i, 1)
                            df.loc[idx, 'homophone'] = selected_group
                        
                        # Make sure we update the session state dataframe
                        st.session_state.current_df = df
                        
                        # Reset classification view and move to next word
                        st.session_state.show_classification = False
                        if 'selections' in st.session_state:
                            del st.session_state.selections
                        st.session_state.current_word_index += 1
                        if st.session_state.current_word_index >= len(duplicate_words):
                            st.session_state.current_word_index = 0
                        st.experimental_rerun()
                
                # Show progress
                st.markdown("---")
                progress = min(1.0, (st.session_state.current_word_index + 1) / len(duplicate_words))
                st.progress(progress)
                st.write(f"Progress: {st.session_state.current_word_index + 1}/{len(duplicate_words)} words to classify")
            
            else:
                # All words have been classified
                st.success("✅ All words have been classified! Download your completed Excel file below.")
            
            # Always show export button at the bottom
            st.markdown("---")
            st.markdown("### Export Database")
            st.markdown("You can export the database at any time. Simply re-upload the database the next time you run this app to continue your work on this data set.")
            
            # Store the dataframe in session state to ensure it persists between reruns
            if 'current_df' not in st.session_state:
                st.session_state.current_df = df
            else:
                # Make sure we're using the most up-to-date version
                st.session_state.current_df = df
            
            st.download_button(
                label="Export Database",
                data=to_excel_bytes(st.session_state.current_df),
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