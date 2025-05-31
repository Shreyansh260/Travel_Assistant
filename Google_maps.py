# Copyright (c) 2025 Shriyansh Singh Rathore
# Licensed under the MIT License

import googlemaps
from datetime import datetime
import re

API_KEY = 'your_google_maps_api_key_here'  # Replace with your actual key
gmaps = googlemaps.Client(key=API_KEY)

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def get_directions(origin, destination, mode, departure_choice):
    if departure_choice == "now":
        departure_time = datetime.now()
    else:
        try:
            date_input = input("Enter departure date (YYYY-MM-DD): ")
            time_input = input("Enter departure time (HH:MM in 24-hour format): ")
            departure_time = datetime.strptime(f"{date_input} {time_input}", "%Y-%m-%d %H:%M")
        except ValueError:
            print("Invalid date/time format. Using current time instead.")
            departure_time = datetime.now()

    directions_result = gmaps.directions(
        origin,
        destination,
        mode=mode,
        departure_time=departure_time,
        traffic_model='best_guess' if mode == 'driving' else None,
        alternatives=False
    )

    if not directions_result:
        print("No route found.")
        return

    leg = directions_result[0]['legs'][0]

    print(f"\n🚦 Route from {origin} to {destination} ({mode}):")
    print(f"Estimated time without traffic: {leg['duration']['text']}")
    if 'duration_in_traffic' in leg:
        print(f"Estimated time *with traffic* at selected time: {leg['duration_in_traffic']['text']}")

    print("\n📍 Step-by-step directions:\n")
    for i, step in enumerate(leg['steps'], 1):
        instruction = remove_html_tags(step['html_instructions'])
        distance = step['distance']['text']
        duration = step['duration']['text']
        print(f"{i}. {instruction} ({distance}, {duration})")

def main():
    print("🚗 Terminal Google Maps with Live/Planned Traffic")
    origin = input("Enter starting location: ")
    destination = input("Enter destination: ")
    mode = input("Travel mode (driving/walking/bicycling/transit): ").lower()
    if mode not in ['driving', 'walking', 'bicycling', 'transit']:
        mode = 'driving'

    departure_choice = input("Depart now or later? (now/later): ").lower()
    if departure_choice not in ["now", "later"]:
        departure_choice = "now"

    get_directions(origin, destination, mode, departure_choice)

if __name__ == '__main__':
    main()
