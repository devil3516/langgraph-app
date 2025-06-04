from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import requests
import re
import os
from dotenv import load_dotenv

# Assuming you have this dataclass in tools.parse_trip_prefs
from tools.parse_trip_prefs import TripPreferences

load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

@dataclass
class Hotel:
    name: str
    address: Optional[str]  # Real address if available; else None
    price_per_night: Optional[float]
    rating: Optional[float]
    amenities: List[str]
    room_type: Optional[str]
    booking_url: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    images: List[str]
    description: str
    source: str

class HotelSearchError(Exception):
    """Custom exception for hotel search errors"""
    pass

class HotelSearcher:
    def __init__(self, tavily_api_key: Optional[str] = None):
        """
        Initialize the hotel searcher with API credentials

        Args:
            tavily_api_key (str, optional): API key for Tavily search
        """
        # Try to get API key from parameter, then environment variable
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        
        # Validate API key
        if not self.tavily_api_key:
            raise ValueError("Tavily API key is required. Please set TAVILY_API_KEY in your .env file or pass it to the constructor.")
        
        if not isinstance(self.tavily_api_key, str) or not self.tavily_api_key.strip():
            raise ValueError("Invalid Tavily API key format. The key must be a non-empty string.")
            
        self.tavily_url = "https://api.tavily.com/search"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.tavily_api_key.strip()}"
        }

    def _format_date(self, date: datetime) -> str:
        """Format datetime object to API required format YYYY-MM-DD"""
        return date.strftime("%Y-%m-%d")

    def _get_price_range(self, travel_style: str, budget: float) -> Tuple[float, float]:
        """Calculate price range based on travel style and total budget"""
        travel_style = travel_style.lower()
        if travel_style == "luxury":
            return (budget * 0.4, budget * 0.6)
        elif travel_style == "moderate":
            return (budget * 0.2, budget * 0.4)
        else:  # budget or others
            return (0, budget * 0.2)

    def _extract_price(self, text: str) -> Optional[float]:
        """Extract price from text using regex (expects $ followed by number)"""
        price_pattern = r'\$(\d+(?:\.\d{2})?)'
        match = re.search(price_pattern, text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def _extract_rating(self, text: str) -> Optional[float]:
        """Extract rating from text using regex, e.g. '4.5 / 5'"""
        rating_pattern = r'(\d+(?:\.\d)?)\s*\/\s*5'
        match = re.search(rating_pattern, text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def _parse_hotel_from_search_result(self, result: Dict[str, Any]) -> Hotel:
        """Parse search result dict into Hotel object"""
        name = result.get("title", "").split(" - ")[0]  # Remove suffixes after dash if any
        description = result.get("content", "")

        price = self._extract_price(description)
        rating = self._extract_rating(description)

        amenities = []
        amenity_keywords = {
            "wifi": ["wifi", "wireless internet", "free wifi"],
            "pool": ["pool", "swimming pool", "indoor pool", "outdoor pool"],
            "gym": ["gym", "fitness center", "workout room"],
            "restaurant": ["restaurant", "dining", "breakfast", "room service"],
            "spa": ["spa", "massage", "wellness center"],
            "parking": ["parking", "free parking", "valet parking"],
            "bar": ["bar", "lounge", "pub"],
            "conference": ["conference room", "meeting room", "business center"],
            "laundry": ["laundry", "dry cleaning", "washing machine"],
            "air_conditioning": ["air conditioning", "ac", "climate control"],
            "elevator": ["elevator", "lift"],
            "accessibility": ["wheelchair accessible", "disabled access"],
            "pet_friendly": ["pet friendly", "pets allowed"],
            "shuttle": ["shuttle", "airport shuttle", "free shuttle"],
            "kitchen": ["kitchen", "kitchenette", "cooking facilities"]
        }
        
        for amenity, keywords in amenity_keywords.items():
            if any(keyword in description.lower() for keyword in keywords):
                amenities.append(amenity)

        # Try to extract real address if available; fallback to None
        address = result.get("address") or None

        return Hotel(
            name=name,
            address=address,
            price_per_night=price,
            rating=rating,
            amenities=amenities,
            room_type=None,  # Not available in search results
            booking_url=result.get("url"),
            latitude=None,
            longitude=None,
            images=[],
            description=description,
            source=result.get("source", "Unknown")
        )

    def search_hotels(self, trip_prefs: TripPreferences, num_results: int = 5) -> List[Hotel]:
        """
        Search for hotels based on trip preferences using Tavily search API.

        Args:
            trip_prefs (TripPreferences): User's trip preferences
            num_results (int): Number of results to return

        Returns:
            List[Hotel]: List of matching hotels

        Raises:
            HotelSearchError: If there is an error during the search
        """
        try:
            if not trip_prefs.destination:
                raise ValueError("Destination is required")
            
            # Calculate price range from budget and travel style
            min_price, max_price = self._get_price_range(trip_prefs.travel_style, trip_prefs.budget)

            # Construct the search query string
            query = (
                f"hotels in {trip_prefs.destination} "
                f"from {self._format_date(trip_prefs.start_date)} "
                f"to {self._format_date(trip_prefs.end_date)} "
                f"{trip_prefs.travel_style} style "
                f"price range ${min_price:.0f}-${max_price:.0f}"
            )

            params = {
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "include_domains": [
                    "booking.com",
                    "hotels.com",
                    "expedia.com",
                    "tripadvisor.com",
                    "agoda.com",
                    "hotel.com"
                ],
                "max_results": num_results,
                "include_raw_content": True
            }

            response = requests.post(self.tavily_url, headers=self.headers, json=params)
            response.raise_for_status()

            results = response.json().get("results", [])
            if not results:
                raise HotelSearchError("No hotels found matching your criteria")
            
            hotels = [self._parse_hotel_from_search_result(r) for r in results]
            
            # Sort by rating if available
            hotels.sort(key=lambda x: x.rating or 0, reverse=True)
            
            return hotels

        except requests.RequestException as e:
            raise HotelSearchError(f"API request failed: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise HotelSearchError(f"Failed to parse hotel data: {e}")
        except Exception as e:
            raise HotelSearchError(f"Unexpected error: {e}")

    def get_hotel_details(self, hotel_id: str) -> Hotel:
        """
        Retrieve detailed information about a specific hotel by ID.

        Args:
            hotel_id (str): Hotel identifier

        Returns:
            Hotel: Detailed hotel information

        Raises:
            HotelSearchError: If there is an error retrieving hotel details
        """
        try:
            url = f"{self.tavily_url}/{hotel_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            return self._parse_hotel_from_search_result(data)

        except requests.RequestException as e:
            raise HotelSearchError(f"API request failed: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise HotelSearchError(f"Failed to parse hotel details: {e}")

def format_hotel_results(hotels: List[Hotel]) -> str:
    """
    Format a list of Hotel objects into a readable string.

    Args:
        hotels (List[Hotel]): List of hotel results

    Returns:
        str: Formatted string
    """
    if not hotels:
        return "No hotels found matching your criteria."

    lines = ["Found the following hotels:\n"]
    for i, hotel in enumerate(hotels, start=1):
        lines.append(f"{i}. {hotel.name}")
        if hotel.price_per_night is not None:
            lines.append(f"   Price per night: ${hotel.price_per_night:.2f}")
        if hotel.rating is not None:
            lines.append(f"   Rating: {hotel.rating}/5.0")
        if hotel.amenities:
            lines.append(f"   Amenities: {', '.join(hotel.amenities)}")
        if hotel.booking_url:
            lines.append(f"   Booking URL: {hotel.booking_url}")
        lines.append(f"   Source: {hotel.source}")
        desc_preview = hotel.description[:200].replace('\n', ' ').strip()
        lines.append(f"   Description: {desc_preview}...\n")

    return "\n".join(lines)

# Helper to convert dict preferences to TripPreferences with proper types
def dict_to_trip_prefs(data: Dict[str, Any]) -> TripPreferences:
    """
    Convert a plain dictionary of preferences to a TripPreferences dataclass instance.
    Parses date strings into datetime objects.
    """
    return TripPreferences(
        destination=data["destination"],
        start_date=datetime.strptime(data["start_date"], "%Y-%m-%d"),
        end_date=datetime.strptime(data["end_date"], "%Y-%m-%d"),
        budget=float(data["budget"]),
        travel_style=data["travel_style"],
        interests=data.get("interests", []),
        accommodation_preference=data.get("accommodation_preference", ""),
        transportation_preference=data.get("transportation_preference", ""),
        dietary_restrictions=data.get("dietary_restrictions"),
        special_requirements=data.get("special_requirements"),
    )

# Example usage
if __name__ == "__main__":
    # Replace with your actual Tavily API key
    TAVILY_API_KEY = "your_tavily_api_key_here"

    # Example trip preferences dictionary (as might come from user input)
    preferences = {
        "destination": "Paris",
        "start_date": "2024-06-01",
        "end_date": "2024-06-07",
        "budget": 2000,
        "travel_style": "moderate",
        "interests": ["culture", "food"],
        "accommodation_preference": "hotel",
        "transportation_preference": "mixed"
    }

    try:
        # Convert dict to TripPreferences object
        trip_prefs = dict_to_trip_prefs(preferences)

        # Initialize searcher with API key
        searcher = HotelSearcher(TAVILY_API_KEY)

        # Search hotels
        hotels = searcher.search_hotels(trip_prefs)

        # Format and print results
        print(format_hotel_results(hotels))

    except Exception as e:
        print(f"Error: {e}")
