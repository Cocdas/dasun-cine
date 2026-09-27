from fastapi import FastAPI, Query
import cloudscraper
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

CINESUBZ_BASE_URL = "https://cinesubz.co/"

# Cloudscraper - Browser එකක් සේ ක්‍රියා කර JS Challenge මඟහැරීමට
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    }
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
# 1. AES Decryption & Security Functions
# ==========================================
def decrypt_cinesubz_link(encrypted_text: str) -> str:
    password = "kasun"
    try:
        encrypted_bytes = base64.b64decode(encrypted_text)
        if not encrypted_bytes.startswith(b"Salted__"): return None
        salt, ciphertext = encrypted_bytes[8:16], encrypted_bytes[16:]
        key_iv, prev = b"", b""
        while len(key_iv) < 48:
            prev = hashlib.md5(prev + password.encode('utf-8') + salt).digest()
            key_iv += prev
        key, iv = key_iv[:32], key_iv[32:48]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(ciphertext)
        return unpad(decrypted_padded, AES.block_size).decode('utf-8').strip('"').strip("'")
    except: return None

def generate_secure_token(url: str, secret_key: str = "csplayer_secret_2026", valid_hours: int = 2) -> str:
    expiry_time = int(time.time()) + (valid_hours * 3600)
    path = urlparse(url).path
    token = hmac.new(secret_key.encode(), f"{path}:{expiry_time}".encode(), hashlib.sha256).hexdigest()
    return f"{url}&token={token}&expires={expiry_time}" if "?" in url else f"{url}?token={token}&expires={expiry_time}"

def bypass_drive_link(url: str) -> str:
    headers = {"Referer": CINESUBZ_BASE_URL}
    try:
        response = scraper.get(url, headers=headers, allow_redirects=True, stream=True, timeout=15)
        final_url = response.url
        response.close()
        return final_url
    except Exception as e:
        return f"Error resolving link: {str(e)}"

# ==========================================
# 2. Utility Endpoints
# ==========================================
@app.get("/api/token/generate")
def create_token(url: str = Query(..., description="The MP4 URL to generate a token for")):
    try:
        return {"status": True, "original_url": url, "secured_url": generate_secure_token(url), "message": "Token generated"}
    except Exception as e:
        return {"status": False, "message": str(e)}

@app.get("/api/cinesubz/get-direct-stream")
def get_direct_stream(url: str = Query(..., description="The drive.csplayer link to bypass")):
    try:
        bypassed_link = bypass_drive_link(url)
        if "Error" in bypassed_link: return {"status": False, "message": bypassed_link}
        return {"status": True, "original_url": url, "bypassed_direct_url": bypassed_link, "message": "Link successfully bypassed!"}
    except Exception as e:
        return {"status": False, "message": str(e)}

# ==========================================
# 3. Main Scraper Endpoints
# ==========================================
@app.get("/api/cinesubz/search")
def search_movies(query: str = Query(..., description="Movie name to search")):
    try:
        search_url = f"{CINESUBZ_BASE_URL}?s={quote(query)}"
        response = scraper.get(search_url, headers={"Referer": CINESUBZ_BASE_URL})
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        all_results, movies, tvshows = [], [], []
        
        for item in soup.find_all('div', class_='display-item'):
            a_tag, img_tag, imdb_tag = item.find('a', href=True), item.find('img'), item.find('span', class_='imdb-score')
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
                    if media_type == "Movie": movies.append(result_obj)
                    else: tvshows.append(result_obj)
                        
        return {"author": "@DasunNethsara", "status": True, "data": {"all": all_results, "movies": movies, "tvshows": tvshows}}
    except Exception as e:
        return {"status": False, "author": "@DasunNethsara", "message": str(e)}

