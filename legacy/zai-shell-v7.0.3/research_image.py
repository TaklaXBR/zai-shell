import os
import base64
import re
import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from colorama import Fore, Style

SUPPORTED_IMAGE_FORMATS = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']


class WebResearchEngine:
    """DuckDuckGo web research engine using official library"""
    
    def __init__(self):
        self.max_results = 8
        self.is_available_flag = DDGS_AVAILABLE or (REQUESTS_AVAILABLE and BS4_AVAILABLE)
        self.ai_model = None
    
    def set_ai_model(self, model):
        """Set AI model for query optimization"""
        self.ai_model = model
    
    def is_available(self) -> bool:
        """Check if web research is available"""
        return self.is_available_flag
    
    def get_current_date(self) -> str:
        """Get current date for context"""
        now = datetime.datetime.now()
        return now.strftime("%Y-%m-%d")
    
    def optimize_query(self, user_query: str) -> str:
        """Use AI to extract optimal English search keywords with date context"""
        if not self.ai_model:
            return user_query
        
        current_date = self.get_current_date()
        current_year = datetime.datetime.now().year
        
        try:
            prompt = f"""You are a search query optimizer. Convert user query to the BEST English search keywords.
Current Date: {current_date}
User query: "{user_query}"

CRITICAL RULES:
1. Identify the core topic.
2. If the user asks for SOFTWARE VERSIONS or DOWNLOADS:
   - MUST append "official site" or "official release notes".
   - Do NOT aggressively add the year "{current_year}" unless it's a news topic. Official download pages often don't have the year in the title.
3. If the user asks for specific technical errors, keep the error code exactly.
4. If asking about current news/events, add "{current_year}".
5. Output ONLY the keywords, 2-6 words max.

Examples:
- "python son sürümü kaç" -> "python latest version official site"
- "en yeni iphone" -> "iphone latest model specs {current_year}"
- "react kurulumu" -> "react install official documentation"
- "nodejs nasıl kurulur" -> "nodejs install tutorial official"
- "how to fix error 404" -> "fix error 404 guide"
- "bugün dolar kuru" -> "dollar exchange rate {current_year}"

Return ONLY the optimized search keywords."""

            response = self.ai_model.generate_content(prompt)
            optimized = response.text.strip().strip('"').strip("'")
            if optimized and len(optimized) < 100:
                return optimized
        except:
            pass
        
        return user_query
    
    def search(self, query: str) -> List[Dict]:
        """Perform DuckDuckGo search"""
        
        if DDGS_AVAILABLE:
            try:
                with DDGS() as ddgs:
                    results = []
                    for r in ddgs.text(query, region='wt-wt', safesearch='off', max_results=self.max_results):
                        results.append({
                            "title": r.get("title", ""),
                            "snippet": r.get("body", ""),
                            "url": r.get("href", "")
                        })
                    return results
            except Exception as e:
                print(f"{Fore.YELLOW}DDGS search error: {e}{Style.RESET_ALL}")
        
        if REQUESTS_AVAILABLE and BS4_AVAILABLE:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
                
                response = requests.get(search_url, headers=headers, timeout=10)
                if response.status_code != 200:
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                for result in soup.select('.result')[:self.max_results]:
                    title_elem = result.select_one('.result__title')
                    snippet_elem = result.select_one('.result__snippet')
                    link_elem = result.select_one('.result__url')
                    
                    if title_elem:
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                            "url": link_elem.get_text(strip=True) if link_elem else ""
                        })
                
                return results
                
            except Exception as e:
                print(f"{Fore.YELLOW}Web search error: {e}{Style.RESET_ALL}")
        
        return []
    
    def format_results_for_ai(self, results: List[Dict], query: str) -> str:
        """Format search results for AI consumption with emphasis on accurate data extraction"""
        if not results:
            return f"No results found for: {query}"
        
        current_date = self.get_current_date()
        
        formatted = f"""CRITICAL INSTRUCTION: You MUST answer based on the web search results below.
Do NOT say "analyzing" or "searching" - provide the ACTUAL DATA from results.

Today's Date: {current_date}
User Question: "{query}"

=== WEB SEARCH RESULTS ==="""
        
        for i, r in enumerate(results, 1):
            formatted += f"\n\n{i}. {r['title']}"
            formatted += f"\n   URL: {r['url']}"
            formatted += f"\n   Content: {r['snippet']}"
        
        formatted += f"""

=== YOUR TASK ===
1. Evaluate which sources are most RELIABLE for this specific topic
2. Extract SPECIFIC information (exact version numbers, dates, prices, etc.)
3. If sources conflict, prefer official/authoritative sources for that topic
4. Answer in the user's language (detect from query)
5. Be DIRECT and SPECIFIC - no vague responses like "analyzing..."
6. Cite which source you got the information from

NOW ANSWER THE USER'S QUESTION WITH SPECIFIC DATA FROM THE RESULTS:"""
        return formatted
    
    def print_results_to_user(self, results: List[Dict], query: str):
        """Print formatted results to console for user to see"""
        print(f"\n{Fore.CYAN}Web Search Results for '{query}':{Style.RESET_ALL}\n")
        for i, r in enumerate(results, 1):
            print(f"{Fore.GREEN}{i}. {r['title']}{Style.RESET_ALL}")
            print(f"   {Fore.BLUE}{r['url']}{Style.RESET_ALL}")
            print(f"   {r['snippet'][:150]}...\n")


class ImageAnalyzer:
    """Image file analyzer using Gemini Vision"""
    
    def __init__(self):
        self.model = None
        self.is_available_flag = PIL_AVAILABLE
    
    def _init_model(self):
        """Lazy initialize the model"""
        if self.model is None:
            self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported"""
        ext = Path(file_path).suffix.lower().lstrip('.')
        return ext in SUPPORTED_IMAGE_FORMATS
    
    def encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """Encode image file to base64"""
        if not self.is_available_flag:
            return None
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"{Fore.RED}Image encoding error: {e}{Style.RESET_ALL}")
            return None
    
    def analyze_image(self, image_path: str, context: str = None) -> Dict:
        """Analyze image and return structured analysis"""
        self._init_model()
        
        if not os.path.exists(image_path):
            return {"success": False, "error": f"File not found: {image_path}"}
        
        if not self.is_supported_format(image_path):
            return {"success": False, "error": f"Unsupported format. Supported: {SUPPORTED_IMAGE_FORMATS}"}
        
        try:
            img_data = self.encode_image_to_base64(image_path)
            if not img_data:
                return {"success": False, "error": "Failed to encode image"}
            
            ext = Path(image_path).suffix.lower().lstrip('.')
            mime_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
            
            prompt = """Analyze this image in detail. 
If it's an error screenshot, identify:
1. Error type and message
2. Possible causes
3. Suggested solutions

If it's a general image, describe:
1. Main content
2. Text visible (if any)
3. Key elements

Respond in a structured format."""
            
            if context:
                prompt = f"Context: {context}\n\n{prompt}"
            
            response = self.model.generate_content([
                prompt,
                {"mime_type": mime_type, "data": img_data}
            ])
            
            return {
                "success": True,
                "analysis": response.text,
                "file": image_path
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_error_screenshot(self, image_path: str) -> Dict:
        """Specialized analysis for error screenshots"""
        return self.analyze_image(image_path, context="This is an error screenshot. Focus on identifying the error and providing solutions.")
