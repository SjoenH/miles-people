import requests
from bs4 import BeautifulSoup
import json
from tqdm import tqdm
import ollama
import os
import time
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_data():
    url = "https://www.miles.no/vi-er-miles/ansatte"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        data = {}
        accordion_items = soup.find_all('div', class_='c-accordion__item')
        
        for accordion_item in tqdm(accordion_items, desc="Scraping locations"):
            location = accordion_item.find('h2', class_='c-accordion__title').get_text(strip=True)
            location_data = []

            articles = accordion_item.find_all('article')
            for article in tqdm(articles, desc=f"Scraping {location}", leave=False):
                person_name = article.find('div', class_='person-name').get_text(strip=True)
                person_file = f"people/{location}/{person_name.replace(' ', '_')}.json"
                
                # Check if we've already scraped this person
                if os.path.exists(person_file):
                    print(f"Loading existing data for: {person_name}")
                    person_data = load_json(person_file)
                else:
                    person_data = {}
                    person_data['name'] = person_name
                    person_data['location'] = location
                    person_data['img'] = article.find('img')['src']
                    person_data['href'] = article.find('a')['href']
                    
                    print(f"Fetching details for: {person_name}")
                    details_page = requests.get(person_data['href'])
                    details_soup = BeautifulSoup(details_page.content, 'html.parser')
                    person_data['description'] = details_soup.find('div', class_='entry-content').get_text(strip=True)
                    
                    # Add profession scraping
                    title_location = details_soup.find('div', class_='title-location')
                    if title_location:
                        profession_location = title_location.get_text(strip=True)
                        profession = re.split(r',\s*', profession_location)[0]  # Split by comma and take the first part
                        person_data['profession'] = profession
                    else:
                        person_data['profession'] = "Not specified"
                    
                    # Save individual person data
                    save_json(person_data, person_file)

                location_data.append(person_data)

            data[location] = location_data

        return data
    else:
        print("Failed to fetch the webpage.")
        return None

def save_json(data, filename):
    directory = os.path.dirname(filename)
    if directory:
        os.makedirs(directory, exist_ok=True)
    json_data = json.dumps(data, indent=4)
    print(f"Saving data to {filename}...")
    with open(filename, 'w') as file:
        file.write(json_data)
    print("Data saved successfully!")

def load_json(filename):
    with open(filename, 'r') as file:
        return json.load(file)

def generate_ai_content(data, max_retries=3):
    for location, people in tqdm(data.items(), desc="Processing locations"):
        for person in tqdm(people, desc=f"Processing {location}", leave=False):
            person_file = f"people/{location}/{person['name'].replace(' ', '_')}.json"
            
            # Check if person data already exists with AI content
            if os.path.exists(person_file):
                person_data = load_json(person_file)
                if 'haiku' in person_data and person_data['haiku'] and 'summary_en' in person_data and person_data['summary_en']:
                    person.update(person_data)
                    continue

            # Generate haiku
            haiku_prompt = f"Generate a haiku for {person['name']} based on this information: {person['description']}. A haiku is a short poem with three lines, where the first line has 5 syllables, the second line has 7 syllables, and the third line has 5 syllables. Reply with just the haiku in English, no additional text."
            person['haiku'] = generate_ai_response(haiku_prompt, max_retries, f"Haiku for {person['name']}")

            # Generate translated summary
            summary_prompt = f"Translate and summarize the following description of {person['name']} into a short paragraph in English, about 2-3 sentences long: {person['description']}"
            person['summary_en'] = generate_ai_response(summary_prompt, max_retries, f"Summary for {person['name']}")

            # Save updated person data
            save_json(person, person_file)

    return data

def generate_ai_response(prompt, max_retries, description):
    for attempt in range(max_retries):
        try:
            response = ollama.generate(model="llama3.2", prompt=prompt)
            generated_text = response['response']
            
            # Log the full AI response
            logging.info(f"{description} (Attempt {attempt + 1}):\n{generated_text}\n")
            
            if generated_text.strip():
                return generated_text.strip()
            else:
                raise ValueError("Empty AI response")
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed for {description}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(5)  # Wait for 5 seconds before retrying
    
    return f"Unable to generate {description.lower()}"

if __name__ == "__main__":
    # Step 1: Scrape data
    scraped_data = scrape_data()
    if scraped_data:
        save_json(scraped_data, 'scraped_data.json')

    # Step 2: Generate AI content
    print("Generating AI content...")
    with open('scraped_data.json', 'r') as file:
        data = json.load(file)
    
    ai_enhanced_data = generate_ai_content(data)
    save_json(ai_enhanced_data, 'ai_enhanced_data.json')
