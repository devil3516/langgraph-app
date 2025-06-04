from typing import Dict, Any, List
from datetime import datetime
from tools.build_itinerary import Itinerary, DayPlan, Activity

class ItineraryFormatter:
    def __init__(self):
        """Initialize the itinerary formatter"""
        pass

    def format_overview(self, itinerary: Itinerary) -> Dict[str, Any]:
        """Format overview data for display"""
        return {
            "destination": itinerary.destination,
            "duration": (itinerary.end_date - itinerary.start_date).days,
            "total_cost": itinerary.total_cost,
            "travel_style": itinerary.travel_style,
            "interests": itinerary.interests,
            "summary": itinerary.summary,
            "hotel": {
                "name": itinerary.hotel.name if itinerary.hotel else None,
                "address": itinerary.hotel.address if itinerary.hotel else None,
                "rating": itinerary.hotel.rating if itinerary.hotel else None,
                "price_per_night": itinerary.hotel.price_per_night if itinerary.hotel else None
            } if itinerary.hotel else None
        }

    def format_daily_plans(self, itinerary: Itinerary) -> List[Dict[str, Any]]:
        """Format daily plans for display"""
        formatted_plans = []
        for day in itinerary.daily_plans:
            formatted_activities = []
            for activity in day.activities:
                formatted_activities.append({
                    "name": activity.name,
                    "start_time": activity.start_time,
                    "end_time": activity.end_time,
                    "location": activity.location,
                    "description": activity.description,
                    "category": activity.category,
                    "cost": activity.cost,
                    "booking_url": activity.booking_url,
                    "notes": activity.notes
                })
            
            formatted_plans.append({
                "date": day.date.strftime("%Y-%m-%d"),
                "day_name": day.date.strftime("%A"),
                "total_cost": day.total_cost,
                "activities": formatted_activities,
                "notes": day.notes
            })
        
        return formatted_plans

    def format_budget_analysis(self, itinerary: Itinerary) -> Dict[str, Any]:
        """Format budget analysis data for display"""
        # Calculate category-wise costs
        category_costs = {}
        for day in itinerary.daily_plans:
            for activity in day.activities:
                if activity.cost:
                    if activity.category not in category_costs:
                        category_costs[activity.category] = 0
                    category_costs[activity.category] += activity.cost
        
        # Calculate daily costs
        daily_costs = [
            {
                "date": day.date.strftime("%Y-%m-%d"),
                "cost": day.total_cost
            }
            for day in itinerary.daily_plans
        ]
        
        return {
            "category_costs": category_costs,
            "daily_costs": daily_costs,
            "total_cost": itinerary.total_cost,
            "average_daily_cost": itinerary.total_cost / len(itinerary.daily_plans)
        }

    def format_activity_categories(self, itinerary: Itinerary) -> List[str]:
        """Get list of unique activity categories"""
        categories = set()
        for day in itinerary.daily_plans:
            for activity in day.activities:
                categories.add(activity.category)
        return sorted(list(categories))

    def format_for_display(self, itinerary: Itinerary) -> Dict[str, Any]:
        """
        Format the entire itinerary for display
        
        Args:
            itinerary (Itinerary): The itinerary to format
            
        Returns:
            Dict[str, Any]: Formatted data for display
        """
        return {
            "overview": self.format_overview(itinerary),
            "daily_plans": self.format_daily_plans(itinerary),
            "budget_analysis": self.format_budget_analysis(itinerary),
            "activity_categories": self.format_activity_categories(itinerary)
        }

def format_itinerary(itinerary: Itinerary) -> Dict[str, Any]:
    """
    Format an itinerary for display
    
    Args:
        itinerary (Itinerary): The itinerary to format
        
    Returns:
        Dict[str, Any]: Formatted data for display
    """
    formatter = ItineraryFormatter()
    return formatter.format_for_display(itinerary)

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
        
        # Format itinerary
        formatted_data = format_itinerary(itinerary)
        
        # Print formatted data (for testing)
        import json
        print(json.dumps(formatted_data, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

