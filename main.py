from fastapi import FastAPI, Query, HTTPException
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI(title="CineSubz API")
CINESUBZ_BASE_URL = "https://cinesubz.lk/"

# 💡 1. Caching සඳහා සරල මතකයක් (In-memory Dictionary) සෑදීම
cache_memory = {}

@app.get("/api/cinesubz/movie")
def get_movie_details(url: str = Query(..., description="Movie page URL")):
    """චිත්‍රපටයේ සම්පූර්ණ විස්තර ලබා ගැනීම (With URL Validation & Caching)"""
    
    # 💡 2. URL Validation (අර JS කේතයේ parsePageUrl function එක මෙන්)
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        # ලින්ක් එක වැරදි නම් 400 Error එකක් යවයි
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
        
    if "cinesubz" not in url.lower():
        raise HTTPException(status_code=400, detail="Only CineSubz URLs are allowed")

    # 💡 3. Cache Checking (අර JS කේතයේ req.cache.get මෙන්)
    if url in cache_memory:
        # මතකයේ තිබේ නම් කෙලින්ම එය ලබා දෙයි (Scraping සිදු නොකරයි)
        print("Serving from Cache!") 
        return cache_memory[url]

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # මාතෘකාව ලබා ගැනීම
        title_element = soup.find('h1')
        title = title_element.text.strip() if title_element else "Unknown Title"
        
        # ඩවුන්ලෝඩ් ලින්ක්ස් ලබා ගැනීම (සරල කර ඇත)
        download_urls = []
        for a_tag in soup.find_all('a', class_='movie-download-button'):
            href = a_tag.get('href', '')
            if 'zt-links' in href or 'csplayer' in href:
                download_urls.append({"link": href})

        # අවසාන ප්‍රතිඵලය සැකසීම
        final_result = {
            "author": "@DasunNethsara",
            "status": True,
            "cached": False, # පළමු වතාව නිසා Cache එකක් නැත
            "data": {
                "title": title,
                "downloadUrl": download_urls
            }
        }
        
        # 💡 4. Cache එකෙහි Save කිරීම (අර JS කේතයේ req.cache.set මෙන්)
        # ඊළඟ වතාවේ කවුරුහරි ඉල්ලුවොත් දෙන්න මේක මතක තියාගන්නවා
        cached_result = final_result.copy()
        cached_result["cached"] = True # මීළඟ වතාවේ යද්දී cached=True ලෙස පෙන්වයි
        cache_memory[url] = cached_result

        return final_result

    except Exception as e:
        # JS කේතයේ තිබූ අයුරින්ම වැරදි කළමනාකරණය (Error Handling)
        raise HTTPException(status_code=502, detail=f"Scraping failed: {str(e)}")
