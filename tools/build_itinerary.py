from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import os
from tools.parse_trip_prefs import TripPreferences
from tools.search_hotels import Hotel
from tools.search_attractions import Attraction

from langchain_groq import ChatGroq
from langchain.schema import HumanMessage

from dotenv import load_dotenv
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

@dataclass
class Activity:
    name: str
    start_time: str
    end_time: str
    location: str
    description: str
    category: str
    cost: Optional[float]
    booking_url: Optional[str]
    notes: Optional[str]

@dataclass
class DayPlan:
    date: datetime
    activities: List[Activity]
    total_cost: float
    notes: Optional[str]

@dataclass
class Itinerary:
    destination: str
    start_date: datetime
    end_date: datetime
    daily_plans: List[DayPlan]
    total_cost: float
    travel_style: str
    interests: List[str]
    hotel: Optional[Hotel]
    summary: str

class ItineraryBuilder:
    def __init__(self, llm_client: ChatGroq):
        """
        Initialize the itinerary builder with a Groq LLM client
        
        Args:
            llm_client (ChatGroq): Initialized Groq chat model
        """
        if not isinstance(llm_client, ChatGroq):
            raise ValueError("llm_client must be an instance of ChatGroq")
        self.llm_client = llm_client

    def _create_llm_prompt(
        self,
        trip_prefs: TripPreferences,
        hotel: Optional[Hotel],
        attractions: List[Attraction]
    ) -> str:
        """Create a prompt for the LLM to generate an itinerary"""
        prompt = f"""Create a detailed travel itinerary for a trip to {trip_prefs.destination} 
from {trip_prefs.start_date.date()} to {trip_prefs.end_date.date()}.

Travel Style: {trip_prefs.travel_style}
Budget: ${trip_prefs.budget}
Interests: {', '.join(trip_prefs.interests)}

Hotel: {hotel.name if hotel else 'Not selected yet'}
Hotel Location: {hotel.address if hotel else 'Not available'}

Available Attractions:
{self._format_attractions_for_prompt(attractions)}

Please create a day-by-day itinerary that:
1. Optimizes time and location (group nearby attractions)
2. Matches the travel style and budget
3. Includes a mix of activities based on interests
4. Includes reasonable travel times between locations
5. Includes meal times and rest periods
6. Provides estimated costs for each activity
7. Considers opening hours and visit durations
8. Includes transportation between locations
9. Accounts for weather and seasonal factors
10. Includes backup activities in case of bad weather

Format the response as a JSON object with the following structure:
{{
    "daily_plans": [
        {{
            "date": "YYYY-MM-DD",
            "activities": [
                {{
                    "name": "Activity name",
                    "start_time": "HH:MM",
                    "end_time": "HH:MM",
                    "location": "Location name",
                    "description": "Brief description",
                    "category": "Activity category",
                    "cost": 0.0,
                    "booking_url": "Optional URL",
                    "notes": "Optional notes"
                }}
            ],
            "total_cost": 0.0,
            "notes": "Optional day notes"
        }}
    ],
    "total_cost": 0.0,
    "summary": "Brief trip summary"
}}

Ensure all dates are in YYYY-MM-DD format and times are in HH:MM 24-hour format.
Make sure the total cost matches the sum of all activity costs.
Include realistic travel times between locations.
Consider local customs and peak hours for attractions.
"""
        return prompt

    def _format_attractions_for_prompt(self, attractions: List[Attraction]) -> str:
        formatted = []
        for i, attraction in enumerate(attractions, 1):
            formatted.append(f"{i}. {attraction.name}")
            formatted.append(f"   Category: {attraction.category}")
            formatted.append(f"   Duration: {attraction.visit_duration or 'Not specified'}")
            formatted.append(f"   Price Level: {attraction.price_level or 'Not specified'}")
            formatted.append(f"   Rating: {attraction.rating or 'Not specified'}/5.0")
            formatted.append("")
        return "\n".join(formatted)

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1]
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    def build_itinerary(
        self,
        trip_prefs: TripPreferences,
        hotel: Optional[Hotel],
        attractions: List[Attraction]
    ) -> Itinerary:
        """Build a complete travel itinerary"""
        try:
            prompt = self._create_llm_prompt(trip_prefs, hotel, attractions)
            
            # Create a human message for the LLM
            message = HumanMessage(content=prompt)
            
            # Get response from Groq
            response = self.llm_client.invoke([message])
            response_text = response.content
            
            if not response_text:
                raise ValueError("Empty response from LLM")
            
            itinerary_data = self._parse_llm_response(response_text)
            
            # Validate itinerary data
            if not itinerary_data.get("daily_plans"):
                raise ValueError("No daily plans in itinerary")
            
            daily_plans = []
            total_cost = 0.0
            
            for day_data in itinerary_data["daily_plans"]:
                activities = [
                    Activity(
                        name=act["name"],
                        start_time=act["start_time"],
                        end_time=act["end_time"],
                        location=act["location"],
                        description=act["description"],
                        category=act["category"],
                        cost=act.get("cost"),
                        booking_url=act.get("booking_url"),
                        notes=act.get("notes")
                    )
                    for act in day_data["activities"]
                ]
                
                day_cost = day_data["total_cost"]
                total_cost += day_cost
                
                daily_plans.append(
                    DayPlan(
                        date=datetime.strptime(day_data["date"], "%Y-%m-%d"),
                        activities=activities,
                        total_cost=day_cost,
                        notes=day_data.get("notes")
                    )
                )
            
            # Verify total cost matches
            if abs(total_cost - itinerary_data["total_cost"]) > 0.01:
                raise ValueError("Total cost mismatch in itinerary")
            
            return Itinerary(
                destination=trip_prefs.destination,
                start_date=trip_prefs.start_date,
                end_date=trip_prefs.end_date,
                daily_plans=daily_plans,
                total_cost=total_cost,
                travel_style=trip_prefs.travel_style,
                interests=trip_prefs.interests,
                hotel=hotel,
                summary=itinerary_data["summary"]
            )
            
        except Exception as e:
            raise ValueError(f"Failed to build itinerary: {str(e)}")


