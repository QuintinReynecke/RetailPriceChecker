import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import scraper
import threading
import os
from datetime import datetime

class PriceCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Product Price Checker")
        self.root.geometry("500x300")
        
        # Styles
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        
        # UI Elements
        self.label_instruction = ttk.Label(root, text="Select your Excel file containing product URLs", font=("Helvetica", 12))
        self.label_instruction.pack(pady=20)
        
        self.btn_load = ttk.Button(root, text="Select Excel File", command=self.load_file)
        self.btn_load.pack(pady=10)
        
        self.lbl_file = ttk.Label(root, text="No file selected", foreground="gray")
        self.lbl_file.pack(pady=5)
        
        self.btn_run = ttk.Button(root, text="Get Product Prices", command=self.start_processing, state="disabled")
        self.btn_run.pack(pady=20)
        
        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)
        
        self.lbl_status = ttk.Label(root, text="Ready")
        self.lbl_status.pack(pady=5)
        
        self.file_path = None
        
    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx;*.xls")])
        if file_path:
            self.file_path = file_path
            self.lbl_file.config(text=f"Selected: {os.path.basename(file_path)}")
            self.btn_run.config(state="normal")
            
    def start_processing(self):
        if not self.file_path:
            return
            
        self.btn_run.config(state="disabled")
        self.btn_load.config(state="disabled")
        self.lbl_status.config(text="Processing... Please wait.")
        
        # Run in separate thread to keep UI responsive
        thread = threading.Thread(target=self.process_file)
        thread.start()
        
    def process_file(self):
        try:
            df = pd.read_excel(self.file_path)
            
            if 'URL' not in df.columns:
                messagebox.showerror("Error", "The Excel file must have a 'URL' column.")
                self.reset_ui()
                return

            total_urls = len(df)
            self.progress["maximum"] = total_urls
            
            results_list = []
            
            for index, row in df.iterrows():
                url = row['URL']
                self.root.after(0, lambda u=url: self.lbl_status.config(text=f"Checking: {u[:30]}..."))
                
                # Call new scraper function which returns a dict
                data = scraper.scrape_product(url)
                results_list.append(data)
                
                self.root.after(0, self.progress.step, 1)
                
            # Convert results to DataFrame
            results_df = pd.DataFrame(results_list)
            
            # Update original dataframe with new columns
            for col in results_df.columns:
                df[col] = results_df[col].values

            # Remove requested columns that are no longer needed
            cols_to_remove = ["1★", "2★", "3★", "4★", "5★"]
            df.drop(columns=[c for c in cols_to_remove if c in df.columns], inplace=True)

            df['Last Checked'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Save to new file
            directory = os.path.dirname(self.file_path)
            filename = os.path.basename(self.file_path)
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_updated_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            save_path = os.path.join(directory, new_filename)
            
            df.to_excel(save_path, index=False)
            
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Done! Saved as:\n{new_filename}"))
            self.root.after(0, lambda: self.lbl_status.config(text="Completed."))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred:\n{str(e)}"))
            self.root.after(0, lambda: self.lbl_status.config(text="Error."))
            
        finally:
            self.root.after(0, self.reset_ui)
            
    def reset_ui(self):
        self.btn_run.config(state="normal")
        self.btn_load.config(state="normal")
        self.progress["value"] = 0

if __name__ == "__main__":
    root = tk.Tk()
    app = PriceCheckerApp(root)
    root.mainloop()
