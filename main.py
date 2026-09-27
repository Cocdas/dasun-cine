from fastapi import FastAPI, Query
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote, urlparse
import re
import base64
import hashlib
import time
import hmac
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# CineSubz සඳහා පමණක් වෙන්වූ API එක
app = FastAPI(
    title="CineSubz Scraper API with Token & Bypass", 
    description="Automated scraping tool with Direct Link Bypass and Token Generation"
)

CINESUBZ_BASE_URL = "https://cinesubz.lk/"

@app.get("/")
def read_root():
    """API එක නිවැරදිව වැඩ කරනවාද යන්න පරීක්ෂා කිරීමේ endpoint එක."""
    return {
        "message": "Welcome to the CineSubz Scraper API!",
        "developer": "Dasun Nethsara",
        "status": "Running smoothly 🚀"
    }

# ==========================================
# 1. AES Decryption & Security Functions
# ==========================================
def decrypt_cinesubz_link(encrypted_text: str) -> str:
    """CSPlayer හි ඇති Encrypted Base64 ලින්ක් එක 'kasun' පාස්වර්ඩ් එකෙන් Decrypt කිරීම"""
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
        return decrypted_link.strip('"').strip("'")
    except Exception:
        return None

def generate_secure_token(url: str, secret_key: str = "csplayer_secret_2026", valid_hours: int = 2) -> str:
    """Direct ලින්ක් සඳහා අලුත් Token එකක් Generate කිරීම."""
    expiry_time = int(time.time()) + (valid_hours * 3600)
    parsed_url = urlparse(url)
    path = parsed_url.path
    message = f"{path}:{expiry_time}"
    token = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    if "?" in url:
        return f"{url}&token={token}&expires={expiry_time}"
    else:
        return f"{url}?token={token}&expires={expiry_time}"