def format_itinerary(itinerary: Itinerary) -> str:
    lines = [
        f"Travel Itinerary for {itinerary.destination}",
        f"Duration: {itinerary.start_date.date()} to {itinerary.end_date.date()}",
        f"Travel Style: {itinerary.travel_style}",
        f"Total Budget: ${itinerary.total_cost:.2f}",
        f"Interests: {', '.join(itinerary.interests)}",
        "\nSummary:",
        itinerary.summary,
        "\nDetailed Itinerary:"
    ]
    
    for day_plan in itinerary.daily_plans:
        lines.append(f"\n{day_plan.date.strftime('%A, %B %d, %Y')}")
        lines.append(f"Total Cost: ${day_plan.total_cost:.2f}")
        
        for activity in day_plan.activities:
            lines.append(f"\n{activity.start_time} - {activity.end_time}: {activity.name}")
            lines.append(f"Location: {activity.location}")
            lines.append(f"Category: {activity.category}")
            if activity.cost:
                lines.append(f"Cost: ${activity.cost:.2f}")
            if activity.description:
                lines.append(f"Description: {activity.description}")
            if activity.notes:
                lines.append(f"Notes: {activity.notes}")
        
        if day_plan.notes:
            lines.append(f"\nDay Notes: {day_plan.notes}")
    
    return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    from tools.parse_trip_prefs import parse_trip_preferences, TripPreferences
    from tools.search_hotels import HotelSearcher
    from tools.search_attractions import AttractionSearcher

    # Initialize Groq client with model name
    llm_client = ChatGroq(
        api_key=GROQ_API_KEY,
        model_name="mistral-saba-24b"  # or another Groq model
    )

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

        hotel_searcher = HotelSearcher()
        attraction_searcher = AttractionSearcher()

        hotels = hotel_searcher.search_hotels(trip_prefs)
        attractions = attraction_searcher.search_attractions(trip_prefs)

        builder = ItineraryBuilder(llm_client)
        itinerary = builder.build_itinerary(
            trip_prefs,
            hotels[0] if hotels else None,
            attractions
        )

        print(format_itinerary(itinerary))

    except Exception as e:
        print(f"Error: {e}")
