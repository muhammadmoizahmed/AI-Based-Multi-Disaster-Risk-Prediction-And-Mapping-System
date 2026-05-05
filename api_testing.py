import os
import requests
import json
from dotenv import load_dotenv
from urllib.parse import quote
from datetime import datetime, timedelta

# Load API keys from .env
load_dotenv()
nasa_api_key = os.getenv('nasaapi')
firms_map_key = os.getenv('firms_map_key', '').strip()
openweather_api_key = os.getenv('open_weather_api', '').strip()

if not nasa_api_key:
    print("Error: NASA API key not found in .env file")
    exit(1)

# Pakistan's bounding box coordinates
PAKISTAN_BOUNDS = {
    'min_lat': 23.5,
    'max_lat': 37.0,
    'min_lon': 60.5,
    'max_lon': 77.0
}

# Major Pakistani cities with coordinates
PAKISTAN_CITIES = {
    'Karachi': (24.86, 67.01),
    'Lahore': (31.52, 74.36),
    'Islamabad': (33.68, 73.05),
    'Rawalpindi': (33.57, 73.05),
    'Faisalabad': (31.42, 73.08),
    'Gujranwala': (32.16, 74.19),
    'Multan': (30.16, 71.52),
    'Peshawar': (34.01, 71.58),
    'Quetta': (30.18, 67.01),
    'Hyderabad': (25.39, 68.37),
    'Sialkot': (32.49, 74.53),
    'Bahawalpur': (29.35, 71.69)
}

def is_in_pakistan(lon, lat):
    """Check if coordinates are within Pakistan's bounds"""
    return (PAKISTAN_BOUNDS['min_lon'] <= lon <= PAKISTAN_BOUNDS['max_lon'] and
            PAKISTAN_BOUNDS['min_lat'] <= lat <= PAKISTAN_BOUNDS['max_lat'])

