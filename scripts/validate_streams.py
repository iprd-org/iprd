import json
import requests
import concurrent.futures
import time

def check_stream(stream):
    url = stream['url']
    try:
        start = time.time()
        # Timeout court pour vérifier que le flux répond
        response = requests.head(url, timeout=10, 
                                 headers={'User-Agent': 'IPRD-Validator/1.0'})
        latency = time.time() - start
        
        return {
            'url': url,
            'status': response.status_code,
            'working': 200 <= response.status_code < 400,
            'latency': round(latency, 2)
        }
    except Exception as e:
        return {
            'url': url,
            'status': 0,
            'working': False,
            'error': str(e)
        }

def main():
    # Chargement du catalogue
    with open('metadata/catalog.json', 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    results = {
        'total': 0,
        'working': 0,
        'failed': 0,
        'details': []
    }
    
    streams_to_check = []
    for station in catalog['stations']:
        for stream in station['streams']:
            stream_info = {
                'url': stream['url'],
                'station': station['name'],
                'country': station['country']
            }
            streams_to_check.append(stream_info)
    
    # Vérification en parallèle
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for stream in streams_to_check:
            futures.append(executor.submit(check_stream, stream))
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results['total'] += 1
            if result['working']:
                results['working'] += 1
            else:
                results['failed'] += 1
            results['details'].append(result)
    
    # Sauvegarde des résultats
    with open('validation-results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'summary': f"{results['working']}/{results['total']} flux fonctionnels ({results['failed']} échecs)",
            'details': results['details']
        }, f, indent=2)

if __name__ == "__main__":
    main()