from fastapi import FastAPI, Query
import requests
from bs4ational import BeautifulSoup

# API එක ආරම්භ කිරීම - CineSubz Scraper API (Developer: Dasun Nethsara)
app = FastAPI(title="CineSubz Scraper API", description="Scrape search results and direct download links from CineSubz")
BASE_URL = "https://cinesubz.net/"

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the CineSubz Scraper API!",
        "developer": "Dasun Nethsara",
        "status": "Running smoothly 🚀"
    }

@app.get("/api/cinesubz/search")
def search_movies(query: str = Query(..., description="Movie name to search")):
    """CineSubz වෙබ් අඩවිය තුළ චිත්‍රපට සෙවීම සහ ප්‍රතිඵල ලබා දීම."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": BASE_URL
        }
        
        # CineSubz සෙවුම් URL එක සකස් කිරීම
        search_url = f"{BASE_URL}?s={query}"
        
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # WordPress post හෝ article අඩංගු විවිධ elements සෙවීම
        items = soup.find_all(['article', 'div'], class_=lambda x: x and ('post' in x or 'item' in x or 'ittl' in x or 'search-item' in x))
        
        if not items:
            # වෙනත් ටැග්ස් මගින් උත්සාහ කිරීම (Fallback)
            items = soup.find_all('div', class_='result-item') or soup.find_all('article')

        for item in items:
            title_tag = item.find(['h2', 'h3', 'a'], class_=['title', 'tit']) or item.find('a')
            link_tag = item.find('a')
            img_tag = item.find('img')
            
            if link_tag and title_tag:
                title = title_tag.text.strip()
                link = link_tag.get('href')
                
                # පින්තූරය ලබා ගැනීම (lazy load images හැසිරවීම)
                image = None
                if img_tag:
                    image = img_tag.get('data-src') or img_tag.get('src') or img_tag.get('data-lazy-src')
                
                if title and link and link.startswith('http'):
                    # ඩුප්ලිකට් ලින්ක්ස් වැළැක්වීම
                    if not any(r['link'] == link for r in results):
                        results.append({
                            "title": title,
                            "link": link,
                            "image": image
                        })
                        
        return {
            "status": "success", 
            "query": query, 
            "total": len(results), 
            "data": results
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/cinesubz/movie")
def get_movie_download_links(url: str = Query(..., description="Movie page URL from search results")):
    """
    Search ප්‍රතිඵලයෙන් ලැබෙන ලින්ක් එක (URL) ලබා දී, 
    එහි ඇති ඩවුන්ලෝඩ් ලින්ක්ස් සහ විස්තර ලබා ගනී.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": BASE_URL
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # චිත්‍රපටයේ නම ලබා ගැනීම
        title_element = soup.find('h1')
        title = title_element.text.strip() if title_element else "Unknown Movie"
        
        download_links = []
        
        # ඩවුන්ලෝඩ් ලින්ක්ස් සෙවීම
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href')
            text = a_tag.text.strip()
            
            if href and href.startswith('http'):
                ignored_domains = ['facebook.com', 't.me', 'telegram.me', 'whatsapp.com', 'twitter.com', '#', 'instagram.com']
                if not any(domain in href for domain in ignored_domains):
                    # ඩවුන්ලෝඩ් හෝ ක්වොලිටි ආශ්‍රිත වචන තිබේදැයි පරීක්ෂා කිරීම
                    keywords = ['download', '1080p', '720p', '480p', 'pixeldrain', 'gofile', 'mega', 'zippy', 'drive']
                    if any(kw in text.lower() or kw in href.lower() for kw in keywords):
                        if not any(d['url'] == href for d in download_links):
                            download_links.append({
                                "quality_or_label": text if text else "Download Link",
                                "url": href
                            })
                            
        # කිසිදු ලින්ක් එකක් හමු නොවූ නම් බොත්තම් (buttons) පරීක්ෂා කිරීම
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
