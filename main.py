from fastapi import FastAPI, Query
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

# API එක ආරම්භ කිරීම - Developed by Dasun Nethsara
app = FastAPI(title="Movie & Drama Scraper API", description="Automated scraping tool for Dramakey, Downloadwella, and CineSubz")

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
    """Downloadwella ලින්ක් එකක් ලබාගෙන, POST request එකක් මගින් form submit කර එහි අවසාන Direct Link එක ලබා දෙයි."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": url
        }
        
        session = requests.Session()
        
        # පියවර 1: GET request යවා සැඟවුණු form data ලබා ගැනීම
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
                
        # පියවර 2: POST request එක මගින් 'Create Download Link' එබීම
        post_response = session.post(url, data=form_data, headers=headers)
        post_response.raise_for_status()
        
        # පියවර 3: දෙවන පිටුවෙන් Direct Link එක සෙවීම
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

CINESUBZ_BASE_URL = "https://cinesubz.net/"

@app.get("/api/cinesubz/search")
def search_movies(query: str = Query(..., description="Movie name to search")):
    """CineSubz වෙබ් අඩවිය තුළ චිත්‍රපට සෙවීම සහ අලුත් JSON ආකෘතියට ප්‍රතිඵල ලබා දීම."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": CINESUBZ_BASE_URL
        }
        
        search_url = f"{CINESUBZ_BASE_URL}?s={quote(query)}"
        
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        all_results = []
        movies = []
        tvshows = []
        
        items = soup.find_all(['article', 'div'], class_=lambda x: x and ('post' in x or 'item' in x or 'ittl' in x or 'box' in x))
        if not items:
            items = soup.find_all('div', class_='result-item') or soup.find_all('article') or soup.find_all('div', class_='search-result')

        for item in items:
            title_tag = item.find(['h2', 'h3', 'a'], class_=['title', 'tit']) or item.find('a')
            link_tag = item.find('a')
            img_tag = item.find('img')
            
            if link_tag and title_tag:
                title = title_tag.text.strip()
                link = link_tag.get('href')
                
                if not title or not link or link == CINESUBZ_BASE_URL:
                    continue
                
                image = None
                if img_tag:
                    image = img_tag.get('data-src') or img_tag.get('src') or img_tag.get('data-lazy-src')
                
                if link.startswith('http') and not any(r['link'] == link for r in all_results):
                    
                    # 1. වර්ෂය (Year) සොයා ගැනීම
                    year_match = re.search(r'\((\d{4})\)', title)
                    year = year_match.group(1) if year_match else ""
                    
                    # 2. Movie ද TV Show ද යන්න තීරණය කිරීම
                    is_tv = 'tvshows' in link or 'tv-shows' in link or 'season' in link.lower() or 'episode' in link.lower()
                    media_type = "TV Show" if is_tv else "Movie"
                    
                    result_obj = {
                        "title": title,
                        "imdb": "", 
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
def get_movie_download_links(url: str = Query(..., description="Movie page URL from search results")):
    """CineSubz ලින්ක් එක (URL) ලබා දී, එහි ඇති ඩවුන්ලෝඩ් ලින්ක්ස් සහ විස්තර ලබා ගනී."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": CINESUBZ_BASE_URL
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_element = soup.find('h1')
        title = title_element.text.strip() if title_element else "Unknown Movie"
        
        download_links = []
        
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href')
            text = a_tag.text.strip()
            
            if href and href.startswith('http'):
                ignored_domains = ['facebook.com', 't.me', 'telegram.me', 'whatsapp.com', 'twitter.com', '#', 'instagram.com', 'youtube.com']
                if not any(domain in href for domain in ignored_domains):
                    keywords = ['download', '1080p', '720p', '480p', 'pixeldrain', 'gofile', 'mega', 'zippy', 'drive', 'hubcloud']
                    if any(kw in text.lower() or kw in href.lower() for kw in keywords):
                        if not any(d['url'] == href for d in download_links):
                            download_links.append({
                                "quality_or_label": text if text else "Download Link",
                                "url": href
                            })
                            
        if not download_links:
            for a_tag in soup.find_all('a', class_=lambda x: x and ('button' in x or 'btn' in x or 'maxbutton' in x)):
                href = a_tag.get('href')
                text = a_tag.text.strip()
                if href and href.startswith('http'):
                    download_links.append({
                        "quality_or_label": text if text else "Download Link",
                        "url": href
                    })

        return {
            "status": "success",
            "title": title,
            "movie_url": url,
            "total_links": len(download_links),
            "download_links": download_links
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
