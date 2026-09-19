from fastapi import FastAPI, Query
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

# CineSubz සඳහා පමණක් වෙන්වූ API එක - Developed by Dasun Nethsara
app = FastAPI(
    title="CineSubz Scraper API",
    description="Dedicated Scraper API for CineSubz movies, series, and direct download links"
)

BASE_URL = "https://cinesubz.lk/"

# -------------------------------------------------------------
# 1. ROOT ENDPOINT (API එක පරීක්ෂා කිරීම)
# -------------------------------------------------------------
@app.get("/")
def read_root():
    return {
        "message": "Welcome to the CineSubz API!",
        "developer": "Dasun Nethsara",
        "status": "Running smoothly 🚀"
    }

# -------------------------------------------------------------
# 2. SEARCH ENDPOINT (චිත්‍රපට සහ ටීවී කතා මාලා සෙවීම)
# -------------------------------------------------------------
@app.get("/api/cinesubz/search")
def search_movies(query: str = Query(..., description="සෙවිය යුතු චිත්‍රපටයේ නම")):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": BASE_URL
        }
        
        search_url = f"{BASE_URL}?s={quote(query)}"
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        all_results = []
        movies = []
        tvshows = []
        
        # CineSubz හි චිත්‍රපට කාඩ්පත් (display-item) හඳුනාගැනීම
        items = soup.find_all('div', class_='display-item')
        
        for item in items:
            a_tag = item.find('a', href=True)
            img_tag = item.find('img')
            imdb_tag = item.find('span', class_='imdb-score')
            
            if a_tag:
                title = a_tag.get('title', '').strip()
                if not title:
                    h3_tag = item.find('h3')
                    title = h3_tag.text.strip() if h3_tag else ''
                    
                link = a_tag.get('href', '')
                
                # lazy-load පින්තූර ලබා ගැනීම
                image = ''
                if img_tag:
                    image = img_tag.get('data-original') or img_tag.get('src', '')
                    
                imdb_score = imdb_tag.text.strip() if imdb_tag else ""
                
                if title and link:
                    # මාතෘකාවෙන් වර්ෂය වෙන් කිරීම
                    year_match = re.search(r'\((\d{4})\)', title)
                    year = year_match.group(1) if year_match else ""
                    
                    # Movie හෝ TV Show ද යන්න තීරණය කිරීම
                    is_tv = a_tag.get('data-ptype') == 'tvshows' or '/tvshows/' in link
                    media_type = "TV Show" if is_tv else "Movie"
                    
                    result_obj = {
                        "title": title,
                        "imdb": imdb_score,
                        "year": year,
                        "link": link,
                        "image": image,
                        "type": media_type,
                        "description": ""
                    }
                    
                    all_results.append(result_obj)
                    
                    if media_type == "Movie":
                        movies.append(result_obj)
                    else:
                        tvshows.append(result_obj)
                        
        return {
            "author": "@DasunNethsara",
            "status": True,
            "data": {
                "all": all_results,
                "movies": movies,
                "tvshows": tvshows
            }
        }
        
    except Exception as e:
        return {"status": False, "author": "@DasunNethsara", "message": str(e)}

# -------------------------------------------------------------
# 3. MOVIE DETAILS & CSPLAYER LINKS (විස්තර සහ ඩවුන්ලෝඩ් ලින්ක්ස්)
# -------------------------------------------------------------
@app.get("/api/cinesubz/movie")
def get_movie_details(url: str = Query(..., description="චිත්‍රපටයේ CineSubz URL එක")):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": BASE_URL
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. මාතෘකාව සහ මූලික විස්තර
        title_element = soup.find('h1')
        title = title_element.text.strip() if title_element else "Unknown Title"
        
        year_match = re.search(r'\((\d{4})\)', title)
        year = year_match.group(1) if year_match else ""
        
        maintitle = re.sub(r'Sinhala Subtitles.*', '', title).strip()
        
        # පින්තූර ලබා ගැනීම
        images = []
        main_image = ""
        for img in soup.find_all('img'):
            src = img.get('data-src') or img.get('src') or ""
            if src.startswith('http') and ('uploads' in src or 'tmdb.org' in src):
                if src not in images:
                    images.append(src)
        if images:
            main_image = images[0]

        # 2. නළු නිළියන් සහ අධ්‍යක්ෂවරුන්
        cast_list = []
        directors = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            name = a_tag.text.strip()
            if '/cast/' in href and name:
                if not any(c['actor']['name'] == name for c in cast_list):
                    cast_list.append({"actor": {"name": name, "link": href}, "character": ""})
            elif '/director/' in href and name:
                if name not in directors:
                    directors.append(name)

        # 3. ඩවුන්ලෝඩ් ලින්ක්ස් (CSPlayer links) සෙවීම
        download_urls = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            text = a_tag.text.strip()
            
            if 'csplayer' in href or 'drive.' in href:
                quality = "720p" if "720" in text else "1080p" if "1080" in text else "480p" if "480" in text else "WEB-DL"
                size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:MB|GB))', text, re.IGNORECASE)
                size = size_match.group(1) if size_match else "Unknown Size"
                
                if not any(d['link'] == href for d in download_urls):
                    download_urls.append({
                        "quality": quality,
                        "size": size,
                        "language": "Kannada/Sinhala",
                        "link": href
                    })

        return {
            "author": "@DasunNethsara",
            "status": True,
            "data": {
                "maintitle": maintitle,
                "title": title,
                "dateCreate": year,
                "country": "India",
                "runtime": "",
                "category": [],
                "mainImage": main_image,
                "imageUrls": images[:2],
                "description": "",
                "rating": {"value": "00", "count": "00"},
                "imdb": {"value": "", "count": "00"},
                "director": {"name": directors},
                "cast": cast_list,
                "downloadUrl": download_urls
            }
        }
    except Exception as e:
        return {"status": False, "author": "@DasunNethsara", "message": str(e)}

# -------------------------------------------------------------
# 4. CSPLAYER RESOLVE ENDPOINT (ඩවුන්ලෝඩ් ලින්ක් එක Bypass කිරීම)
# -------------------------------------------------------------
@app.get("/api/cinesubz/resolve")
def resolve_csplayer_link(url: str = Query(..., description="CSPlayer Download URL")):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        html = response.text
        
        soup = BeautifulSoup(html, 'html.parser')
        actual_urls = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Telegram Bot ලින්ක් එක හෝ Direct MP4 සබැඳිය ලබා ගැනීම
            if 'telegram.me' in href or 't.me' in href or '?token=' in href or '.mp4' in href or 'drive' in href:
                if not any(d['url'] == href for d in actual_urls):
                    actual_urls.append({"url": href})
                    
        return {
            "author": "@DasunNethsara",
            "status": True,
            "data": {
                "title": "Direct Download File",
                "size": "Original Quality",
                "downloadUrls": actual_urls
            }
        }
    except Exception as e:
        return {"status": False, "author": "@DasunNethsara", "message": str(e)}
