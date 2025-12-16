import time
import random
import pandas as pd
import undetected_chromedriver as uc
from pyquery import PyQuery as pq
from selenium.webdriver.common.by import By

# ==============================================================================
# CONFIGURACIÓN: CABECERAS Y COOKIES (Del CURL proporcionado)
# ==============================================================================

HEADERS = {
    "accept-language": "es,en;q=0.9,ca;q=0.8",
    "dnt": "1",
    "priority": "u=0, i",
    "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1"
}

# Cookie 'datadome' es crítica. Si te bloquean, actualiza este string con una nueva cookie de tu navegador.
COOKIE_STRING = "PARAGLIDE_LOCALE=es; uppar=false; didomi_token=eyJ1c2VyX2lkIjoiMTlhOTM3ODktM2U1ZS02YmFmLTk2MmUtYzNlMTM1YzJkN2VjIiwiY3JlYXRlZCI6IjIwMjUtMTEtMTdUMjA6MTk6MDQuMjkzWiIsInVwZGF0ZWQiOiIyMDI1LTExLTE3VDIwOjE5OjA5Ljc4MFoiLCJ2ZW5kb3JzIjp7ImVuYWJsZWQiOlsiZ29vZ2xlIiwiYzpob3RqYXIiLCJjOmxpbmtlZGluLW1hcmtldGluZy1zb2x1dGlvbnMiLCJjOm1pY3Jvc29mdC1XblVHa0VqWiIsImM6Z29vZ2xlYW5hLTRUWG5KaWdSIiwiYzptaXhwYW5lbCIsImM6YWJ0YXN0eS1MTGtFQ0NqOCIsImM6YmVhbWVyLUg3dHI3SGl4IiwiYzp0ZWFsaXVtY28tRFZEQ2Q4WlAiLCJjOnRpa3Rvay1LWkFVUUxaOSIsImM6aWRlYWxpc3RhLUx6dEJlcUUzIiwiYzppZGVhbGlzdGEtZmVSRWplMmMiLCJjOm1pY3Jvc29mdCJdfSwicHVycG9zZXMiOnsiZW5hYmxlZCI6WyJnZW9sb2NhdGlvbl9kYXRhIiwiZGV2aWNlX2NoYXJhY3RlcmlzdGljcyJdfSwidmVyc2lvbiI6MiwiYWMiOiJDaEdBRUFGa0ZDSUEuQUFBQSJ9; euconsent-v2=CQbB_cAQbB_cAAHABBENCFFsAP_gAAAAAAAAHXwCAAIAAqABaAFsAUgBZgF5gOvAAAAKSgAwABBd8pABgACC75CADAAEF3x0AGAAILvhIAMAAQXf.f_wAAAAAAAAA; datadome=pE1UnZ06urwQ73RKwv~Y20hIQ3bCJq82wBJEg1~gqja3pnOgQn7xsMafy4TrAy6dSYxqoHquou10Q79AXBX3DTjbUmUhR5bCMqKOaPRu0o_MT_M8iLjwMP~NAEHbBoBF"

# ==============================================================================
# FUNCIÓN DE PARSEO (EXTRACCIÓN DE DATOS)
# ==============================================================================

