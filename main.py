from fastapi import FastAPI, Query
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote
import re
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# CineSubz සඳහා පමණක් වෙන්වූ API එක - Developed by Dasun Nethsara
app = FastAPI(
    title="CineSubz Scraper API", 
    description="Automated scraping tool dedicated for CineSubz matching target JSON format"
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
# AES Decryption Function
# ==========================================
def decrypt_cinesubz_link(encrypted_text: str) -> str:
    """CSPlayer හි ඇති Encrypted Base64 ලින්ක් එක kasun පාස්වර්ඩ් එකෙන් Decrypt කිරීම"""
    password = "kasun"
    try:
        encrypted_bytes = base64.b64decode(encrypted_text)
        
        if not encrypted_bytes.startswith(b"Salted__"):
            return None
            
        salt = encrypted_bytes[8:16]
        ciphertext = encrypted_bytes[16:]
        
        key_iv = b""
        prev = b""
        while len(key_iv) < 48:
            prev = hashlib.md5(prev + password.encode('utf-8') + salt).digest()
            key_iv += prev
            
        key = key_iv[:32]
        iv = key_iv[32:48]
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(ciphertext)
        decrypted_link = unpad(decrypted_padded, AES.block_size).decode('utf-8')
        
        decrypted_link = decrypted_link.strip('"').strip("'")
        return decrypted_link
    except Exception as e:
        return None

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
    """චිත්‍රපටයේ සම්පූර්ණ විස්තර සහ ඩවුන්ලෝඩ් ලින්ක්ස් නිවැරදිව ලබා ගැනීම."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": CINESUBZ_BASE_URL
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Title නිවැරදිව ලබා ගැනීම (Split නොකර)
        title_element = soup.find('h1')
        title = title_element.text.strip() if title_element else "Unknown Title"
        
        year_match = re.search(r'\((\d{4})\)', title)
        year = year_match.group(1) if year_match else ""
        maintitle = re.sub(r'Sinhala Subtitles.*|සිංහල උපසිරැසි සමඟ.*', '', title).strip()
        
        # 2. Images ලබා ගැනීම (අනවශ්‍ය ලෝගෝ ඉවත් කර සියල්ල ලබා ගැනීම)
        images = []
        for img in soup.find_all('img'):
            src = img.get('data-src') or img.get('src') or ""
            if src.startswith('http') and ('uploads' in src or 'tmdb.org' in src):
                # අනවශ්‍ය ලෝගෝ ෆිල්ටර් කිරීම
                if 'cinesibz' not in src.lower() and 'logo' not in src.lower() and 'avatar' not in src.lower():
                    if src not in images:
                        images.append(src)
        
        main_image = images[0] if images else ""

        # 3. Country, Runtime, Category, IMDb අගයන් සොයා ගැනීම
        country = ""
        runtime = ""
        category = []
        imdb_val = ""

        # Category සොයා ගැනීම
        for a_tag in soup.find_all('a', rel='category tag'):
            cat_name = a_tag.text.strip()
            if cat_name and cat_name not in category:
                category.append(cat_name)

        # Country, Runtime, IMDb සෙවීම (HTML හි පවතින Text මඟින්)
        for text_el in soup.stripped_strings:
            if 'IMDb:' in text_el:
                imdb_val = text_el.replace('IMDb:', '').strip()
            elif 'Runtime:' in text_el or 'min' in text_el.lower():
                rt_match = re.search(r'(\d+\s*min)', text_el, re.IGNORECASE)
                if rt_match:
                    runtime = rt_match.group(1)

        # 4. Cast (නළු නිළියන්) නිවැරදිව ලබා ගැනීම (අනවශ්‍ය ලින්ක්ස් ඉවත් කර)
        cast_list = []
        directors = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            name = a_tag.text.strip()
            
            # අනවශ්‍ය Cast Collection ලින්ක්ස් ඉවත් කිරීම
            if 'Cast Collection' in name or 'Go Full' in name or not name:
                continue
                
            if '/cast/' in href:
                if not any(c['actor']['name'] == name for c in cast_list):
                    cast_list.append({"actor": {"name": name, "link": href}, "character": ""})
            elif '/director/' in href:
                if name not in directors:
                    directors.append(name)

        # 5. Download Links නිවැරදි කිරීම (Google -> Drive සහ .mp4 -> ?ext=mp4)
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
                
                # --- අලුත් වෙනස: google.com මාරු කිරීම සහ ?ext=mp4 යෙදීම ---
                if 'google.com' in actual_link:
                    actual_link = actual_link.replace('google.com', 'drive.csplayer2.space')
                if actual_link.endswith('.mp4') and 'drive.csplayer2.space' in actual_link:
                    actual_link = actual_link[:-4] + '?ext=mp4'
                
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
                    
                    # --- අලුත් වෙනස: google.com මාරු කිරීම සහ ?ext=mp4 යෙදීම ---
                    if 'google.com' in href:
                        href = href.replace('google.com', 'drive.csplayer2.space')
                    if href.endswith('.mp4') and 'drive.csplayer2.space' in href:
                        href = href[:-4] + '?ext=mp4'
                        
                    if not any(d['link'] == href for d in download_urls):
                        download_urls.append({
                            "quality": quality,
                            "size": size,
                            "language": "Sinhala/Unknown",
                            "link": href
                        })

        # --- @DarkYasiya Format එකට Output කිරීම ---
        return {
            "author": "@DasunNethsara",
            "status": True,
            "data": {
                "maintitle": maintitle,
                "title": title,
                "dateCreate": year,
                "country": country,
                "runtime": runtime, 
                "category": category,
                "mainImage": main_image,
                "imageUrls": images,
                "description": "",
                "rating": {"value": "00", "count": "00"},
                "imdb": {"value": imdb_val, "count": "00"},
                "director": {"name": directors},
                "cast": cast_list,
                "downloadUrl": download_urls
            }
        }
    except Exception as e:
        return {"status": False, "author": "@DasunNethsara", "message": str(e)}

@app.get("/api/cinesubz/resolve")
def resolve_csplayer_link(url: str = Query(..., description="CSPlayer Download URL")):
    """URL හරහා Title එක ලබාගෙන, JSON ආකෘතිය නිවැරදිව සකසා MP4 ලින්ක් ලබා දීම."""
    try:
        file_title = unquote(url.split('/')[-1])
        if '?ext=' in file_title:
            file_title = file_title.split('?ext=')[0]

        if "google.com" in url:
            url = url.replace("google.com", "drive.csplayer2.space")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://cinesubz.lk/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        
        actual_urls = []
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 404:
            return {
                "author": "@DasunNethsara",
                "status": False,
                "message": "මෙම වීඩියෝව සර්වර් එකෙන් ඉවත් කර හෝ කල් ඉකුත් වී ඇත (404 Not Found)."
            }
            
        response.raise_for_status()
        html = response.text
        
        hex_matches = re.findall(r'([a-fA-F0-9]{150,})', html)
        for hex_str in hex_matches:
            try:
                payload = bytes.fromhex(hex_str)
                post_headers = headers.copy()
                post_headers["Content-Type"] = "application/octet-stream"
                
                post_res = requests.post(url, headers=post_headers, data=payload, timeout=10)
                
                if post_res.status_code == 200:
                    res_text = post_res.content.decode(errors='ignore')
                    enc_matches = re.findall(r'(U2FsdGVkX1[a-zA-Z0-9\/\+]+={0,2})', res_text)
                    
                    for enc_text in enc_matches:
                        decrypted_url = decrypt_cinesubz_link(enc_text)
                        if decrypted_url and ('http' in decrypted_url or '.mp4' in decrypted_url):
                            
                            if "google.com" in decrypted_url:
                                decrypted_url = decrypted_url.replace("google.com", "drive.csplayer2.space")
                                
                            if not any(d['url'] == decrypted_url for d in actual_urls):
                                actual_urls.append({"url": decrypted_url})
            except Exception as e:
                continue

        encrypted_matches = re.findall(r'(U2FsdGVkX1[a-zA-Z0-9\/\+]+={0,2})', html)
        for enc_text in encrypted_matches:
            decrypted_url = decrypt_cinesubz_link(enc_text)
            if decrypted_url and ('http' in decrypted_url or '.mp4' in decrypted_url):
                
                if "google.com" in decrypted_url:
                    decrypted_url = decrypted_url.replace("google.com", "drive.csplayer2.space")
                    
                if not any(d['url'] == decrypted_url for d in actual_urls):
                    actual_urls.append({"url": decrypted_url})
        
        tg_links = re.findall(r'(https?://(?:t\.me|telegram\.me)/[a-zA-Z0-9_]+\?start=[a-zA-Z0-9_]+)', html)
        for tg in tg_links:
            if not any(d['url'] == tg for d in actual_urls):
                actual_urls.append({"url": tg})
                
        token_links = re.findall(r'(https?://[^\s"\'<>]+(?:token=[a-zA-Z0-9\.\-\_]+|\.mp4))', html)
        for dl in token_links:
            if ('token=' in dl or '.mp4' in dl) and 'cinesubz' not in dl.lower():
                if not any(d['url'] == dl for d in actual_urls):
                    actual_urls.append({"url": dl})
                    
        return {
            "author": "@DasunNethsara",
            "status": True,
            "data": {
                "title": file_title,
                "size": "Original Quality",
                "downloadUrls": actual_urls
            }
        }
    except Exception as e:
        return {"status": False, "author": "@DasunNethsara", "message": f"Error: {str(e)}"}
