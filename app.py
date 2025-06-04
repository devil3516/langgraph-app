import streamlit as st
from datetime import datetime
import os
from dotenv import load_dotenv
from tools.parse_trip_prefs import TripPreferences, parse_trip_preferences
from tools.search_hotels import HotelSearcher
from tools.search_attractions import AttractionSearcher
from tools.build_itinerary import ItineraryBuilder
from tools.export_itinerary import ItineraryExporter
from utils.formatter import ItineraryFormatter
from langchain_groq import ChatGroq
import plotly.express as px

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

def check_api_keys():
    """Check if required API keys are set"""
    missing_keys = []
    if not GROQ_API_KEY:
        missing_keys.append("GROQ_API_KEY")
    if not TAVILY_API_KEY:
        missing_keys.append("TAVILY_API_KEY")
    return missing_keys

def initialize_session_state():
    """Initialize session state variables"""
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 'preferences'
    if 'trip_prefs' not in st.session_state:
        st.session_state.trip_prefs = None
    if 'hotels' not in st.session_state:
        st.session_state.hotels = None
    if 'attractions' not in st.session_state:
        st.session_state.attractions = None
    if 'itinerary' not in st.session_state:
        st.session_state.itinerary = None

def display_api_key_instructions():
    """Display instructions for setting up API keys"""
    st.error("Missing API Keys")
    st.write("Please set up your API keys in the `.env` file:")
    st.code("""
# Create a .env file in the project root with:
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
    """)
    st.write("You can obtain API keys from:")
    st.write("1. Groq API: https://console.groq.com/")
    st.write("2. Tavily API: https://tavily.com/")
    
    if st.button("I've set up my API keys"):
        st.rerun()

