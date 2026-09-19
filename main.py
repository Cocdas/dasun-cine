from fastapi import FastAPI, Query
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

# API එක ආරම්භ කිරීම - Developed by Dasun Nethsara
app = FastAPI(
    title="Movie & Drama Scraper API", 
    description="Automated scraping tool for Dramakey, Downloadwella, and CineSubz"
)

@app.get("/")
def read_root():
    """API එක නිවැරදිව වැඩ කරනවාද යන්න පරීක්ෂා කිරීමේ endpoint එක."""
    return {
        "message": "Welcome to the Scraper API!",
        "developer": "Dasun Nethsara",
        "status": "Running smoothly 🚀"
    }

# ==========================================
# 1. DRAMAKEY & DOWNLOADWELLA ENDPOINTS
# ==========================================

@app.get("/api/dramas")
def get_dramas():
    """Dramakey මුල් පිටුවෙන් Drama මාතෘකා සහ links ලබා දෙයි."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get("https://dramakey.com/", headers=headers)
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        dramas = []
        
        for heading in soup.find_all(['h2', 'h3']):
            link_tag = heading.find('a')
            if link_tag:
                title = link_tag.text.strip()
                link = link_tag.get('href')
                if title and link:
                    dramas.append({"title": title, "link": link})
                    
        return {"status": "success", "total_dramas_found": len(dramas), "data": dramas}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/download")
def get_download_links(url: str):
    """අදාළ ඩ්‍රාමා පිටුවේ ඇති ඩවුන්ලෝඩ් ලින්ක්ස් (Downloadwella/වෙනත්) ලබා දෙයි."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        download_links = []
        content_area = soup.find('div', class_='entry-content')
        
        if content_area:
            for link_tag in content_area.find_all('a'):
                link_text = link_tag.text.strip()
                link_href = link_tag.get('href')
                if link_text and link_href and link_href.startswith('http'):
                    download_links.append({"label": link_text, "url": link_href})
                    
        return {"status": "success", "drama_url": url, "download_links": download_links}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/downloadwella")
def get_downloadwella_direct_link(url: str):
    """Downloadwella ලින්ක් එකක් ලබාගෙන එහි අවසාන Direct Link එක ලබා දෙයි."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": url
        }
        
        session = requests.Session()
        response = session.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        form = soup.find('form')
        if not form:
            return {"status": "error", "message": "Form not found on step 1."}
            
        form_data = {}
        for input_tag in form.find_all('input'):
            input_name = input_tag.get('name')
            if input_name:
                form_data[input_name] = input_tag.get('value', '')
                
        post_response = session.post(url, data=form_data, headers=headers)
        post_response.raise_for_status()
        
        post_soup = BeautifulSoup(post_response.text, 'html.parser')
        direct_link = None
        all_links = []
        
        for a_tag in post_soup.find_all('a'):
            href = a_tag.get('href')
            if href:
                all_links.append(href)
                if href.endswith(('.mkv', '.mp4', '.zip', '.rar')) or '/d/' in href:
                    direct_link = href
                    break
        
        if not direct_link:
            span_link = post_soup.find('span', id='direct_link')
            if span_link and span_link.find('a'):
                direct_link = span_link.find('a').get('href')

        if direct_link:
            return {
                "status": "success", 
                "developer": "Dasun Nethsara",
                "original_url": url, 
                "direct_download_link": direct_link
            }
        else:
            return {
                "status": "error", 
                "message": "Could not find the final direct link. Inspect 'debug_links_found'.",
                "debug_links_found": all_links
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# 2. CINESUBZ ENDPOINTS
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
        
        # 1. නිවැරදි මාතෘකාව ලබා ගැනීම
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

        # 3. ඩවුන්ලෝඩ් ලින්ක්ස් ලබා ගැනීම (zt-links විසඳීම)
        download_urls = []
        
        # අලුත් ආකෘතිය: 'movie-download-button' සෙවීම
        download_buttons = soup.find_all('a', class_='movie-download-button')
        
        if download_buttons:
            for btn in download_buttons:
                href = btn.get('href', '')
                meta_span = btn.find('span', class_='movie-download-meta')
                meta_text = meta_span.text if meta_span else ""
                
                # Quality, Size, Language වෙන් කරගැනීම (උදා: WEB-DL 480p • 400 MB • English)
                parts = [p.strip() for p in meta_text.split('•')]
                quality = parts[0] if len(parts) > 0 else "Unknown Quality"
                size = parts[1] if len(parts) > 1 else "Unknown Size"
                language = parts[2] if len(parts) > 2 else "Unknown Language"
                
                actual_link = href
                
                # zt-links හරහා ගොස් සැබෑ CSPlayer ලින්ක් එක සොයාගැනීම
                if 'zt-links' in href:
                    try:
                        zt_res = requests.get(href, headers=headers, timeout=5)
                        zt_soup = BeautifulSoup(zt_res.text, 'html.parser')
                        link_tag = zt_soup.find('a', id='link')
                        if link_tag and link_tag.get('href'):
                            actual_link = link_tag.get('href')
                    except Exception as e:
                        pass # දෝෂයක් ආවොත් මුල් ලින්ක් එකම තබාගනී
                
                if not any(d['link'] == actual_link for d in download_urls):
                    download_urls.append({
                        "quality": quality,
                        "size": size,
                        "language": language,
                        "link": actual_link
                    })
        else:
            # පැරණි ආකෘතිය සඳහා Fallback (අමතර ආරක්ෂාවට)
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
    """CSPlayer ලින්ක් එකකට ගොස් සැබෑ Direct MP4 සහ Telegram ලින්ක්ස් Bypass කරයි."""
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
