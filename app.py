import streamlit as st
import pandas as pd
import scraper
import os
import subprocess
from datetime import datetime
import time

# --- Helper: Install Playwright Browsers ---
def install_playwright():
    """Ensure Playwright browsers are installed (essential for Cloud)"""
    try:
        # Check if we can run a simple playwright command, if not, install
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"Failed to install Playwright browsers: {e}")

# Call installation once
if "playwright_installed" not in st.session_state:
    with st.spinner("Preparing scraping engine..."):
        install_playwright()
    st.session_state["playwright_installed"] = True

# --- UI Configuration ---
st.set_page_config(page_title="Product Price Checker", page_icon="🛒", layout="wide")

st.title("🛒 Product Price Checker")
st.markdown("""
Upload an Excel file with a list of product URLs to scrape the latest prices, stock status, and seller info.
**Supported Sites:** Takealot, Makro, Amazon.
""")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        
        if 'URL' not in df.columns:
            st.error("The Excel file must have a 'URL' column.")
        else:
            st.write(f"Loaded **{len(df)}** products.")
            st.dataframe(df.head())
            
            if st.button("🚀 Start Scraping"):
                urls = df['URL'].tolist()
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # --- Callback for Progress ---
                def update_progress(index, url):
                    progress = (index) / len(urls)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing ({index+1}/{len(urls)}): {url}")
                
                # --- Run Scraper ---
                with st.spinner("Scraping in progress... Do not close this tab."):
                    try:
                        results = scraper.scrape_products_batch(urls, progress_callback=update_progress)
                        
                        # --- Process Results ---
                        results_df = pd.DataFrame(results)
                        
                        # Merge results back to original
                        for col in results_df.columns:
                            df[col] = results_df[col].values
                            
                        # Cleanup Columns
                        cols_to_remove = ["1★", "2★", "3★", "4★", "5★"]
                        df.drop(columns=[c for c in cols_to_remove if c in df.columns], inplace=True)
                        df['Last Checked'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        progress_bar.progress(1.0)
                        status_text.success("Done!")
                        
                        st.success("Scraping Completed Successfully!")
                        st.dataframe(df)
                        
                        # --- Download ---
                        output_filename = f"checked_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        
                        # Save to a buffer (compatible with st.download_button)
                        # Pandas requires an engine for writing to buffer (openpyxl)
                        from io import BytesIO
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                            
                        st.download_button(
                            label="📥 Download Updated Excel",
                            data=buffer.getvalue(),
                            file_name=output_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                    except Exception as e:
                        st.error(f"An error occurred during scraping: {e}")
                        
    except Exception as e:
        st.error(f"Error reading file: {e}")
