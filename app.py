import requests
from bs4 import BeautifulSoup
import json
from tqdm import tqdm

# Función para extraer datos de jugadores desde una URL de partido
def extraer_datos_jugadores(url):
    try:
        r = requests.get(url)

        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            tables = soup.find_all('table', class_='wf-table-inset mod-overview')

            data = []  # Lista para almacenar los datos de los jugadores

            for cont, table in enumerate(tables, start=1):  # Usar enumerate para contar
                if cont == 3:  # Limitar a las primeras 3 tablas
                    break

                # Obtener encabezados de la tabla
                headers = [th.get_text(strip=True) for th in table.select('thead th')]

                # Obtener datos de la tabla
                for row in table.select('tbody tr'):
                    player_data = {}
                    cells = row.select('td')

                    # Obtener el nombre del jugador
                    name = cells[0].select_one('a')
                    player_data['name'] = name.get_text(strip=True) if name else None

                    # Crear un diccionario con los datos del jugador
                    for i in range(1, len(headers)):  # Comenzar desde 1 para omitir el nombre
                        span_element = cells[i].select_one('span.side')
                        cell_value = span_element.get_text(strip=True) if span_element else None

                        # Verificar si cell_value es None antes de agregarlo
                        if cell_value:
                            field_name = headers[i]
                            # Cambiar el nombre del campo "+/\u2013" a "+/-"
                            field_name = "+/-" if field_name == "+/\u2013" else field_name
                            player_data[field_name] = cell_value

                    # Agregar solo si hay datos del jugador
                    if player_data:
                        data.append(player_data)

            return data
        else:
            print(f"Error al acceder a la URL: {url}, código de estado: {r.status_code}")
            return None

    except Exception as e:
        print(f"Ocurrió un error al extraer datos: {str(e)}")
        return None

# URL base de la página que contiene los datos de los partidos
base_url = "https://www.vlr.gg/matches/results"

# Diccionario para almacenar los datos de los partidos organizados por eventos
matches_by_event = {}
existing_links = set()

# Intentar cargar partidos existentes desde el archivo JSON
try:
    with open('matches_by_event.json', 'r', encoding='utf-8') as f:
        matches_by_event = json.load(f)

    # Crear un conjunto de enlaces existentes para facilitar la verificación
    existing_links = {match['link'] for event in matches_by_event.values() for match in event}
except FileNotFoundError:
    print("No se encontró el archivo 'matches_by_event.json'. Se crearán nuevos registros.")
except json.JSONDecodeError:
    print("Error al leer el archivo JSON. Puede estar corrupto o vacío.")

# Iterar a través de las páginas de resultados
page_number = 1
while page_number <= 67:  # Limitar a las primeras 67 páginas
    print(f"Extrayendo datos de la página {page_number}...")
    url = f"{base_url}/?page={page_number}"

    # Hacer una solicitud GET a la página
    response = requests.get(url)

    # Si la respuesta no es 200, se ha alcanzado el final de las páginas
    if response.status_code != 200:
        print("No se encontraron más páginas. Finalizando...")
        break

    # Analizar el contenido HTML de la página
    soup = BeautifulSoup(response.content, "html.parser")

    # Encontrar todos los partidos dentro de divs con la clase 'wf-card'
    match_cards = soup.find_all('div', class_='wf-card')
    if not match_cards:  # Si no hay más partidos en la página, terminar
        print("No se encontraron más partidos en la página. Finalizando...")
        break

    # Usar tqdm para la barra de progreso
    for card in tqdm(match_cards, desc="Extrayendo partidos"):
        # Encontrar todos los enlaces <a> dentro de cada wf-card
        match_links = card.find_all('a', href=True)

        for link_tag in match_links:
            match_info = {}
            
            # Extraer el enlace al partido
            match_info['link'] = "https://vlr.gg" + link_tag['href']

            # Verificar si el partido ya existe
            if match_info['link'] in existing_links:
                continue  # Si ya existe, saltar a la siguiente iteración
            
            # Extraer el tiempo del partido
            match_time = link_tag.find('div', class_='match-item-time')
            match_info['time'] = match_time.get_text(strip=True) if match_time else 'N/A'
            
            # Extraer los equipos
            teams = link_tag.find_all('div', class_='match-item-vs-team')
            if teams and len(teams) == 2:
                match_info['team_1'] = teams[0].find('div', class_='match-item-vs-team-name').get_text(strip=True)
                match_info['team_2'] = teams[1].find('div', class_='match-item-vs-team-name').get_text(strip=True)

            # Extraer los puntajes
            scores = link_tag.find_all('div', class_='match-item-vs-team-score')
            if scores and len(scores) == 2:
                match_info['score_1'] = scores[0].get_text(strip=True)
                match_info['score_2'] = scores[1].get_text(strip=True)
            
            # Extraer el estado del partido
            match_status = link_tag.find('div', class_='ml-status')
            match_info['status'] = match_status.get_text(strip=True) if match_status else 'N/A'
            
            # Extraer solo el nombre del evento (tournament) sin el contenido del sub-div
            event_info = link_tag.find('div', class_='match-item-event')
            
            # Verificar si event_info no es None antes de continuar
            if event_info is not None:
                event_name = event_info.get_text(strip=True) if event_info else 'N/A'
                
                # Quitar el contenido del sub-div 'match-item-event-series'
                event_series_info = event_info.find('div', class_='match-item-event-series')
                if event_series_info:
                    event_name = event_name.replace(event_series_info.get_text(strip=True), '').strip()

                match_info['event_series'] = event_series_info.get_text(strip=True) if event_series_info else 'N/A'
            else:
                match_info['event_series'] = 'N/A'
                event_name = 'N/A'

            # Extraer el ganador del partido
            if len(scores) == 2:
                score_1 = scores[0].get_text(strip=True)
                score_2 = scores[1].get_text(strip=True)

                # Extraer el ganador
                if score_1 > score_2:
                    match_info['winner'] = match_info['team_1']
                elif score_1 < score_2:
                    match_info['winner'] = match_info['team_2']
                else:
                    match_info['winner'] = 'Draw'
            else:
                match_info['score_1'] = 'N/A'
                match_info['score_2'] = 'N/A'
                match_info['winner'] = 'N/A'
            
            # Organizar partidos por evento
            if event_name not in matches_by_event:
                matches_by_event[event_name] = []

            # Agregar el nuevo partido al principio de la lista
            matches_by_event[event_name].insert(0, match_info)

            # Extraer datos de los jugadores del partido
            jugador_data = extraer_datos_jugadores(match_info['link'])
            if jugador_data:
                match_info['player_stats'] = jugador_data
            else:
                match_info['player_stats'] = []

    # Guardar los datos organizados en el archivo JSON después de procesar la página
    with open('matches_by_event.json', 'w', encoding='utf-8') as f:
        json.dump(matches_by_event, f, ensure_ascii=False, indent=4)

    print(f"Datos de la página {page_number} guardados en 'matches_by_event.json'.")

    # Aumentar el número de página
    page_number += 1

print("Todos los datos de partidos y estadísticas de jugadores han sido extraídos y organizados por eventos.")
