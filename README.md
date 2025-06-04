# Travel Itinerary Planner

An AI-powered travel itinerary planner that helps you create detailed travel plans based on your preferences.

## Features

- Search for hotels and attractions based on your preferences
- Generate detailed day-by-day itineraries
- Export itineraries in multiple formats (PDF, JSON, HTML)
- Interactive UI with data visualization
- Budget tracking and analysis

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Travel-ltinerary-planner-agent
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Install wkhtmltopdf (required for PDF export):
   - macOS: `brew install wkhtmltopdf`
   - Ubuntu: `sudo apt-get install wkhtmltopdf`
   - Windows: Download from https://wkhtmltopdf.org/downloads.html

5. Create a `.env` file in the project root with your API keys:
```
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

## Usage

1. Start the application:
```bash
streamlit run app.py
```

2. Open your web browser and navigate to the URL shown in the terminal (usually http://localhost:8501)

3. Follow the step-by-step process:
   - Enter your travel preferences
   - Select hotels and attractions
   - Generate and customize your itinerary
   - Export in your preferred format

## API Keys

You'll need to obtain API keys for:
1. Groq API (for LLM-powered itinerary generation)
2. Tavily API (for hotel and attraction searches)

## Project Structure

- `app.py`: Main Streamlit application
- `tools/`: Core functionality modules
  - `build_itinerary.py`: Itinerary generation
  - `search_hotels.py`: Hotel search
  - `search_attractions.py`: Attraction search
  - `export_itinerary.py`: Export functionality
- `utils/`: Utility modules
  - `formatter.py`: Data formatting utilities

## Contributing

Feel free to submit issues and enhancement requests! 