def parse_items(html_content):
    """Analiza el HTML y devuelve una lista de diccionarios con los datos de los pisos."""
    d = pq(html_content)
    items = d("article.item")
    data_list = []

    for item in items.items():
        try:
            # 1. Datos básicos
            listing_id = item.attr("data-element-id")
            title = item.find("a.item-link").text()
            link_href = item.find("a.item-link").attr("href")
            full_link = f"https://www.idealista.com{link_href}" if link_href else None

            # 2. Precio
            raw_price = item.find("span.item-price").text()
            price = None
            if raw_price:
                # Limpiar "261.000€" -> 261000
                clean_p = raw_price.replace(".", "").replace("€", "").strip()
                if clean_p.isdigit():
                    price = int(clean_p)

            # 3. Características (Habitaciones, m2, Planta)
            details = item.find("span.item-detail")
            rooms, area, floor, exterior, elevator = None, None, None, None, None
            
            for detail in details.items():
                txt = detail.text().strip()
                if "hab." in txt:
                    rooms = txt.replace("hab.", "").strip()
                elif "m²" in txt:
                    area = txt.replace("m²", "").strip().replace(".", "")
                elif "Planta" in txt or "Bajo" in txt or "Entreplanta" in txt:
                    floor = txt
                    if "exterior" in txt.lower(): exterior = "Exterior"
                    elif "interior" in txt.lower(): exterior = "Interior"
                    if "con ascensor" in txt.lower(): elevator = "Sí"
                    elif "sin ascensor" in txt.lower(): elevator = "No"

            # 4. Extras
            parking = "Sí" if item.find("span.item-parking") else "No"
            description = item.find(".item-description p").text()
            
            # Agencia / Particular
            agency = item.find("picture.logo-branding img").attr("alt")
            if not agency:
                agency = item.find("span.item-seller").text()
            if not agency:
                agency = "Particular / Desconocido"

            # 5. Guardar en diccionario
            row = {
                "ID": listing_id,
                "Título": title,
                "Precio": price,
                "Habitaciones": int(rooms) if rooms and rooms.isdigit() else rooms,
                "Metros_Cuadrados": int(area) if area and area.isdigit() else area,
                "Planta_Descripcion": floor,
                "Exterior": exterior,
                "Ascensor": elevator,
                "Parking": parking,
                "Agencia": agency,
                "Enlace": full_link,
                "Descripción": description
            }
            data_list.append(row)

        except Exception as e:
            print(f"Error parseando un item: {e}")
            continue

    return data_list

# ==============================================================================
# SCRIPT PRINCIPAL
# ==============================================================================

def run_scraper():
    # Configuración del navegador indetectable
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    
    print("🚀 Iniciando navegador...")
    driver = uc.Chrome(options=options)

    # Inyección de Cabeceras (CDP)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': HEADERS})

    base_url = 'https://www.idealista.com/venta-viviendas/gijon-asturias/con-solo-pisos/' # 'https://www.idealista.com/venta-viviendas/gijon/centro/'
    all_properties = []

    try:
        # 1. Inyectar Cookies (requiere ir al dominio primero)
        print("🍪 Inyectando cookies de sesión...")
        driver.get("https://www.idealista.com")
        
        for c in COOKIE_STRING.split('; '):
            if '=' in c:
                name, value = c.split('=', 1)
                try:
                    driver.add_cookie({'name': name, 'value': value, 'domain': '.idealista.com'})
                except:
                    pass
        
        time.sleep(2)

        # 2. Bucle por páginas
        for page in range(1, 35):
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}pagina-{page}.htm"

            print(f"\n📄 Navegando a página {page}...")
            driver.get(url)

            # Scroll humano aleatorio
            scrolls = random.randint(3, 5)
            for _ in range(scrolls):
                driver.execute_script(f"window.scrollBy(0, {random.randint(400, 800)});")
                time.sleep(random.uniform(0.8, 1.5))

            # Espera para carga completa
            time.sleep(random.uniform(2, 4))

            # Obtener HTML
            html = driver.page_source
            
            # Chequeo de seguridad
            if "verifying you are human" in html.lower():
                print("⚠️  BLOQUEO DETECTADO: Resuelve el CAPTCHA manualmente en el navegador.")
                print("    El script esperará 30 segundos...")
                time.sleep(30)
                html = driver.page_source # Recargar html tras resolver

            # Extraer datos
            page_data = parse_items(html)
            count = len(page_data)
            print(f"✅ Encontrados {count} anuncios en página {page}.")
            
            if count == 0:
                print("⚠️  No se encontraron anuncios (posible fin de lista o bloqueo fuerte).")
                # Opcional: break si crees que es fin de lista
            
            all_properties.extend(page_data)

    except Exception as e:
        print(f"❌ Error fatal: {e}")
    finally:
        print("🛑 Cerrando navegador...")
        driver.quit()

        # 3. Guardar resultados
        if all_properties:
            print(f"\n💾 Guardando {len(all_properties)} registros en Excel...")
            df = pd.DataFrame(all_properties)
            
            # Guardar a Excel
            filename = "idealista_gijon_centro.xlsx"
            df.to_excel(filename, index=False)
            print(f"🎉 ¡Éxito! Archivo generado: {filename}")
            
            # Previsualización
            print(df[["Título", "Precio", "Agencia"]].head())
        else:
            print("☹️ No se extrajeron datos.")

if __name__ == "__main__":
    run_scraper()