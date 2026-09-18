from fastapi import FastAPI, Query
import requests
from bs4 import BeautifulSoup

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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        search_url = f"{BASE_URL}?s={query}"
        
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for article in soup.find_all(['article', 'div'], class_=['post', 'item', 'ittl']):
            title_tag = article.find(['h2', 'h3', 'a'])
            link_tag = article.find('a')
            img_tag = article.find('img')
            
            if link_tag and title_tag:
                title = title_tag.text.strip()
                link = link_tag.get('href')
                image = img_tag.get('data-src') or img_tag.get('src') if img_tag else None
                
                if title and link and link.startswith('http'):
                    if not any(r['link'] == link for r in results):
                        results.append({
                            "title": title,
                            "link": link,
                            "image": image
                        })
                        
        return {"status": "success", "query": query, "total": len(results), "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/cinesubz/movie")
def get_movie_download_links(url: str = Query(..., description="Movie page URL from search results")):
    """
    Search ප්‍රතිඵලයෙන් ලැබෙන ලින්ක් එක (URL) ලබා දී, 
    එහි ඇති ඩවුන්ලෝඩ් ලින්ක්ස් සහ විස්තර ලබා ගනී.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # චිත්‍රපටයේ නම ලබා ගැනීම
        title_element = soup.find('h1')
        title = title_element.text.strip() if title_element else "Unknown Movie"
        
        # ඩවුන්ලෝඩ් ලින්ක්ස් අඩංගු ප්‍රදේශය සෙවීම
        download_links = []
        
        # CineSubz වල ඩවුන්ලෝඩ් ලින්ක්ස් තියෙන ටැග්ස් හෝ බොත්තම් සෙවීම
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href')
            text = a_tag.text.strip()
            
            if href and href.startswith('http'):
                # Social media, ads සහ වෙනත් නුසුදුසු ලින්ක්ස් පෙරීම (Filter out)
                ignored_domains = ['facebook.com', 't.me', 'telegram.me', 'whatsapp.com', 'twitter.com', '#']
                if not any(domain in href for domain in ignored_domains):
                    # ලින්ක් එකේ text එක හෝ URL එක ඇතුළේ download/mega/gdrive/zippyshare වැනි දේ තිබේදැයි බැලීම
                    if 'download' in text.lower() or '1080p' in text.lower() or '720p' in text.lower() or '480p' in text.lower() or 'pixeldrain' in href.lower() or 'gofile' in href.lower():
                        if not any(d['url'] == href for d in download_links):
                            download_links.append({
                                "quality_or_label": text,
                                "url": href
                            })
                            
        # යම් හෙයකින් ඉහත පෙරීමෙන් ලින්ක්ස් හමු නොවූ නම්, පිටුවේ ඇති ප්‍රධාන ඩවුන්ලෝඩ් ලින්ක්ස් සියල්ල ලබා දීම
        if not download_links:
            for a_tag in soup.find_all('a', class_=['maxbutton', 'button', 'btn']):
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
