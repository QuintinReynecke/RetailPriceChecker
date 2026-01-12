# Product Price Checker

This application allows you to track product prices from Amazon, Makro, and Takealot using an Excel file.

## Prerequisites

You need to have Python installed on your computer.

## Setup

1.  Open your command prompt (cmd) or terminal.
2.  Navigate to this folder:
    ```bash
    cd c:\Users\Quintin\Desktop\App\price_checker
    ```
3.  Install the required libraries:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install the browser engine**:
    ```bash
    playwright install
    ```

## How to Use

1.  **Create a Product List**:
    *   You can run the helper script to create a sample file:
        ```bash
        python create_sample_excel.py
        ```
    *   Or create your own Excel file (`.xlsx`) with a column named `URL`.

2.  **Run the Application**:
    ```bash
    python main.py
    ```

3.  **Get Prices**:
    *   Click "Select Excel File" and choose your `.xlsx` file.
    *   Click "Get Product Prices".
    *   Wait for the process to finish. A new file ending in `_updated_TIMESTAMP.xlsx` will be created with the prices.

## Notes

*   **Takealot**: Some Takealot pages load prices dynamically using JavaScript. This basic scraper attempts to find the price in the page source, but it might not work for all products. If you see "Not Found", it might require a more advanced browser simulation (like Selenium or Playwright), which requires more setup.
*   **Makro/Amazon**: These sites often block automated requests. The application uses a "fake user agent" to mimic a real browser, but frequent requests might still get blocked temporarily.
