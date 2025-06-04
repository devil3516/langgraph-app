

from dataclasses import asdict
from datetime import datetime
from typing import Dict, Any, Optional
import json
import os
from pathlib import Path
import pdfkit
from jinja2 import Environment, FileSystemLoader
from tools.build_itinerary import Itinerary, DayPlan, Activity

class ItineraryExporter:
    def __init__(self, output_dir: str = "exports"):
        """
        Initialize the itinerary exporter
        
        Args:
            output_dir (str): Directory to save exported files
        """
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment for HTML templates
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
        # Create templates directory if it doesn't exist
        template_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default HTML template if it doesn't exist
        self._create_default_template()

    def _create_default_template(self):
        """Create a default HTML template for itinerary export"""
        template_path = Path(__file__).parent / "templates" / "itinerary.html"
        if not template_path.exists():
            template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Travel Itinerary - {{ itinerary.destination }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { text-align: center; margin-bottom: 30px; }
        .day { margin-bottom: 30px; border: 1px solid #ddd; padding: 20px; border-radius: 5px; }
        .activity { margin: 15px 0; padding: 10px; background: #f9f9f9; border-radius: 3px; }
        .time { color: #666; }
        .cost { color: #2c5282; }
        .notes { color: #718096; font-style: italic; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Travel Itinerary for {{ itinerary.destination }}</h1>
        <p>Duration: {{ itinerary.start_date.strftime('%B %d, %Y') }} to {{ itinerary.end_date.strftime('%B %d, %Y') }}</p>
        <p>Travel Style: {{ itinerary.travel_style }}</p>
        <p>Total Budget: ${{ "%.2f"|format(itinerary.total_cost) }}</p>
        <p>Interests: {{ itinerary.interests|join(', ') }}</p>
    </div>

    <div class="summary">
        <h2>Trip Summary</h2>
        <p>{{ itinerary.summary }}</p>
    </div>

    {% if itinerary.hotel %}
    <div class="hotel">
        <h2>Accommodation</h2>
        <p><strong>{{ itinerary.hotel.name }}</strong></p>
        <p>{{ itinerary.hotel.address }}</p>
    </div>
    {% endif %}

    <div class="itinerary">
        <h2>Detailed Itinerary</h2>
        {% for day in itinerary.daily_plans %}
        <div class="day">
            <h3>{{ day.date.strftime('%A, %B %d, %Y') }}</h3>
            <p>Total Cost: ${{ "%.2f"|format(day.total_cost) }}</p>
            
            {% for activity in day.activities %}
            <div class="activity">
                <h4>{{ activity.name }}</h4>
                <p class="time">{{ activity.start_time }} - {{ activity.end_time }}</p>
                <p>Location: {{ activity.location }}</p>
                <p>Category: {{ activity.category }}</p>
                {% if activity.cost %}
                <p class="cost">Cost: ${{ "%.2f"|format(activity.cost) }}</p>
                {% endif %}
                {% if activity.description %}
                <p>{{ activity.description }}</p>
                {% endif %}
                {% if activity.notes %}
                <p class="notes">Notes: {{ activity.notes }}</p>
                {% endif %}
            </div>
            {% endfor %}
            
            {% if day.notes %}
            <p class="notes">Day Notes: {{ day.notes }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""
            template_path.write_text(template_content)

    def export_json(self, itinerary: Itinerary, filename: Optional[str] = None) -> str:
        """
        Export itinerary as JSON file
        
        Args:
            itinerary (Itinerary): The itinerary to export
            filename (str, optional): Custom filename
            
        Returns:
            str: Path to the exported file
        """
        if filename is None:
            filename = f"itinerary_{itinerary.destination}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert itinerary to dictionary
        itinerary_dict = asdict(itinerary)
        
        # Convert datetime objects to strings
        itinerary_dict["start_date"] = itinerary_dict["start_date"].isoformat()
        itinerary_dict["end_date"] = itinerary_dict["end_date"].isoformat()
        
        for day_plan in itinerary_dict["daily_plans"]:
            day_plan["date"] = day_plan["date"].isoformat()
        
        # Write to file
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(itinerary_dict, f, indent=2, ensure_ascii=False)
        
        return filepath

    def export_html(self, itinerary: Itinerary, filename: Optional[str] = None) -> str:
        """
        Export itinerary as HTML file
        
        Args:
            itinerary (Itinerary): The itinerary to export
            filename (str, optional): Custom filename
            
        Returns:
            str: Path to the exported file
        """
        if filename is None:
            filename = f"itinerary_{itinerary.destination}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Render template
        template = self.env.get_template("itinerary.html")
        html_content = template.render(itinerary=itinerary)
        
        # Write to file
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath

    def export_pdf(self, itinerary: Itinerary, filename: Optional[str] = None) -> str:
        """
        Export itinerary as PDF file
        
        Args:
            itinerary (Itinerary): The itinerary to export
            filename (str, optional): Custom filename
            
        Returns:
            str: Path to the exported file
        """
        if filename is None:
            filename = f"itinerary_{itinerary.destination}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # First export as HTML
        html_filepath = self.export_html(itinerary, filename.replace('.pdf', '.html'))
        
        # Convert HTML to PDF
        pdf_filepath = os.path.join(self.output_dir, filename)
        try:
            pdfkit.from_file(html_filepath, pdf_filepath)
        except Exception as e:
            raise Exception(f"Failed to create PDF: {str(e)}")
        
        # Clean up temporary HTML file
        os.remove(html_filepath)
        
        return pdf_filepath

    def export_all(self, itinerary: Itinerary, base_filename: Optional[str] = None) -> Dict[str, str]:
        """
        Export itinerary in all available formats
        
        Args:
            itinerary (Itinerary): The itinerary to export
            base_filename (str, optional): Base filename without extension
            
        Returns:
            Dict[str, str]: Dictionary of format to filepath
        """
        if base_filename is None:
            base_filename = f"itinerary_{itinerary.destination}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "json": self.export_json(itinerary, f"{base_filename}.json"),
            "html": self.export_html(itinerary, f"{base_filename}.html"),
            "pdf": self.export_pdf(itinerary, f"{base_filename}.pdf")
        }

# Example usage
if __name__ == "__main__":
    from tools.build_itinerary import ItineraryBuilder
    from tools.parse_trip_prefs import parse_trip_preferences, TripPreferences
    from tools.search_hotels import HotelSearcher
    from tools.search_attractions import AttractionSearcher
    from langchain_groq import ChatGroq
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # Example trip preferences
    preferences = {
        "destination": "Paris",
        "start_date": "2024-06-01",
        "end_date": "2024-06-07",
        "budget": 2000,
        "travel_style": "moderate",
        "interests": ["culture", "food", "art"],
        "accommodation_preference": "hotel",
        "transportation_preference": "mixed"
    }
    
    try:
        # Parse preferences
        state = {"user_input": preferences}
        parsed_state = parse_trip_preferences(state)
        if "error" in parsed_state:
            raise Exception(parsed_state["error"])
        
        trip_prefs = TripPreferences(
            destination=parsed_state["destination"],
            start_date=parsed_state["start_date"],
            end_date=parsed_state["end_date"],
            budget=parsed_state["budget"],
            travel_style=parsed_state["travel_style"],
            interests=parsed_state["interests"],
            accommodation_preference=parsed_state["accommodation_preference"],
            transportation_preference=parsed_state["transportation_preference"],
            dietary_restrictions=parsed_state.get("dietary_restrictions"),
            special_requirements=parsed_state.get("special_requirements")
        )
        
        # Search for hotels and attractions
        hotel_searcher = HotelSearcher()
        attraction_searcher = AttractionSearcher()
        
        hotels = hotel_searcher.search_hotels(trip_prefs)
        attractions = attraction_searcher.search_attractions(trip_prefs)
        
        # Build itinerary
        llm_client = ChatGroq(api_key=GROQ_API_KEY)
        builder = ItineraryBuilder(llm_client)
        itinerary = builder.build_itinerary(
            trip_prefs,
            hotels[0] if hotels else None,
            attractions
        )
        
        # Export itinerary in all formats
        exporter = ItineraryExporter()
        exported_files = exporter.export_all(itinerary)
        
        print("Itinerary exported successfully:")
        for format, filepath in exported_files.items():
            print(f"{format.upper()}: {filepath}")
        
    except Exception as e:
        print(f"Error: {e}")