def bypass_drive_link(url: str) -> str:
    """drive.csplayer2.space වැනි ලින්ක් වල අවසාන Direct Download URL එක ලබාගැනීම."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://cinesubz.lk/", 
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    try:
        response = requests.get(url, headers=headers, allow_redirects=True, stream=True, timeout=15)
        final_url = response.url
        response.close()
        return final_url
    except requests.exceptions.RequestException as e:
        return f"Error resolving link: {str(e)}"

# ==========================================
# 2. Utility & Bypass Endpoints
# ==========================================
@app.get("/api/token/generate")
def create_token(url: str = Query(..., description="The MP4 URL to generate a token for")):
    try:
        secure_url = generate_secure_token(url)
        return {"status": True, "original_url": url, "secured_url": secure_url, "message": "Token generated successfully"}
    except Exception as e:
        return {"status": False, "message": str(e)}

@app.get("/api/cinesubz/get-direct-stream")
def get_direct_stream(url: str = Query(..., description="The drive.csplayer2.space link to bypass")):
    try:
        bypassed_link = bypass_drive_link(url)
        if "Error" in bypassed_link:
            return {"status": False, "message": bypassed_link}
        return {"status": True, "original_url": url, "bypassed_direct_url": bypassed_link, "message": "Link successfully bypassed!"}
    except Exception as e:
        return {"status": False, "message": str(e)}

# ==========================================
# 3. Main Scraper Endpoints
# ==========================================
@app.get("/api/cinesubz/search")
def search_movies(query: str = Query(..., description="Movie name to search")):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": CINESUBZ_BASE_URL}
        search_url = f"{CINESUBZ_BASE_URL}?s={quote(query)}"
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        all_results, movies, tvshows = [], [], []
        items = soup.find_all('div', class_='display-item')
        
        for item in items:
            a_tag = item.find('a', href=True)
            img_tag = item.find('img')
            imdb_tag = item.find('span', class_='imdb-score')
            
            if a_tag:
                title = a_tag.get('title', '').strip() or (item.find('h3').text.strip() if item.find('h3') else '')
                link = a_tag.get('href', '')
                image = img_tag.get('data-original') or img_tag.get('src', '') if img_tag else ''
                imdb_score = imdb_tag.text.strip() if imdb_tag else ""
                
                if title and link:
                    year_match = re.search(r'\((\d{4})\)', title)
                    year = year_match.group(1) if year_match else ""
                    media_type = "TV Show" if a_tag.get('data-ptype') == 'tvshows' or '/tvshows/' in link else "Movie"
                    
                    result_obj = {"title": title, "imdb": imdb_score, "year": year, "link": link, "image": image, "type": media_type, "description": ""}
                    all_results.append(result_obj)
                    if media_type == "Movie":
                        movies.append(result_obj)
                    else:
                        tvshows.append(result_obj)
                        
        return {"author": "@DasunNethsara", "status": True, "data": {"all": all_results, "movies": movies, "tvshows": tvshows}}
    except Exception as e:
        return {"status": False, "author": "@DasunNethsara", "message": str(e)}

@app.get("/api/cinesubz/movie")
def get_movie_details(url: str = Query(..., description="Movie page URL")):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": CINESUBZ_BASE_URL}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_element = soup.find('h1')
        title = title_element.text.strip() if title_element else "Unknown Title"
        year = re.search(r'\((\d{4})\)', title).group(1) if re.search(r'\((\d{4})\)', title) else ""
        maintitle = re.sub(r'Sinhala Subtitles.*|සිංහල උපසිරැසි සමඟ.*', '', title).strip()
        
        images = [img.get('data-src') or img.get('src') for img in soup.find_all('img') if (img.get('data-src') or img.get('src')) and 'cinesibz' not in (img.get('data-src') or img.get('src')).lower() and 'logo' not in (img.get('data-src') or img.get('src')).lower() and 'avatar' not in (img.get('data-src') or img.get('src')).lower()]
        images = list(dict.fromkeys(filter(None, images))) # Remove duplicates and nones
        main_image = images[0] if images else ""
        
        country, runtime, imdb_val = "", "", ""
        category = list(dict.fromkeys([a.text.strip() for a in soup.find_all('a', rel='category tag') if a.text.strip()]))
        
        for text_el in soup.stripped_strings:
            if 'IMDb:' in text_el:
                imdb_val = text_el.replace('IMDb:', '').strip()
            elif 'Runtime:' in text_el or 'min' in text_el.lower():
                rt_match = re.search(r'(\d+\s*min)', text_el, re.IGNORECASE)
                if rt_match: runtime = rt_match.group(1)

        cast_list, directors = [], []
        for a_tag in soup.find_all('a', href=True):
            href, name = a_tag['href'], a_tag.text.strip()
            if 'Cast Collection' in name or 'Go Full' in name or not name: continue
            if '/cast/' in href and not any(c['actor']['name'] == name for c in cast_list):
                cast_list.append({"actor": {"name": name, "link": href}, "character": ""})
            elif '/director/' in href and name not in directors:
                directors.append(name)

        download_urls = []
        download_buttons = soup.find_all('a', class_='movie-download-button')
        
        if download_buttons:
            for btn in download_buttons:
                href = btn.get('href', '')
                meta_text = btn.find('span', class_='movie-download-meta').text if btn.find('span', class_='movie-download-meta') else ""
                parts = [p.strip() for p in meta_text.split('•')]
                quality, size, language = (parts[0] if len(parts) > 0 else "Unknown"), (parts[1] if len(parts) > 1 else "Unknown"), (parts[2] if len(parts) > 2 else "Unknown")
                
                actual_link = href
                if 'zt-links' in href:
                    try:
                        zt_res = requests.get(href, headers=headers, timeout=5)
                        link_tag = BeautifulSoup(zt_res.text, 'html.parser').find('a', id='link')
                        if link_tag and link_tag.get('href'): actual_link = link_tag.get('href')
                    except: pass
                if 'google.com' in actual_link: actual_link = actual_link.replace('google.com', 'drive.csplayer2.space')
                if actual_link.endswith('.mp4') and 'drive.csplayer2.space' in actual_link: actual_link = actual_link[:-4] + '?ext=mp4'
                
                if not any(d['link'] == actual_link for d in download_urls):
                    download_urls.append({"quality": quality, "size": size, "language": language, "link": actual_link})
        else:
            for a_tag in soup.find_all('a', href=True):
                href, text = a_tag['href'], a_tag.text.strip()
                if 'csplayer' in href or 'drive.' in href:
                    quality = "1080p" if "1080" in text else "720p" if "720" in text else "480p" if "480" in text else "WEB-DL"
                    size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:MB|GB))', text, re.IGNORECASE)
                    size = size_match.group(1) if size_match else "Unknown Size"
                    if 'google.com' in href: href = href.replace('google.com', 'drive.csplayer2.space')
                    if href.endswith('.mp4') and 'drive.csplayer2.space' in href: href = href[:-4] + '?ext=mp4'
                    if not any(d['link'] == href for d in download_urls):
                        download_urls.append({"quality": quality, "size": size, "language": "Sinhala/Unknown", "link": href})

        return {
            "author": "@DasunNethsara", "status": True,
            "data": {
                "maintitle": maintitle, "title": title, "dateCreate": year, "country": country, "runtime": runtime, "category": category,
                "mainImage": main_image, "imageUrls": images, "description": "", "rating": {"value": "00", "count": "00"}, 
                "imdb": {"value": imdb_val, "count": "00"}, "director": {"name": directors}, "cast": cast_list, "downloadUrl": download_urls
            }
        }
    except Exception as e:
        return {"status": False, "author": "@DasunNethsara", "message": str(e)}

# ==========================================
# 4. Resolve Endpoint (@DarkYasiya Format)
# ==========================================
@app.get("/api/cinesubz/resolve")
def resolve_csplayer_link(url: str = Query(..., description="CSPlayer Download URL")):
    """URL හරහා Title එක සහ Size එක ලබාගෙන, @DarkYasiya JSON ආකෘතියට සකසා ලින්ක් ලබා දීම."""
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
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 404:
            return {"author": "@DarkYasiya", "status": False, "message": "මෙම වීඩියෝව සර්වර් එකෙන් ඉවත් කර ඇත."}
            
        response.raise_for_status()
        html = response.text
        
        # පිටුවෙන් වීඩියෝවේ Size එක සොයාගැනීම
        file_size = "Unknown Size"
        size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:MB|GB))', html, re.IGNORECASE)
        if size_match:
            file_size = size_match.group(1)
        
        actual_urls = []
        
        # API / XHR Bypass
        api_endpoints = re.findall(r'action="([^"]+)"', html)
        for api in api_endpoints:
            if '/api/source' in api or '/token' in api:
                bypass_url = api if api.startswith('http') else f"https://{urlparse(url).netloc}{api}"
                try:
                    res = requests.post(bypass_url, headers={"X-Requested-With": "XMLHttpRequest", "Referer": url})
                    if res.status_code == 200:
                        json_data = res.json()
                        if 'data' in json_data:
                            bypass_link = json_data['data']
                            if not any(d['url'] == bypass_link for d in actual_urls):
                                actual_urls.append({"url": bypass_link})
                except:
                    pass
        
        # Hex/Payload Decryption
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
            except Exception:
                continue

        # Standard HTML Encrypted Links
        encrypted_matches = re.findall(r'(U2FsdGVkX1[a-zA-Z0-9\/\+]+={0,2})', html)
        for enc_text in encrypted_matches:
            decrypted_url = decrypt_cinesubz_link(enc_text)
            if decrypted_url and ('http' in decrypted_url or '.mp4' in decrypted_url):
                if "google.com" in decrypted_url:
                    decrypted_url = decrypted_url.replace("google.com", "drive.csplayer2.space")
                if not any(d['url'] == decrypted_url for d in actual_urls):
                    actual_urls.append({"url": decrypted_url})
        
        # Telegram Links
        tg_links = re.findall(r'(https?://(?:t\.me|telegram\.me)/[a-zA-Z0-9_]+\?start=[a-zA-Z0-9_]+)', html)
        for tg in tg_links:
            if not any(d['url'] == tg for d in actual_urls):
                actual_urls.append({"url": tg})
                
        # Token Links
        token_links = re.findall(r'(https?://[^\s"\'<>]+(?:token=[a-zA-Z0-9\.\-\_]+|\.mp4))', html)
        for dl in token_links:
            if ('token=' in dl or '.mp4' in dl) and 'cinesubz' not in dl.lower():
                if not any(d['url'] == dl for d in actual_urls):
                    actual_urls.append({"url": dl})
                    
        return {
            "author": "@DarkYasiya",
            "status": True,
            "data": {
                "title": file_title,
                "size": file_size,
                "downloadUrls": actual_urls
            }
        }
    except Exception as e:
        return {"status": False, "author": "@DarkYasiya", "message": f"Error: {str(e)}"}