@app.get("/api/cinesubz/movie")
def get_movie_details(url: str = Query(..., description="Movie page URL (e.g., https://cinesubz.co/movie-name/)")):
    try:
        response = scraper.get(url, headers={"Referer": CINESUBZ_BASE_URL})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_element = soup.find('h1')
        title = title_element.text.strip() if title_element else "Unknown Title"
        
        # ඔබ වැරදීමකින් Download link එකක් දුන්නොත් එය හඳුනාගෙන පණිවිඩයක් දීමට
        if "Please Enable JavaScript" in title or "api-" in url:
            return {"author": "@DasunNethsara", "status": False, "message": "කරුණාකර මෙතනට චිත්‍රපටයේ ප්‍රධාන පිටුවේ (Movie Page) ලින්ක් එක ලබා දෙන්න. ඩවුන්ලෝඩ් ලින්ක් ලබා නොදෙන්න."}

        year = re.search(r'\((\d{4})\)', title).group(1) if re.search(r'\((\d{4})\)', title) else ""
        maintitle = re.sub(r'Sinhala Subtitles.*|සිංහල උපසිරැසි සමඟ.*', '', title).strip()
        
        images = [img.get('data-src') or img.get('src') for img in soup.find_all('img') if (img.get('data-src') or img.get('src')) and 'logo' not in (img.get('data-src') or img.get('src')).lower()]
        images = list(dict.fromkeys(filter(None, images)))
        main_image = images[0] if images else ""
        
        country, runtime, imdb_val = "", "", ""
        category = list(dict.fromkeys([a.text.strip() for a in soup.find_all('a', rel='category tag') if a.text.strip()]))
        
        for text_el in soup.stripped_strings:
            if 'IMDb:' in text_el: imdb_val = text_el.replace('IMDb:', '').strip()
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
        for btn in soup.find_all('a', class_='movie-download-button'):
            href = btn.get('href', '')
            meta_text = btn.find('span', class_='movie-download-meta').text if btn.find('span', class_='movie-download-meta') else ""
            parts = [p.strip() for p in meta_text.split('•')]
            quality, size, language = (parts[0] if len(parts) > 0 else "Unknown"), (parts[1] if len(parts) > 1 else "Unknown"), (parts[2] if len(parts) > 2 else "Unknown")
            
            actual_link = href
            if 'google.com' in actual_link: actual_link = actual_link.replace('google.com', 'drive.csplayer2.space')
            if actual_link.endswith('.mp4') and 'drive.csplayer2.space' in actual_link: actual_link = actual_link[:-4] + '?ext=mp4'
            if not any(d['link'] == actual_link for d in download_urls):
                download_urls.append({"quality": quality, "size": size, "language": language, "link": actual_link})

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
    try:
        file_title = unquote(url.split('/')[-1]).split('?ext=')[0]
        if "google.com" in url: url = url.replace("google.com", "drive.csplayer2.space")

        response = scraper.get(url, headers={"Referer": CINESUBZ_BASE_URL}, timeout=15)
        if response.status_code == 404: return {"author": "@DarkYasiya", "status": False, "message": "වීඩියෝව ඉවත් කර ඇත."}
        html = response.text
        
        file_size = re.search(r'(\d+(?:\.\d+)?\s*(?:MB|GB))', html, re.IGNORECASE).group(1) if re.search(r'(\d+(?:\.\d+)?\s*(?:MB|GB))', html, re.IGNORECASE) else "Unknown Size"
        actual_urls = []
        
        for api in re.findall(r'action="([^"]+)"', html):
            if '/api/source' in api or '/token' in api:
                bypass_url = api if api.startswith('http') else f"https://{urlparse(url).netloc}{api}"
                try:
                    res = scraper.post(bypass_url, headers={"X-Requested-With": "XMLHttpRequest", "Referer": url})
                    if res.status_code == 200 and 'data' in res.json():
                        bypass_link = res.json()['data']
                        if not any(d['url'] == bypass_link for d in actual_urls): actual_urls.append({"url": bypass_link})
                except: pass
        
        for hex_str in re.findall(r'([a-fA-F0-9]{150,})', html):
            try:
                res_text = scraper.post(url, headers={"Content-Type": "application/octet-stream"}, data=bytes.fromhex(hex_str), timeout=10).content.decode(errors='ignore')
                for enc_text in re.findall(r'(U2FsdGVkX1[a-zA-Z0-9\/\+]+={0,2})', res_text):
                    dec_url = decrypt_cinesubz_link(enc_text)
                    if dec_url and ('http' in dec_url or '.mp4' in dec_url):
                        if "google.com" in dec_url: dec_url = dec_url.replace("google.com", "drive.csplayer2.space")
                        if not any(d['url'] == dec_url for d in actual_urls): actual_urls.append({"url": dec_url})
            except: pass

        for enc_text in re.findall(r'(U2FsdGVkX1[a-zA-Z0-9\/\+]+={0,2})', html):
            dec_url = decrypt_cinesubz_link(enc_text)
            if dec_url and ('http' in dec_url or '.mp4' in dec_url):
                if "google.com" in dec_url: dec_url = dec_url.replace("google.com", "drive.csplayer2.space")
                if not any(d['url'] == dec_url for d in actual_urls): actual_urls.append({"url": dec_url})
        
        for tg in re.findall(r'(https?://(?:t\.me|telegram\.me)/[a-zA-Z0-9_]+\?start=[a-zA-Z0-9_]+)', html):
            if not any(d['url'] == tg for d in actual_urls): actual_urls.append({"url": tg})
                
        for dl in re.findall(r'(https?://[^\s"\'<>]+(?:token=[a-zA-Z0-9\.\-\_]+|\.mp4))', html):
            if ('token=' in dl or '.mp4' in dl) and 'cinesubz' not in dl.lower():
                if not any(d['url'] == dl for d in actual_urls): actual_urls.append({"url": dl})
                    
        return {"author": "@DarkYasiya", "status": True, "data": {"title": file_title, "size": file_size, "downloadUrls": actual_urls}}
    except Exception as e:
        return {"status": False, "author": "@DarkYasiya", "message": f"Error: {str(e)}"}
