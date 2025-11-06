import requests
import pandas as pd
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
import time

API_KEY = "e22e3f4c6458a05b24ceb325d55e7472"

# Liste des villes françaises à traiter
cities = [
    "Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Nantes", "Strasbourg", "Montpellier", "Bordeaux", "Lille",
    "Rennes", "Reims", "Le Havre", "Saint-Étienne", "Toulon", "Grenoble", "Dijon", "Angers", "Nîmes", "Villeurbanne",
    "Clermont-Ferrand", "Le Mans", "Aix-en-Provence", "Brest", "Tours", "Amiens", "Limoges", "Annecy", "Perpignan", 
    "Metz", "Besançon", "Orléans", "Rouen", "Mulhouse", "Caen"
]

# Nombre d'hôtels à récupérer par ville
hotels_per_city = 5

# Utilisation de Nominatim pour géolocaliser les hôtels
geolocator = Nominatim(user_agent="hotel_mapper")


# Liste pour stocker les données de géolocalisation des villes
geoloc_data = []

for city in cities:
    try:
        # Construction de l'URL pour la requête de géolocalisation
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},FR&limit=1&appid={API_KEY}"
        
        # Envoi de la requête GET à OpenWeather pour récupérer les coordonnées
        r = requests.get(url).json()
        
        # Si des données sont récupérées, ajout des coordonnées à la liste
        if r:
            geoloc_data.append({"city": city, "lat": r[0]["lat"], "lon": r[0]["lon"]})
        
        # Attente d'une seconde entre chaque requête pour éviter le blocage par l'API
        time.sleep(1)
    except Exception as e:
        # Si une erreur se produit pendant la requête, elle est ignorée
        pass

# Sauvegarde des résultats dans un fichier CSV
df_geo = pd.DataFrame(geoloc_data)
df_geo.to_csv("cities_geoloc.csv", index=False)


weather_data = []

# Pour chaque ville récupérée dans les coordonnées
for _, row in df_geo.iterrows():
    try:
        # Construction de l'URL pour récupérer les prévisions météo sur 5 jours
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={row['lat']}&lon={row['lon']}&appid={API_KEY}&units=metric&lang=fr"
        
        # Envoi de la requête GET pour récupérer les données météo
        r = requests.get(url).json()
        
        # Vérification que les données météo sont disponibles
        if "list" in r:
            temps, rains, clouds = [], [], []
            
            # Traitement des données de prévision (toutes les 3 heures)
            for item in r["list"]:
                temps.append(item["main"]["temp"])
                rains.append(item.get("rain", {}).get("3h", 0))
                clouds.append(item["clouds"]["all"])
            
            # Calcul de la température moyenne, de la pluie moyenne et du taux de nuages moyen
            avg_temp = sum(temps)/len(temps)
            avg_rain = sum(rains)/len(rains)
            avg_cloud = sum(clouds)/len(clouds)
            
            # Calcul du score météo : température - (pluie * poids) - (nuages * poids)
            score = avg_temp - (avg_rain*0.5) - (avg_cloud*0.2)
            
            # Ajout des données dans la liste weather_data
            weather_data.append({
                "city": row["city"],
                "avg_temp": round(avg_temp, 1),
                "avg_rain": round(avg_rain, 1),
                "avg_cloud": round(avg_cloud, 1),
                "weather_score": round(score, 2)
            })
        
        # Attente entre les requêtes pour respecter les limites de l'API
        time.sleep(1)
    except Exception as e:
        # Si une erreur se produit lors de la récupération des prévisions météo, elle est ignorée
        pass

# Sauvegarde des résultats dans un fichier CSV
df_weather = pd.DataFrame(weather_data)
df_weather.to_csv("weather_data.csv", index=False)


# Tri des villes par score météo et sélection des 5 meilleures
df_top = df_weather.sort_values(by="weather_score", ascending=False).head(5)
df_top.to_csv("top_cities.csv", index=False)


# Liste pour stocker les données des hôtels
hotels_list = []

# Headers pour simuler une requête depuis un navigateur
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}

# Pour chaque ville dans le Top 5
for city in df_top["city"]:
    # Construction de l'URL pour la recherche d'hôtels sur Booking.com
    url = f"https://www.booking.com/searchresults.html?ss={city}&rows={hotels_per_city}"
    
    # Envoi de la requête GET
    r = requests.get(url, headers=headers)
    
    # Parsing du contenu HTML de la page avec BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    
    # Sélection des cartes d'hôtels
    hotel_cards = soup.select("div[data-testid='property-card']")[:hotels_per_city]
    
    # Pour chaque hôtel, récupérer son nom et sa note
    for card in hotel_cards:
        name_tag = card.select_one("div[data-testid='title']")
        rating_tag = card.select_one("div[data-testid='review-score']")
        
        name = name_tag.text.strip() if name_tag else "N/A"
        rating = rating_tag.text.strip() if rating_tag else "N/A"
        
        # Géolocalisation de l'hôtel via Nominatim
        location_query = f"{name}, {city}, France"
        try:
            location = geolocator.geocode(location_query)
            lat = location.latitude if location else None
            lon = location.longitude if location else None
        except:
            lat, lon = None, None
        
        # Ajout des informations de l'hôtel dans la liste
        hotels_list.append({
            "city": city,
            "hotel_name": name,
            "rating": rating,
            "lat": lat,
            "lon": lon
        })
        
        # Attente entre les requêtes pour ne pas être bloqué
        time.sleep(1)

# Sauvegarde des données des hôtels dans un fichier CSV
df_hotels = pd.DataFrame(hotels_list)
df_hotels.to_csv("top5_hotels.csv", index=False)

