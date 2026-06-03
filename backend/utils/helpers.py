"""
Helper functions and data for DisasterGuard weather module
"""

# Major cities in Pakistan with coordinates
PAKISTAN_CITIES = [
    {"name": "Karachi", "province": "Sindh", "lat": 24.8607, "lng": 67.0011},
    {"name": "Lahore", "province": "Punjab", "lat": 31.5497, "lng": 74.3436},
    {"name": "Islamabad", "province": "ICT", "lat": 33.6844, "lng": 73.0479},
    {"name": "Rawalpindi", "province": "Punjab", "lat": 33.5651, "lng": 73.0169},
    {"name": "Peshawar", "province": "Khyber Pakhtunkhwa", "lat": 34.0151, "lng": 71.5249},
    {"name": "Quetta", "province": "Balochistan", "lat": 30.1798, "lng": 66.9750},
    {"name": "Multan", "province": "Punjab", "lat": 30.1979, "lng": 71.4725},
    {"name": "Faisalabad", "province": "Punjab", "lat": 31.4180, "lng": 73.0791},
    {"name": "Hyderabad", "province": "Sindh", "lat": 25.3792, "lng": 68.3667},
    {"name": "Sukkur", "province": "Sindh", "lat": 27.7052, "lng": 68.8574},
    {"name": "Gujranwala", "province": "Punjab", "lat": 32.1877, "lng": 74.1945},
    {"name": "Sialkot", "province": "Punjab", "lat": 32.4946, "lng": 74.5389},
    {"name": "Abbottabad", "province": "Khyber Pakhtunkhwa", "lat": 34.1468, "lng": 73.2146},
    {"name": "Gilgit", "province": "Gilgit-Baltistan", "lat": 35.9200, "lng": 74.4700},
    {"name": "Muzaffarabad", "province": "Azad Kashmir", "lat": 34.3700, "lng": 73.4700},
    {"name": "Bahawalpur", "province": "Punjab", "lat": 29.3900, "lng": 71.6700},
    {"name": "Larkana", "province": "Sindh", "lat": 27.5500, "lng": 68.9000},
    {"name": "Rahim Yar Khan", "province": "Punjab", "lat": 28.4200, "lng": 70.3000},
    {"name": "Gwadar", "province": "Balochistan", "lat": 25.1300, "lng": 62.3200},
    {"name": "Mardan", "province": "Khyber Pakhtunkhwa", "lat": 34.2000, "lng": 72.0500},
    {"name": "Dera Ismail Khan", "province": "Khyber Pakhtunkhwa", "lat": 31.8333, "lng": 70.9000},
    {"name": "Kohat", "province": "Khyber Pakhtunkhwa", "lat": 33.5900, "lng": 71.5400},
    {"name": "Mingora", "province": "Khyber Pakhtunkhwa", "lat": 34.7795, "lng": 72.3639},
    {"name": "Nawabshah", "province": "Sindh", "lat": 26.2399, "lng": 68.4030},
    {"name": "Jacobabad", "province": "Sindh", "lat": 28.2800, "lng": 68.4400},
    {"name": "Sahiwal", "province": "Punjab", "lat": 30.6700, "lng": 73.1000},
    {"name": "Okara", "province": "Punjab", "lat": 30.8100, "lng": 73.4500},
    {"name": "Kasur", "province": "Punjab", "lat": 31.1200, "lng": 74.4500},
    {"name": "Sheikhupura", "province": "Punjab", "lat": 31.7100, "lng": 73.9800},
    {"name": "Gujrat", "province": "Punjab", "lat": 32.5800, "lng": 74.0700},
    {"name": "Jhelum", "province": "Punjab", "lat": 32.9300, "lng": 73.7300},
    {"name": "Sargodha", "province": "Punjab", "lat": 32.0836, "lng": 72.6711},
    {"name": "Mianwali", "province": "Punjab", "lat": 32.5800, "lng": 71.5400},
    {"name": "Bhakkar", "province": "Punjab", "lat": 31.6200, "lng": 71.0600},
    {"name": "Khanewal", "province": "Punjab", "lat": 30.3000, "lng": 71.9300},
    {"name": "Vehari", "province": "Punjab", "lat": 30.0400, "lng": 72.3500},
    {"name": "Dera Ghazi Khan", "province": "Punjab", "lat": 30.0500, "lng": 70.6300},
    {"name": "Layyah", "province": "Punjab", "lat": 30.9600, "lng": 70.9400},
    {"name": "Muzaffargarh", "province": "Punjab", "lat": 30.0700, "lng": 71.1900},
    {"name": "Rajanpur", "province": "Punjab", "lat": 29.1000, "lng": 70.3200},
    {"name": "Lodhran", "province": "Punjab", "lat": 29.5400, "lng": 71.6300},
    {"name": "Khushab", "province": "Punjab", "lat": 32.2900, "lng": 72.3500},
    {"name": "Chiniot", "province": "Punjab", "lat": 31.7200, "lng": 72.9800},
    {"name": "Jhang", "province": "Punjab", "lat": 31.2800, "lng": 72.3200},
    {"name": "Toba Tek Singh", "province": "Punjab", "lat": 30.9700, "lng": 72.4800},
    {"name": "Pakpattan", "province": "Punjab", "lat": 30.3400, "lng": 73.3900},
    {"name": "Bahawalnagar", "province": "Punjab", "lat": 29.9900, "lng": 73.2500},
    {"name": "Narowal", "province": "Punjab", "lat": 32.1000, "lng": 74.8800},
    {"name": "Hafizabad", "province": "Punjab", "lat": 32.0700, "lng": 73.6800},
    {"name": "Mandi Bahauddin", "province": "Punjab", "lat": 32.5800, "lng": 73.5000},
    {"name": "Gujar Khan", "province": "Punjab", "lat": 33.2600, "lng": 73.3100},
    {"name": "Chakwal", "province": "Punjab", "lat": 32.9300, "lng": 72.8600},
    {"name": "Talagang", "province": "Punjab", "lat": 32.9200, "lng": 72.4200},
    {"name": "Attock", "province": "Punjab", "lat": 33.7700, "lng": 72.3600},
    {"name": "Taxila", "province": "Punjab", "lat": 33.7500, "lng": 72.8100},
    {"name": "Wah Cantonment", "province": "Punjab", "lat": 33.7700, "lng": 72.7100},
    {"name": "Hasan Abdal", "province": "Punjab", "lat": 33.8000, "lng": 72.6900},
    {"name": "Swabi", "province": "Khyber Pakhtunkhwa", "lat": 34.1667, "lng": 72.4667},
    {"name": "Bannu", "province": "Khyber Pakhtunkhwa", "lat": 32.7333, "lng": 70.7833},
    {"name": "Charsadda", "province": "Khyber Pakhtunkhwa", "lat": 34.1500, "lng": 71.7500},
    {"name": "Nowshera", "province": "Khyber Pakhtunkhwa", "lat": 34.0167, "lng": 71.9833},
    {"name": "Haripur", "province": "Khyber Pakhtunkhwa", "lat": 34.0833, "lng": 72.9333},
    {"name": "Mansehra", "province": "Khyber Pakhtunkhwa", "lat": 34.3333, "lng": 73.2000},
    {"name": "Chitral", "province": "Khyber Pakhtunkhwa", "lat": 35.8500, "lng": 71.7833},
    {"name": "Dera Bugti", "province": "Balochistan", "lat": 29.0300, "lng": 69.1700},
    {"name": "Sibi", "province": "Balochistan", "lat": 29.5500, "lng": 67.8800},
    {"name": "Loralai", "province": "Balochistan", "lat": 30.3700, "lng": 68.5900},
    {"name": "Kalat", "province": "Balochistan", "lat": 29.8900, "lng": 66.5900},
    {"name": "Khuzdar", "province": "Balochistan", "lat": 27.8200, "lng": 66.6100},
    {"name": "Turbat", "province": "Balochistan", "lat": 26.0000, "lng": 63.0500},
    {"name": "Panjgur", "province": "Balochistan", "lat": 26.9700, "lng": 64.0800},
    {"name": "Pasni", "province": "Balochistan", "lat": 25.2700, "lng": 63.5400},
    {"name": "Ormara", "province": "Balochistan", "lat": 25.2200, "lng": 64.5800},
    {"name": "Jiwani", "province": "Balochistan", "lat": 25.0500, "lng": 61.7500},
    {"name": "Gawadar", "province": "Balochistan", "lat": 25.1300, "lng": 62.3200},
    {"name": "Lasbela", "province": "Balochistan", "lat": 25.9300, "lng": 66.2500},
    {"name": "Hub", "province": "Balochistan", "lat": 25.0300, "lng": 66.8600},
    {"name": "Sonmiani", "province": "Balochistan", "lat": 25.0800, "lng": 66.7700},
    {"name": "Uthal", "province": "Balochistan", "lat": 25.7800, "lng": 66.0200},
    {"name": "Winder", "province": "Balochistan", "lat": 25.5900, "lng": 66.5400},
    {"name": "Skardu", "province": "Gilgit-Baltistan", "lat": 35.2900, "lng": 75.5500},
    {"name": "Hunza", "province": "Gilgit-Baltistan", "lat": 36.3100, "lng": 74.6500},
    {"name": "Ghizer", "province": "Gilgit-Baltistan", "lat": 36.1500, "lng": 73.3000},
    {"name": "Mirpur", "province": "Azad Kashmir", "lat": 33.1500, "lng": 73.7500},
    {"name": "Kotli", "province": "Azad Kashmir", "lat": 33.5100, "lng": 73.9000},
    {"name": "Bhimber", "province": "Azad Kashmir", "lat": 32.9500, "lng": 74.0500},
    {"name": "Rawalakot", "province": "Azad Kashmir", "lat": 33.8500, "lng": 73.7500},
    {"name": "Bagh", "province": "Azad Kashmir", "lat": 34.0500, "lng": 73.7500},
    {"name": "Poonch", "province": "Azad Kashmir", "lat": 33.7700, "lng": 74.1000},
    {"name": "Sindhri", "province": "Sindh", "lat": 25.3000, "lng": 68.8000},
    {"name": "Shikarpur", "province": "Sindh", "lat": 27.9500, "lng": 68.6500},
    {"name": "Khairpur", "province": "Sindh", "lat": 27.5300, "lng": 68.7600},
    {"name": "Dadu", "province": "Sindh", "lat": 26.7300, "lng": 67.7700},
    {"name": "Thatta", "province": "Sindh", "lat": 24.7400, "lng": 67.9200},
    {"name": "Badin", "province": "Sindh", "lat": 24.6500, "lng": 68.8400},
    {"name": "Mirpur Khas", "province": "Sindh", "lat": 25.3700, "lng": 69.0300},
    {"name": "Umerkot", "province": "Sindh", "lat": 25.3700, "lng": 69.7400},
    {"name": "Tando Adam", "province": "Sindh", "lat": 25.7700, "lng": 68.6700},
    {"name": "Tando Allahyar", "province": "Sindh", "lat": 25.4600, "lng": 68.6400},
    {"name": "Ghotki", "province": "Sindh", "lat": 28.0200, "lng": 69.3200},
    {"name": "Kashmore", "province": "Sindh", "lat": 28.1700, "lng": 69.5900},
    {"name": "Sukkur", "province": "Sindh", "lat": 27.7052, "lng": 68.8574},
    {"name": "Sanghar", "province": "Sindh", "lat": 25.5200, "lng": 69.3500},
    {"name": "Naushahro Feroze", "province": "Sindh", "lat": 26.9700, "lng": 68.2400},
    {"name": "Matiari", "province": "Sindh", "lat": 25.6000, "lng": 68.4000},
    {"name": "Tando Muhammad Khan", "province": "Sindh", "lat": 25.1300, "lng": 68.5400},
    {"name": "Sujawal", "province": "Sindh", "lat": 24.6000, "lng": 68.0000},
    {"name": "Malir", "province": "Sindh", "lat": 24.8800, "lng": 67.3300},
    {"name": "Korangi", "province": "Sindh", "lat": 24.8300, "lng": 67.3700},
    {"name": "Central Karachi", "province": "Sindh", "lat": 24.8600, "lng": 67.0300},
    {"name": "South Karachi", "province": "Sindh", "lat": 24.8200, "lng": 67.0300},
    {"name": "East Karachi", "province": "Sindh", "lat": 24.8900, "lng": 67.1000},
    {"name": "West Karachi", "province": "Sindh", "lat": 24.9300, "lng": 66.9900},
]

def find_pakistan_city(city_name: str):
    """Find a Pakistan city by name (case-insensitive)"""
    city_name_lower = city_name.lower().strip()
    for city in PAKISTAN_CITIES:
        if city["name"].lower() == city_name_lower:
            return city
        # Check for partial matches if exact not found
        if city_name_lower in city["name"].lower():
            return city
    return None

def search_pakistan_cities(query: str, limit: int = 10):
    """Search Pakistan cities by name or province (case-insensitive)"""
    query_lower = query.lower().strip()
    results = []
    
    for city in PAKISTAN_CITIES:
        if (
            query_lower in city["name"].lower()
            or query_lower in city["province"].lower()
        ):
            results.append(city)
            if len(results) >= limit:
                break
                
    return results
