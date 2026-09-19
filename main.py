from fastapi import FastAPI, Query
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

# CineSubz සඳහා පමණක් වෙන්වූ API එක - Developed by Dasun Nethsara
app = FastAPI(
    title="CineSubz Scraper API", 
    description="Automated scraping tool dedicated for CineSubz"
)

@app.get("/")
def read_root():
    """API එක නිවැරදිව වැඩ කරනවාද යන්න පරීක්ෂා කිරීමේ endpoint එක."""
    return {
        "message": "Welcome to the CineSubz Scraper API!",
        "developer": "Dasun Nethsara",
        "status": "Running smoothly 🚀"
    }

# ==========================================
# CINESUBZ ENDPOINTS ONLY
# ==========================================

CINESUBZ_BASE_URL = "https://cinesubz.lk/"

@app.get("/api/cinesubz/search")
def search_movies(query: str = Query(..., description="Movie name to search")):
    """CineSubz වෙබ් අඩවිය තුළ චිත්‍රපට සෙවීම."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": CINESUBZ_BASE_URL
        }
        
        search_url = f"{CINESUBZ_BASE_URL}?s={quote(query)}"
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        all_results = []
        movies = []
        tvshows = []
        
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
                image = ''
                if img_tag:
                    image = img_tag.get('data-original') or img_tag.get('src', '')
                    
                imdb_score = imdb_tag.text.strip() if imdb_tag else ""
                
                if title and link:
                    year_match = re.search(r'\((\d{4})\)', title)
                    year = year_match.group(1) if year_match else ""
                    
                    media_type = "TV Show" if a_tag.get('data-ptype') == 'tvshows' or '/tvshows/' in link else "Movie"
                    
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

@app.get("/api/cinesubz/movie")
def get_movie_details(url: str = Query(..., description="Movie page URL")):
    """චිත්‍රපටයේ සම්පූර්ණ විස්තර සහ ඩවුන්ලෝඩ් ලින්ක්ස් ලබා ගැනීම."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": CINESUBZ_BASE_URL
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            title = meta_title.get('content', '').split('|')[0].strip()
        else:
            title_element = soup.find('h1')
            title = title_element.text.strip() if title_element else "Unknown Title"
        
        year_match = re.search(r'\((\d{4})\)', title)
        year = year_match.group(1) if year_match else ""
        maintitle = re.sub(r'Sinhala Subtitles.*', '', title).strip()
        
        images = []
        main_image = ""
        for img in soup.find_all('img'):
            src = img.get('data-src') or img.get('src') or ""
            if src.startswith('http') and ('uploads' in src or 'tmdb.org' in src):
                if src not in images:
                    images.append(src)
        if images:
            main_image = images[0]

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

        download_urls = []
        download_buttons = soup.find_all('a', class_='movie-download-button')
        
        if download_buttons:
            for btn in download_buttons:
                href = btn.get('href', '')
                meta_span = btn.find('span', class_='movie-download-meta')
                meta_text = meta_span.text if meta_span else ""
                
                parts = [p.strip() for p in meta_text.split('•')]
                quality = parts[0] if len(parts) > 0 else "Unknown Quality"
                size = parts[1] if len(parts) > 1 else "Unknown Size"
                language = parts[2] if len(parts) > 2 else "Unknown Language"
                
                actual_link = href
                
                if 'zt-links' in href:
                    try:
                        zt_res = requests.get(href, headers=headers, timeout=5)
                        zt_soup = BeautifulSoup(zt_res.text, 'html.parser')
                        link_tag = zt_soup.find('a', id='link')
                        if link_tag and link_tag.get('href'):
                            actual_link = link_tag.get('href')
                    except Exception as e:
                        pass
                
                if not any(d['link'] == actual_link for d in download_urls):
                    download_urls.append({
                        "quality": quality,
                        "size": size,
                        "language": language,
                        "link": actual_link
                    })
        else:
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                text = a_tag.text.strip()
                if 'csplayer' in href or 'drive.' in href:
                    quality = "1080p" if "1080" in text else "720p" if "720" in text else "480p" if "480" in text else "WEB-DL"
                    size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:MB|GB))', text, re.IGNORECASE)
                    size = size_match.group(1) if size_match else "Unknown Size"
                    if not any(d['link'] == href for d in download_urls):
                        download_urls.append({
                            "quality": quality,
                            "size": size,
                            "language": "Sinhala/Unknown",
                            "link": href
                        })

        return {
            "author": "@DasunNethsara",
            "status": True,
            "data": {
                "maintitle": maintitle,
                "title": title,
                "dateCreate": year,
                "country": "",
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

@app.get("/api/cinesubz/resolve")
def resolve_csplayer_link(url: str = Query(..., description="CSPlayer Download URL")):
    """අපි හොයාගත් /api/download-data භාවිතයෙන් සහ HTML scraping මඟින් Token/MP4 ලින්ක් ලබා ගැනීම."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": url,
            "X-Requested-With": "XMLHttpRequest"
        }
        
        actual_urls = []
        
        # 1. අපි සොයාගත් රහසිගත API එකට (POST request) යැවීම මඟින් උත්සාහ කිරීම
        api_endpoint = "https://drive.csplayer2.space/api/download-data"
        try:
            api_res = requests.post(api_endpoint, headers=headers, data={"url": url}, timeout=5)
            if api_res.status_code == 200:
                json_data = api_res.json()
                # ලැබෙන JSON එක ඇතුළේ ලින්ක්ස් තිබේ නම් ඒවා ලබා ගැනීම
                if isinstance(json_data, dict):
                    for key, val in json_data.items():
                        if isinstance(val, str) and ('token=' in val or '.mp4' in val or 't.me' in val):
                            if not any(d['url'] == val for d in actual_urls):
                                actual_urls.append({"url": val})
        except Exception:
            pass

        # 2. සාමාන්‍ය පිටුවට ගොස් HTML/JS කේතයෙන් Token සහ Telegram ලින්ක්ස් සෙවීම (Fallback)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        html = response.text
        
        # Telegram Bot ලින්ක්ස් සෙවීම
        tg_links = re.findall(r'(https?://(?:t\.me|telegram\.me)/[a-zA-Z0-9_]+\?start=[a-zA-Z0-9_]+)', html)
        for tg in tg_links:
            if not any(d['url'] == tg for d in actual_urls):
                actual_urls.append({"url": tg})
                
        # Token සහිත MP4 ලින්ක්ස් සෙවීම
        token_links = re.findall(r'(https?://[^\s"\'<>]+(?:token=[a-zA-Z0-9\.\-\_]+|\.mp4))', html)
        for dl in token_links:
            if ('token=' in dl or '.mp4' in dl) and 'cinesubz' not in dl.lower():
                if not any(d['url'] == dl for d in actual_urls):
                    actual_urls.append({"url": dl})
                    
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
        return {"status": "error", "message": str(e)}
