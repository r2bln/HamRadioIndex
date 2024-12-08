from bs4 import BeautifulSoup
from markdown import Markdown
from urllib.parse import urlparse
import concurrent.futures
import requests
import sys, os

def extract_urls_from_markdown(file_path):
    """Извлекает URL из Markdown файла."""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Конвертируем Markdown в HTML
    md = Markdown()
    html = md.convert(content)
    
    # Используем BeautifulSoup для парсинга HTML
    soup = BeautifulSoup(html, 'html.parser')
    
    # Находим все ссылки
    urls = []
    for link in soup.find_all('a'):
        url = link.get('href')
        if url and (url.startswith('http://') or url.startswith('https://')):
            urls.append(url)
    
    return urls

def check_url(url):
    """Проверяет доступность URL."""
    try:
        response = requests.get(
            url, 
            timeout=10, 
            allow_redirects=True, 
            headers={ 
                "Content-Type": "text/html; charset=utf-8", 
                "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0'
            }
        )
        status = response.status_code
        return {
            'url': url,
            'status': status,
            'available': 200 <= status < 400 or status == 403 # ignore cloudflare forbid for now
        }
    except requests.RequestException as e:
        return {
            'url': url,
            'status': str(e),
            'available': False
        }

def main(markdown_file):
    # Извлекаем URLs
    print("Извлечение URLs из файла...")
    urls = extract_urls_from_markdown(markdown_file)
    print(f"Найдено {len(urls)} уникальных URLs")
    
    # Проверяем URLs параллельно
    print("\nПроверка доступности URLs...")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(check_url, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            results.append(future.result())
    
    # Выводим результаты
    print("\nРезультаты проверки:")
    print("-" * 80)
    
    # Сортируем результаты: сначала доступные, потом недоступные
    results.sort(key=lambda x: (not x['available'], x['url']))
    
    for result in results:
        status = "✅" if result['available'] else "❌"
        print(f"{status} {result['url']}")
        print(f"   Статус: {result['status']}")
        print("-" * 80)
    
    # Статистика
    available = sum(1 for r in results if r['available'])
    print(f"\nСтатистика:")
    print(f"Всего URLs: {len(results)}")
    print(f"Доступны: {available}")
    print(f"Недоступны: {len(results) - available}")

    if len(results) - available > 0:
        return sys.exit(1)
    return sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1])