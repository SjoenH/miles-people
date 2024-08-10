import requests
from bs4 import BeautifulSoup
import json

url = "https://www.miles.no/vi-er-miles/ansatte"
response = requests.get(url)

if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')

    data = {}
    for accordion_item in soup.find_all('div', class_='c-accordion__item'):
        location = accordion_item.find('h2', class_='c-accordion__title').get_text(strip=True)
        location_data = []

        for article in accordion_item.find_all('article'):
            person_data = {}
            person_data['name'] = article.find('div', class_='person-name').get_text(strip=True)
            person_data['img'] = article.find('img')['src']
            location_data.append(person_data)

        data[location] = location_data

    json_data = json.dumps(data, indent=4)
    print(json_data)
else:
    print("Failed to fetch the webpage.")