def get_trip_preferences():
    """Get trip preferences from user input"""
    st.title("Travel Itinerary Planner")
    st.write("Let's plan your perfect trip! Please provide your travel preferences.")
    
    with st.form("trip_preferences"):
        # Destination
        destination = st.text_input("Where would you like to go?")
        
        # Dates
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", min_value=datetime.now().date())
        with col2:
            end_date = st.date_input("End Date", min_value=start_date)
        
        # Budget
        budget = st.number_input("Total Budget ($)", min_value=0.0, step=100.0)
        
        # Travel Style
        travel_style = st.selectbox(
            "Travel Style",
            ["budget", "moderate", "luxury"]
        )
        
        # Interests
        interests = st.multiselect(
            "Interests",
            ["culture", "food", "nature", "adventure", "shopping", "history", "art", "relaxation"],
            default=["culture", "food"]
        )
        
        # Accommodation Preference
        accommodation = st.selectbox(
            "Accommodation Preference",
            ["hotel", "hostel", "apartment", "resort"]
        )
        
        # Transportation Preference
        transportation = st.selectbox(
            "Transportation Preference",
            ["public", "private", "mixed"]
        )
        
        # Optional Preferences
        with st.expander("Additional Preferences"):
            dietary = st.multiselect(
                "Dietary Restrictions",
                ["none", "vegetarian", "vegan", "gluten-free", "halal", "kosher"]
            )
            special_req = st.text_area("Special Requirements or Notes")
        
        submitted = st.form_submit_button("Plan My Trip!")
        
        if submitted:
            if not destination:
                st.error("Please enter a destination")
                return
            
            preferences = {
                "destination": destination,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "budget": float(budget),
                "travel_style": travel_style,
                "interests": interests,
                "accommodation_preference": accommodation,
                "transportation_preference": transportation,
                "dietary_restrictions": dietary if dietary else None,
                "special_requirements": special_req if special_req else None
            }
            
            # Parse preferences
            state = {"user_input": preferences}
            parsed_state = parse_trip_preferences(state)
            
            if "error" in parsed_state:
                st.error(parsed_state["error"])
                return
            
            st.session_state.trip_prefs = TripPreferences(
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
            
            st.session_state.current_step = 'searching'
            st.rerun()

def search_hotels_and_attractions():
    """Search for hotels and attractions based on preferences"""
    st.title("Searching for Options...")
    
    with st.spinner("Searching for hotels and attractions..."):
        # Initialize searchers
        hotel_searcher = HotelSearcher(TAVILY_API_KEY)
        attraction_searcher = AttractionSearcher(TAVILY_API_KEY)
        
        # Search for hotels
        hotels = hotel_searcher.search_hotels(st.session_state.trip_prefs)
        st.session_state.hotels = hotels
        
        # Search for attractions
        attractions = attraction_searcher.search_attractions(st.session_state.trip_prefs)
        st.session_state.attractions = attractions
    
    st.session_state.current_step = 'selecting'
    st.rerun()

def select_hotel_and_attractions():
    """Let user select hotel and attractions"""
    st.title("Select Your Options")
    
    # Hotel selection
    st.subheader("Select a Hotel")
    if st.session_state.hotels:
        hotel_options = {f"{h.name} - ${h.price_per_night:.2f}/night": h for h in st.session_state.hotels}
        selected_hotel = st.selectbox("Choose your hotel", list(hotel_options.keys()))
        selected_hotel_obj = hotel_options[selected_hotel]
        
        # Display hotel details
        with st.expander("Hotel Details"):
            st.write(f"**Address:** {selected_hotel_obj.address}")
            st.write(f"**Rating:** {selected_hotel_obj.rating}/5.0")
            st.write(f"**Amenities:** {', '.join(selected_hotel_obj.amenities)}")
            if selected_hotel_obj.description:
                st.write(f"**Description:** {selected_hotel_obj.description}")
    else:
        st.warning("No hotels found matching your criteria")
        selected_hotel_obj = None
    
    # Attraction selection
    st.subheader("Select Attractions")
    if st.session_state.attractions:
        # Group attractions by category
        categories = {}
        for attraction in st.session_state.attractions:
            if attraction.category not in categories:
                categories[attraction.category] = []
            categories[attraction.category].append(attraction)
        
        selected_attractions = []
        for category, attractions in categories.items():
            st.write(f"**{category.title()}**")
            for attraction in attractions:
                if st.checkbox(
                    f"{attraction.name} - {attraction.visit_duration or 'Duration not specified'}",
                    key=f"attraction_{attraction.name}"
                ):
                    selected_attractions.append(attraction)
    else:
        st.warning("No attractions found matching your criteria")
        selected_attractions = []
    
    if st.button("Generate Itinerary"):
        if not selected_attractions:
            st.error("Please select at least one attraction")
            return
        
        st.session_state.current_step = 'generating'
        st.rerun()

def generate_itinerary():
    """Generate the final itinerary"""
    st.title("Generating Your Itinerary...")
    
    with st.spinner("Creating your perfect itinerary..."):
        # Initialize LLM client and builder
        llm_client = ChatGroq(api_key=GROQ_API_KEY)
        builder = ItineraryBuilder(llm_client)
        
        # Build itinerary
        itinerary = builder.build_itinerary(
            st.session_state.trip_prefs,
            st.session_state.hotels[0] if st.session_state.hotels else None,
            st.session_state.attractions
        )
        
        st.session_state.itinerary = itinerary
    
    st.session_state.current_step = 'displaying'
    st.rerun()

def display_itinerary():
    """Display the final itinerary"""
    if st.session_state.itinerary:
        # Initialize formatter
        formatter = ItineraryFormatter()
        formatted_data = formatter.format_for_display(st.session_state.itinerary)
        
        # Display overview
        st.title(f"Your Trip to {formatted_data['overview']['destination']}")
        
        # Overview section
        st.header("Trip Overview")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Duration", f"{formatted_data['overview']['duration']} days")
        with col2:
            st.metric("Total Cost", f"${formatted_data['overview']['total_cost']:.2f}")
        with col3:
            st.metric("Travel Style", formatted_data['overview']['travel_style'].title())
        
        st.write("**Interests:**", ", ".join(formatted_data['overview']['interests']))
        st.write("**Summary:**", formatted_data['overview']['summary'])
        
        # Hotel information
        if formatted_data['overview']['hotel']:
            st.header("Accommodation")
            hotel = formatted_data['overview']['hotel']
            st.write(f"**{hotel['name']}**")
            if hotel['address']:
                st.write(f"Address: {hotel['address']}")
            if hotel['rating']:
                st.write(f"Rating: {hotel['rating']}/5.0")
            if hotel['price_per_night']:
                st.write(f"Price per night: ${hotel['price_per_night']:.2f}")
        
        # Daily plans
        st.header("Daily Itinerary")
        for day in formatted_data['daily_plans']:
            with st.expander(f"{day['day_name']}, {day['date']} - ${day['total_cost']:.2f}"):
                for activity in day['activities']:
                    st.subheader(f"{activity['start_time']} - {activity['end_time']}: {activity['name']}")
                    st.write(f"**Location:** {activity['location']}")
                    st.write(f"**Category:** {activity['category']}")
                    if activity['cost']:
                        st.write(f"**Cost:** ${activity['cost']:.2f}")
                    if activity['description']:
                        st.write(activity['description'])
                    if activity['notes']:
                        st.write(f"*{activity['notes']}*")
                if day['notes']:
                    st.write(f"**Day Notes:** {day['notes']}")
        
        # Budget analysis
        st.header("Budget Analysis")
        budget_data = formatted_data['budget_analysis']
        
        # Category costs pie chart
        if budget_data['category_costs']:
            st.subheader("Costs by Category")
            categories = list(budget_data['category_costs'].keys())
            costs = list(budget_data['category_costs'].values())
            fig = px.pie(values=costs, names=categories, title="Cost Distribution by Category")
            st.plotly_chart(fig)
        
        # Daily costs line chart
        st.subheader("Daily Costs")
        daily_dates = [day['date'] for day in budget_data['daily_costs']]
        daily_costs = [day['cost'] for day in budget_data['daily_costs']]
        fig = px.line(x=daily_dates, y=daily_costs, title="Cost Trend Over Days")
        st.plotly_chart(fig)
        
        # Export options
        st.sidebar.title("Export Options")
        if st.sidebar.button("Export as PDF"):
            exporter = ItineraryExporter()
            try:
                pdf_path = exporter.export_pdf(st.session_state.itinerary)
                st.sidebar.success(f"PDF exported successfully: {pdf_path}")
            except Exception as e:
                st.sidebar.error(f"Failed to export PDF: {str(e)}")
        
        if st.sidebar.button("Export as JSON"):
            exporter = ItineraryExporter()
            try:
                json_path = exporter.export_json(st.session_state.itinerary)
                st.sidebar.success(f"JSON exported successfully: {json_path}")
            except Exception as e:
                st.sidebar.error(f"Failed to export JSON: {str(e)}")
    else:
        st.error("No itinerary available. Please generate an itinerary first.")

def main():
    """Main application function"""
    try:
        # Check for required API keys
        missing_keys = check_api_keys()
        if missing_keys:
            display_api_key_instructions()
            return
        
        initialize_session_state()
        
        # Navigation
        if st.session_state.current_step == 'preferences':
            get_trip_preferences()
        elif st.session_state.current_step == 'searching':
            search_hotels_and_attractions()
        elif st.session_state.current_step == 'selecting':
            select_hotel_and_attractions()
        elif st.session_state.current_step == 'generating':
            generate_itinerary()
        elif st.session_state.current_step == 'displaying':
            display_itinerary()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        if st.button("Start Over"):
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()
