# OpenRouter Desktop Dashboard

A sleek, borderless floating widget built in Python that tracks your live OpenRouter API spend, credit balance, and model usage directly on your desktop. 

## Features
* **Always on Top:** Stays pinned above other windows for easy monitoring.
* **Live Analytics:** Connects to OpenRouter's Analytics API to show usage over the last 12 hours.
* **Auto-Refresh:** Automatically fetches new data and updates the UI every 5 minutes.
* **Balance Tracking:** Displays your live credit balance or Pay-As-You-Go status.
* **Custom Colors:** Easily map your favorite OpenRouter models to specific colors in the graph.

## How to Download and Run (Windows)
You do not need Python installed to run this dashboard. 
1. Go to the **Actions** tab at the top of this repository.
2. Click the latest successful build under "Build Windows EXE".
3. Scroll down to the **Artifacts** section and download the `OpenRouter-Dashboard` file.
4. Extract the `.exe` and place it anywhere on your computer.

## Setup & Configuration
When you launch the application for the first time, it will prompt you for an API key. 
1. Log into your OpenRouter account and go to **Settings > Management API Keys**.
2. Generate a new key. *(Note: Standard inference keys will not work, it must be a Management key to read analytics).*
3. Click the **⚙ (Settings)** button on the widget, paste your key, and click Save. 

Your key is saved locally to a tiny `or_config.json` file in the same folder as the application so you never have to enter it again. 

## Running from Source (For Developers)
If you prefer to run the Python script directly or modify the code:
1. Clone this repository.
2. Install the requirements: `pip install -r requirements.txt`
3. Run the application: `python or_dashboard.py`

## Customizing Model Colors
If you want the dashboard to perfectly match the colors in your OpenRouter web portal, simply open `or_dashboard.py` in a text editor and update the hex codes in the `CUSTOM_MODEL_COLORS` dictionary before running or compiling the script.

## License
Distributed under the MIT License. See `LICENSE` for more information.