def get_nearest_city(lon, lat):
    """Find nearest Pakistani city to given coordinates"""
    min_distance = float('inf')
    nearest_city = 'Unknown'

    for city, (city_lat, city_lon) in PAKISTAN_CITIES.items():
        distance = ((lat - city_lat) ** 2 + (lon - city_lon) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            nearest_city = city

    return nearest_city

print("=" * 60)
print("PAKISTAN DISASTER RISK DATA - NASA EONET API")
print("=" * 60)
print(f"API Key: {nasa_api_key[:10]}...")
print()

# NASA EONET API - Natural events
url = f"https://eonet.gsfc.nasa.gov/api/v3/events?api_key={nasa_api_key}&limit=50"

print(f"Fetching data from NASA EONET...")
print()

try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    all_events = data.get('events', [])

    # Filter events within Pakistan
    pakistan_events = []
    for event in all_events:
        for geom in event.get('geometry', []):
            coords = geom.get('coordinates', [])
            if len(coords) >= 2:
                lon, lat = coords[0], coords[1]
                if is_in_pakistan(lon, lat):
                    event_copy = event.copy()
                    event_copy['pakistan_coords'] = {'lon': lon, 'lat': lat}
                    event_copy['nearest_city'] = get_nearest_city(lon, lat)
                    pakistan_events.append(event_copy)
                    break

    print(f"Total global events: {len(all_events)}")
    print(f"Pakistan region events: {len(pakistan_events)}")
    print()

    if not pakistan_events:
        print("No recent disaster events found in Pakistan region.")
    else:
        print("-" * 60)
        print("PAKISTAN CITY-WISE DISASTER EVENTS:")
        print("-" * 60)

        # Group by city
        city_events = {}
        for event in pakistan_events:
            city = event['nearest_city']
            if city not in city_events:
                city_events[city] = []
            city_events[city].append(event)

        for city, events in city_events.items():
            print(f"\n{city.upper()} ({len(events)} event(s)):")
            for event in events:
                cat = event.get('categories', [{}])[0].get('title', 'N/A')
                date = event.get('geometry', [{}])[0].get('date', 'N/A')[:10]
                coords = event.get('pakistan_coords', {})
                print(f"   - {event.get('title', 'N/A')}")
                print(f"     Type: {cat} | Date: {date}")
                print(f"     Coordinates: {coords.get('lat', 'N/A'):.4f}, {coords.get('lon', 'N/A'):.4f}")
                print(f"     Status: {'Active' if not event.get('closed') else 'Closed'}")

    # Also fetch USGS Earthquake data for Pakistan
    print()
    print("=" * 60)
    print("PAKISTAN EARTHQUAKE DATA (USGS):")
    print("=" * 60)

    usgs_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    usgs_params = {
        'format': 'geojson',
        'minlatitude': PAKISTAN_BOUNDS['min_lat'],
        'maxlatitude': PAKISTAN_BOUNDS['max_lat'],
        'minlongitude': PAKISTAN_BOUNDS['min_lon'],
        'maxlongitude': PAKISTAN_BOUNDS['max_lon'],
        'starttime': '2025-01-01',
        'orderby': 'time',
        'limit': 20
    }

    eq_response = requests.get(usgs_url, params=usgs_params, timeout=30)
    eq_response.raise_for_status()
    eq_data = eq_response.json()

    earthquakes = eq_data.get('features', [])
    print(f"Total earthquakes in Pakistan region: {len(earthquakes)}")
    print()

    if earthquakes:
        # Separate current (last 48 hours) and recent (older)
        now = datetime.now()
        current_cutoff = now - timedelta(hours=48)

        current_eqs = []
        recent_eqs = []

        for eq in earthquakes:
            props = eq.get('properties', {})
            eq_time_ms = props.get('time', 0)
            eq_datetime = datetime.fromtimestamp(eq_time_ms / 1000)

            coords = eq.get('geometry', {}).get('coordinates', [0, 0])
            lon, lat = coords[0], coords[1]
            nearest_city = get_nearest_city(lon, lat)

            eq_data_dict = {
                'mag': props.get('mag', 'N/A'),
                'place': props.get('place', 'N/A'),
                'time': eq_datetime.strftime('%Y-%m-%d %H:%M'),
                'lat': lat,
                'lon': lon,
                'city': nearest_city
            }

            if eq_datetime > current_cutoff:
                current_eqs.append(eq_data_dict)
            else:
                recent_eqs.append(eq_data_dict)

        # Show CURRENT earthquakes in table format
        if current_eqs:
            print("-" * 100)
            print("CURRENT EARTHQUAKES (Last 48 Hours)")
            print("-" * 100)
            print(f"{'City':<15} | {'Magnitude':<10} | {'Location':<45} | {'Time':<20}")
            print("-" * 100)

            for eq in current_eqs:
                city = eq['city'][:14]
                mag = str(eq['mag'])[:9]
                loc = eq['place'][:44]
                time = eq['time'][:19]
                print(f"{city:<15} | {mag:<10} | {loc:<45} | {time:<20}")
            print("-" * 100)

        # Show RECENT earthquakes in table format
        if recent_eqs:
            print()
            print("-" * 100)
            print("RECENT EARTHQUAKES (Past Events)")
            print("-" * 100)
            print(f"{'City':<15} | {'Magnitude':<10} | {'Location':<45} | {'Time':<20}")
            print("-" * 100)

            for eq in recent_eqs:
                city = eq['city'][:14]
                mag = str(eq['mag'])[:9]
                loc = eq['place'][:44]
                time = eq['time'][:19]
                print(f"{city:<15} | {mag:<10} | {loc:<45} | {time:<20}")
            print("-" * 100)

    # WILDFIRE DATA
    all_wildfires = []

    # Try NASA EONET for wildfire data
    try:
        eonet_wildfire_url = f"https://eonet.gsfc.nasa.gov/api/v3/categories/wildfires?api_key={nasa_api_key}&limit=50"
        wf_response = requests.get(eonet_wildfire_url, timeout=30)
        wf_response.raise_for_status()
        wf_data = wf_response.json()

        # Filter wildfire events in Pakistan
        for event in wf_data.get('events', []):
            for geom in event.get('geometry', []):
                coords = geom.get('coordinates', [])
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                    if is_in_pakistan(lon, lat):
                        all_wildfires.append({
                            'title': event.get('title', 'N/A'),
                            'lat': lat,
                            'lon': lon,
                            'date': geom.get('date', 'N/A')[:10],
                            'status': 'Active' if not event.get('closed') else 'Closed',
                            'nearest_city': get_nearest_city(lon, lat)
                        })
                        break

        # Wildfire events collected from EONET

    except requests.exceptions.RequestException as e:
        pass  # Silent fail for wildfire fetch

    # GDACS API - Alternative wildfire sources (no key required)
    try:
        gdacs_response = requests.get("https://www.gdacs.org/xml/rss.xml", timeout=30)
        if gdacs_response.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(gdacs_response.content)
            gdacs_fires = []
            for item in root.findall('.//item'):
                title = item.find('title')
                if title is not None and ('wildfire' in title.text.lower() or 'fire' in title.text.lower()):
                    geo_lat = item.find('.//{http://www.w3.org/2003/01/geo/wgs84_pos#}lat')
                    geo_long = item.find('.//{http://www.w3.org/2003/01/geo/wgs84_pos#}long')
                    if geo_lat is not None and geo_long is not None:
                        try:
                            lat = float(geo_lat.text)
                            lon = float(geo_long.text)
                            if is_in_pakistan(lon, lat):
                                gdacs_fires.append({'title': title.text, 'lat': lat, 'lon': lon, 'source': 'GDACS'})
                        except:
                            continue
            # GDACS RSS wildfires found
            all_wildfires.extend(gdacs_fires)
    except Exception:
        pass  # Silent fail

    # Try GDACS JSON feed
    try:
        from datetime import datetime, timedelta
        today = datetime.now().strftime('%Y-%m-%d')
        last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        gdacs_json_url = f"https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?fromDate={last_week}&toDate={today}"
        gdacs_json = requests.get(gdacs_json_url, timeout=30)
        if gdacs_json.status_code == 200:
            events = gdacs_json.json()
            gdacs_json_fires = []
            for event in events.get('features', []):
                props = event.get('properties', {})
                if 'wildfire' in props.get('eventtype', '').lower() or 'fire' in props.get('eventtype', '').lower():
                    coords = event.get('geometry', {}).get('coordinates', [0, 0])
                    if len(coords) >= 2:
                        lon, lat = coords[0], coords[1]
                        if is_in_pakistan(lon, lat):
                            gdacs_json_fires.append({
                                'title': props.get('name', 'Wildfire'),
                                'lat': lat,
                                'lon': lon,
                                'date': props.get('fromdate', 'N/A')[:10],
                                'source': 'GDACS JSON'
                            })
            # GDACS JSON wildfires collected
            all_wildfires.extend(gdacs_json_fires)
    except Exception:
        pass  # Silent fail

    # Remove duplicates
    wildfires = []
    seen_coords = set()
    for wf in all_wildfires:
        coord_key = (round(wf['lat'], 2), round(wf['lon'], 2))
        if coord_key not in seen_coords:
            seen_coords.add(coord_key)
            wildfires.append(wf)

    # Separate current (active) and recent wildfires
    now = datetime.now()
    current_wf = [wf for wf in wildfires if wf.get('status') == 'Active']
    recent_wf = [wf for wf in wildfires if wf.get('status') != 'Active']

    print(f"\nTotal wildfire events in Pakistan: {len(wildfires)}")
    print(f"  - Current/Active: {len(current_wf)}")
    print(f"  - Recent/Past: {len(recent_wf)}")
    print()

    # Show CURRENT wildfires in table format
    if current_wf:
        print("-" * 110)
        print("CURRENT WILDFIRES (Active Now)")
        print("-" * 110)
        print(f"{'City':<12} | {'Title':<30} | {'Date':<12} | {'Lat':<10} | {'Lon':<10} | {'Status':<10}")
        print("-" * 110)

        for wf in current_wf[:20]:  # Limit to 20
            city = wf['nearest_city'][:11]
            title = wf['title'][:29]
            date = str(wf['date'])[:11]
            lat = f"{wf['lat']:.2f}"
            lon = f"{wf['lon']:.2f}"
            status = wf['status'][:9]
            print(f"{city:<12} | {title:<30} | {date:<12} | {lat:<10} | {lon:<10} | {status:<10}")
        print("-" * 110)

    # Show RECENT wildfires in table format
    if recent_wf:
        print()
        print("-" * 110)
        print("RECENT WILDFIRES (Past Events)")
        print("-" * 110)
        print(f"{'City':<12} | {'Title':<30} | {'Date':<12} | {'Lat':<10} | {'Lon':<10} | {'Status':<10}")
        print("-" * 110)

        for wf in recent_wf[:20]:  # Limit to 20
            city = wf['nearest_city'][:11]
            title = wf['title'][:29]
            date = str(wf['date'])[:11]
            lat = f"{wf['lat']:.2f}"
            lon = f"{wf['lon']:.2f}"
            status = wf['status'][:9]
            print(f"{city:<12} | {title:<30} | {date:<12} | {lat:<10} | {lon:<10} | {status:<10}")
        print("-" * 110)

    if not wildfires:
        print("No wildfire data found.")
        print("(No active or recent wildfires detected in Pakistan)")

    # FLOOD DATA
    try:
        flood_url = f"https://eonet.gsfc.nasa.gov/api/v3/categories/floods?api_key={nasa_api_key}&limit=50"
        flood_response = requests.get(flood_url, timeout=30)
        flood_response.raise_for_status()
        flood_data = flood_response.json()

        # Filter flood events in Pakistan
        pakistan_floods = []
        for event in flood_data.get('events', []):
            for geom in event.get('geometry', []):
                coords = geom.get('coordinates', [])
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                    if is_in_pakistan(lon, lat):
                        event_copy = event.copy()
                        event_copy['pakistan_coords'] = {'lon': lon, 'lat': lat}
                        event_copy['nearest_city'] = get_nearest_city(lon, lat)
                        pakistan_floods.append(event_copy)
                        break

        # Separate current (active) and recent floods
        current_floods = [f for f in pakistan_floods if not f.get('closed')]
        recent_floods = [f for f in pakistan_floods if f.get('closed')]

        print(f"Total flood events in Pakistan: {len(pakistan_floods)}")
        print(f"  - Current/Active: {len(current_floods)}")
        print(f"  - Recent/Closed: {len(recent_floods)}")
        print()

        # Show CURRENT floods in table format
        if current_floods:
            print("-" * 110)
            print("CURRENT FLOODS (Active Now)")
            print("-" * 110)
            print(f"{'City':<12} | {'Title':<35} | {'Date':<12} | {'Lat':<10} | {'Lon':<10} | {'Status':<10}")
            print("-" * 110)

            for event in current_floods[:20]:
                city = event['nearest_city'][:11]
                title = event.get('title', 'N/A')[:34]
                date = event.get('geometry', [{}])[0].get('date', 'N/A')[:11]
                coords = event.get('pakistan_coords', {})
                lat = f"{coords.get('lat', 0):.2f}"
                lon = f"{coords.get('lon', 0):.2f}"
                print(f"{city:<12} | {title:<35} | {date:<12} | {lat:<10} | {lon:<10} | Active    ")
            print("-" * 110)

        # Show RECENT floods in table format
        if recent_floods:
            print()
            print("-" * 110)
            print("RECENT FLOODS (Past Events)")
            print("-" * 110)
            print(f"{'City':<12} | {'Title':<35} | {'Date':<12} | {'Lat':<10} | {'Lon':<10} | {'Status':<10}")
            print("-" * 110)

            for event in recent_floods[:20]:
                city = event['nearest_city'][:11]
                title = event.get('title', 'N/A')[:34]
                date = event.get('geometry', [{}])[0].get('date', 'N/A')[:11]
                coords = event.get('pakistan_coords', {})
                lat = f"{coords.get('lat', 0):.2f}"
                lon = f"{coords.get('lon', 0):.2f}"
                print(f"{city:<12} | {title:<35} | {date:<12} | {lat:<10} | {lon:<10} | Closed    ")
            print("-" * 110)

        if not pakistan_floods:
            print("No flood events found.")
            print("(No active or recent floods detected in Pakistan)")

    except requests.exceptions.RequestException:
        pass  # Silent fail for flood fetch

    # NASA POWER API - Rainfall/Precipitation Data
    print()
    print("=" * 60)
    print("PAKISTAN RAINFALL DATA (NASA POWER API):")
    print("=" * 60)

    # Get rainfall data for major Pakistan cities
    rainfall_data = []

    for city, (city_lat, city_lon) in PAKISTAN_CITIES.items():
        try:
            # NASA POWER API for precipitation
            power_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
            power_params = {
                'parameters': 'PRECTOTCORR',  # Precipitation corrected
                'community': 'RE',
                'longitude': city_lon,
                'latitude': city_lat,
                'start': (datetime.now() - timedelta(days=7)).strftime('%Y%m%d'),
                'end': datetime.now().strftime('%Y%m%d'),
                'format': 'JSON'
            }

            power_response = requests.get(power_url, params=power_params, timeout=30)
            if power_response.status_code == 200:
                power_data = power_response.json()
                properties = power_data.get('properties', {})
                parameter = properties.get('parameter', {})
                prectotcorr = parameter.get('PRECTOTCORR', {})

                if prectotcorr:
                    # Filter out -999 (missing data indicator)
                    valid_rainfall = [v for v in prectotcorr.values() if v > -900]

                    if valid_rainfall:
                        # Calculate total rainfall in last 7 days (in mm)
                        total_rainfall = sum(valid_rainfall)
                        avg_daily = total_rainfall / len(valid_rainfall)

                        # Get today's rainfall
                        today_key = datetime.now().strftime('%Y%m%d')
                        today_value = prectotcorr.get(today_key, 0)
                        today_rainfall = today_value if today_value > -900 else 0

                        rainfall_data.append({
                            'city': city,
                            'today_mm': round(today_rainfall, 2),
                            'weekly_total_mm': round(total_rainfall, 2),
                            'avg_daily_mm': round(avg_daily, 2),
                            'days_with_data': len(valid_rainfall)
                        })
        except Exception as e:
            continue

    if rainfall_data:
        print(f"\nRainfall data for {len(rainfall_data)} cities (Last 7 days):")
        print()

        # Sort by today's rainfall (highest first)
        rainfall_data.sort(key=lambda x: x['today_mm'], reverse=True)

        # Show rainfall in table format
        print()
        print("-" * 90)
        print("RAINFALL DATA (Last 7 Days)")
        print("-" * 90)
        print(f"{'City':<15} | {'Today (mm)':<12} | {'Weekly Total (mm)':<20} | {'Daily Avg (mm)':<15} | {'Status':<10}")
        print("-" * 90)

        for data in rainfall_data:
            city = data['city'][:14]
            today = f"{data['today_mm']:.1f}"
            weekly = f"{data['weekly_total_mm']:.1f}"
            avg = f"{data['avg_daily_mm']:.1f}"
            status = "Raining" if data['today_mm'] > 0 else "Dry"
            print(f"{city:<15} | {today:<12} | {weekly:<20} | {avg:<15} | {status:<10}")
        print("-" * 90)
    else:
        print("No rainfall data available from NASA POWER API.")

    # OpenWeather API - Flood, Cyclone, Heat Wave Data
    print()
    print("=" * 60)
    print("PAKISTAN WEATHER HAZARDS (OpenWeather API):")
    print("=" * 60)

    if not openweather_api_key:
        print("Note: OpenWeather API key not found in .env file")
        print("Add: open_weather_api=YOUR_API_KEY")
    else:
        flood_alerts = []
        cyclone_alerts = []
        heatwave_alerts = []

        for city, (city_lat, city_lon) in PAKISTAN_CITIES.items():
            try:
                # Get current weather and 5-day forecast
                weather_url = "https://api.openweathermap.org/data/2.5/forecast"
                weather_params = {
                    'lat': city_lat,
                    'lon': city_lon,
                    'appid': openweather_api_key,
                    'units': 'metric'
                }

                weather_response = requests.get(weather_url, params=weather_params, timeout=30)
                if weather_response.status_code == 200:
                    weather_data = weather_response.json()
                    forecast_list = weather_data.get('list', [])

                    if forecast_list:
                        # Check for flood conditions (heavy rain > 50mm in 3 hours)
                        heavy_rain_days = []
                        for forecast in forecast_list[:5]:  # Next 15 hours
                            rain_data = forecast.get('rain', {})
                            rain_3h = rain_data.get('3h', 0)
                            if rain_3h > 20:  # More than 20mm in 3 hours
                                heavy_rain_days.append({
                                    'time': forecast.get('dt_txt', 'N/A'),
                                    'rain_mm': round(rain_3h, 2),
                                    'description': forecast.get('weather', [{}])[0].get('description', 'N/A')
                                })

                        if heavy_rain_days:
                            flood_alerts.append({
                                'city': city,
                                'alerts': heavy_rain_days
                            })

                        # Check for cyclone conditions (wind speed > 90 km/h)
                        high_wind_days = []
                        for forecast in forecast_list:
                            wind_speed = forecast.get('wind', {}).get('speed', 0)
                            if wind_speed > 25:  # More than 25 m/s (90 km/h)
                                high_wind_days.append({
                                    'time': forecast.get('dt_txt', 'N/A'),
                                    'wind_ms': wind_speed,
                                    'wind_kmh': round(wind_speed * 3.6, 1)
                                })

                        if high_wind_days:
                            cyclone_alerts.append({
                                'city': city,
                                'alerts': high_wind_days
                            })

                        # Check for heat wave conditions (temp > 40°C)
                        extreme_heat_days = []
                        for forecast in forecast_list:
                            temp = forecast.get('main', {}).get('temp', 0)
                            if temp > 40:  # More than 40°C
                                extreme_heat_days.append({
                                    'time': forecast.get('dt_txt', 'N/A'),
                                    'temp_c': round(temp, 1)
                                })

                        if extreme_heat_days:
                            heatwave_alerts.append({
                                'city': city,
                                'alerts': extreme_heat_days
                            })

            except Exception as e:
                continue

        # Display Flood Alerts in table format
        print(f"\nFLOOD ALERTS (Heavy Rain >20mm/3h)")
        print("-" * 80)
        if flood_alerts:
            print(f"{'City':<15} | {'Date/Time':<20} | {'Rain (mm/3h)':<15} | {'Condition':<25}")
            print("-" * 80)
            for alert in flood_alerts:
                city = alert['city'][:14]
                for item in alert['alerts']:
                    time_str = str(item['time'])[:19]
                    rain_str = f"{item['rain_mm']}"
                    desc_str = item['description'][:24]
                    print(f"{city:<15} | {time_str:<20} | {rain_str:<15} | {desc_str:<25}")
            print("-" * 80)
        else:
            print("No flood alerts currently.")

        # Display Cyclone Alerts in table format
        print(f"\nCYCLONE/STORM ALERTS (Wind >90 km/h)")
        print("-" * 60)
        if cyclone_alerts:
            print(f"{'City':<15} | {'Date/Time':<20} | {'Wind Speed (km/h)':<20}")
            print("-" * 60)
            for alert in cyclone_alerts:
                city = alert['city'][:14]
                for item in alert['alerts']:
                    time_str = str(item['time'])[:19]
                    wind_str = f"{item['wind_kmh']}"
                    print(f"{city:<15} | {time_str:<20} | {wind_str:<20}")
            print("-" * 60)
        else:
            print("No cyclone/storm alerts currently.")

        # Display Heat Wave Alerts in table format
        print(f"\nHEAT WAVE ALERTS (Temp >40C)")
        print("-" * 70)
        if heatwave_alerts:
            print(f"{'City':<15} | {'Date/Time':<20} | {'Temperature':<15}")
            print("-" * 70)
            for alert in heatwave_alerts:
                city = alert['city'][:14]
                for item in alert['alerts']:
                    time_str = str(item['time'])[:19]
                    temp_str = f"{item['temp_c']}C"
                    print(f"{city:<15} | {time_str:<20} | {temp_str:<15}")
            print("-" * 70)
        else:
            print("No heat wave alerts currently.")

    # NOAA Tsunami API
    print()
    print("=" * 60)
    print("PAKISTAN TSUNAMI DATA (NOAA NGDC):")
    print("=" * 60)

    try:
        # NOAA NGDC Tsunami Events API
        tsunami_url = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/tsunamis/events"

        # Search for tsunamis near Pakistan (Arabian Sea and Indian Ocean coastal areas)
        tsunami_params = {
            'minLatitude': 23.0,
            'maxLatitude': 25.5,
            'minLongitude': 61.0,
            'maxLongitude': 68.0,  # Arabian Sea region near Pakistan coast
        }

        tsunami_response = requests.get(tsunami_url, params=tsunami_params, timeout=30)
        if tsunami_response.status_code == 200:
            tsunami_data = tsunami_response.json()
            items = tsunami_data.get('items', [])

            # Filter for Pakistan region events
            pakistan_tsunamis = []
            for event in items:
                lat = event.get('latitude', 0)
                lon = event.get('longitude', 0)

                # Check if near Pakistan coast
                if is_in_pakistan(lon, lat) or (23 <= lat <= 25.5 and 61 <= lon <= 68):
                    year = event.get('year', 'N/A')
                    month = event.get('month', '')
                    day = event.get('day', '')
                    date_str = f"{year}-{month:02d}-{day:02d}" if month and day else str(year)

                    pakistan_tsunamis.append({
                        'year': year,
                        'date': date_str,
                        'location': event.get('location', 'Unknown'),
                        'country': event.get('country', 'N/A'),
                        'cause': event.get('cause', 'Unknown'),
                        'maxWaterHeight': event.get('maxWaterHeight', 'N/A'),
                        'deaths': event.get('deaths', 0) or 0,
                        'lat': lat,
                        'lon': lon,
                        'nearest_city': get_nearest_city(lon, lat)
                    })

            # Separate current (recent) and historical
            current_tsunamis = [t for t in pakistan_tsunamis if t['year'] and int(t['year']) >= 2000]
            historical_tsunamis = [t for t in pakistan_tsunamis if t['year'] and int(t['year']) < 2000]

            print(f"\nTotal tsunami events near Pakistan: {len(pakistan_tsunamis)}")
            print(f"  - Current/Recent (2000+): {len(current_tsunamis)}")
            print(f"  - Historical (before 2000): {len(historical_tsunamis)}")
            print()

            # Show CURRENT/RECENT tsunamis in table format
            if current_tsunamis:
                print("-" * 120)
                print("CURRENT/RECENT TSUNAMIS (2000 onwards)")
                print("-" * 120)
                print(f"{'City':<12} | {'Date':<12} | {'Location':<25} | {'Country':<12} | {'Cause':<15} | {'Height (m)':<10} | {'Deaths':<8}")
                print("-" * 120)

                for tsu in current_tsunamis:
                    city = tsu['nearest_city'][:11]
                    date = str(tsu['date'])[:11]
                    loc = tsu['location'][:24]
                    country = str(tsu['country'])[:11]
                    cause = str(tsu['cause'])[:14]
                    height = str(tsu['maxWaterHeight'])[:9]
                    deaths = str(tsu['deaths'])[:7]
                    print(f"{city:<12} | {date:<12} | {loc:<25} | {country:<12} | {cause:<15} | {height:<10} | {deaths:<8}")
                print("-" * 120)

            # Show HISTORICAL tsunamis in table format
            if historical_tsunamis:
                print()
                print("-" * 100)
                print("HISTORICAL TSUNAMIS (Before 2000)")
                print("-" * 100)
                print(f"{'City':<12} | {'Date':<12} | {'Location':<25} | {'Cause':<15} | {'Height (m)':<10}")
                print("-" * 100)

                for tsu in historical_tsunamis[:10]:  # Limit to 10 historical
                    city = tsu['nearest_city'][:11]
                    date = str(tsu['date'])[:11]
                    loc = tsu['location'][:24]
                    cause = str(tsu['cause'])[:14]
                    height = str(tsu['maxWaterHeight'])[:9]
                    print(f"{city:<12} | {date:<12} | {loc:<25} | {cause:<15} | {height:<10}")
                print("-" * 100)

            if not pakistan_tsunamis:
                print("No tsunami events found in Pakistan region.")
        else:
            print("Unable to fetch tsunami data from NOAA.")

    except Exception as e:
        pass  # Silent fail for tsunami fetch

    print()
    print("=" * 60)
    print("FINAL SUMMARY:")
    print("=" * 60)
    print(f"Earthquakes in Pakistan: {len(earthquakes)}")
    print(f"Wildfire Hotspots in Pakistan: {len(wildfires) if 'wildfires' in locals() else 'N/A'}")
    print(f"Flood Events in Pakistan: {len(pakistan_floods) if 'pakistan_floods' in locals() else 'N/A'}")
    print(f"Tsunami Events near Pakistan: {len(pakistan_tsunamis) if 'pakistan_tsunamis' in locals() else 'N/A'}")
    print(f"Cities with Rainfall Data: {len(rainfall_data) if 'rainfall_data' in locals() else 'N/A'}")
    if openweather_api_key:
        print(f"OpenWeather Flood Alerts: {len(flood_alerts) if 'flood_alerts' in locals() else 'N/A'}")
        print(f"OpenWeather Cyclone Alerts: {len(cyclone_alerts) if 'cyclone_alerts' in locals() else 'N/A'}")
        print(f"OpenWeather Heat Wave Alerts: {len(heatwave_alerts) if 'heatwave_alerts' in locals() else 'N/A'}")

except requests.exceptions.RequestException as e:
    print(f"Error fetching data: {e}")
