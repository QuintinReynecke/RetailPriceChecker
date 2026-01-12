import pandas as pd

def create_sample():
    data = {
        'URL': [
            'https://www.amazon.com/dp/B08N5WRWNW', # Example placeholder
            'https://www.makro.co.za/electronics-computers/audio-visual/televisions/led-televisions/samsung-108cm-43-crystal-uhd-4k-tv-cu7000/p/000000000000456890_EA', # Example placeholder
            'https://www.takealot.com/russell-hobbs-2200w-crease-control-iron/PLID34147865' # Example placeholder
        ],
        'Current Price': ['', '', '']
    }
    
    df = pd.DataFrame(data)
    try:
        df.to_excel('products.xlsx', index=False)
        print("Successfully created products.xlsx")
    except Exception as e:
        print(f"Error creating excel file: {e}")

if __name__ == "__main__":
    create_sample()
