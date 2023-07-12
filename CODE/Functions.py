import pandas as pd
import numpy as np
import requests
import random
import re
import time
from bs4 import BeautifulSoup
from unidecode import unidecode
import pandas as pd
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression as LinReg
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn import metrics
from sklearn.linear_model import Ridge, Lasso
from sklearn.linear_model import SGDRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.preprocessing import LabelEncoder
from scipy.stats import trim_mean




# ------------------------------------  SCRAPPING ----------------------------------- #

def get_links(ini_pg, fin_pg):
    links = []
    user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15'
        ]
    
    for i in range(ini_pg*20, fin_pg*20, 20):
        headers = {'User-Agent': random.choice(user_agents)}
        url = f'https://www.boat24.com/en/secondhandboats/?page={i}'
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        boxes = list(soup.find_all('div', {'data-link': True}))
        for div in boxes:
            links.append(div['data-link'])
        i += 20

    return links


def get_id(url):
    id = int(url.split('/')[-2])
    return id

def get_full_info(df):
    list_dicts = []
    for index, row in df.iterrows():
        dict = {}
        dict['ID'] = row['ID']

        response = requests.get(row['LINK'])
        soup = BeautifulSoup(response.content, 'html.parser')
        
        try:
            title = soup.find('h2', class_='heading__title').text.strip()
            dict.update({'Model': title})
        except:
            print(row['ID'])
            pass
        
        try:
            type = soup.find('p', class_="heading__title-header")
            dict.update({'Type': type})
        except:
            print(row['ID'])
            pass

        try:
            div_location = soup.find_all('div', {'id': 'location'})
            p_location = div_location[0].find(class_='text').text.split(" ")[0].strip()
            dict.update({'location': p_location})
        except:
            print(row['ID'])
            pass

        try:
            p_price = soup.find_all('p', {'class': 'contact-box__price'})
            price = p_price[0].find('strong').text.strip()
            dict.update({'Price': price})
        except:
            print(row['ID'])
            pass
        
        try:
            div_specs = list(soup.find_all('div', {'id': 'specs'}))
            all_lis = div_specs[0].find_all('li')
            all_lis
            for li in all_lis:
                try:
                    key = li.find(class_='list__key').text.strip()
                    value = li.find(class_='list__value').text.strip()
                    dict.update({key:value})
                except:
                    pass
        except:
            print(row['ID'])
            pass
        
        try:
            div_description = soup.find('div', class_='content', attrs={'x-ref': 'translationContent'} )
            if div_description:
                description = div_description.text
                dict.update({'Description': description})
        except:
            print(row['ID'])
            pass

        dict['Link'] = row['LINK']
        
        list_dicts.append(dict)

    return pd.DataFrame(list_dicts)


# ------------------------------------  CLEANING ----------------------------------- #

def upper_columns(df):
    column_names_upper = df.columns.str.upper()
    df.columns = column_names_upper
    return df


def get_category(df):
    df['CATEGORY'] = ""
    #df['SUBCATEGORY'] = ""
    for index, row in df.iterrows():
        link = row['LINK']
        if 'catalog' not in link:
            df.at[index, 'CATEGORY'] = link.split('/')[4]
            #df.at[index, 'SUBCATEGORY'] = link.split('/')[5]
        else:
            df.at[index, 'CATEGORY'] = link.split('/')[5]
            #df.at[index, 'SUBCATEGORY'] = link.split('/')[6]

    non_wanted = ('engines', 'fibrafort', 'quicksilver', 'berths', 'trailers')
    df = df[~df['CATEGORY'].isin(non_wanted)]
    
    return df


def get_subcategory(df):
    df['SUBCATEGORY'] = ""

    for index, row in df.iterrows():
        boat_type = str(row['TYPE'])
        if 'title=' in boat_type:
            subcategory = boat_type.split('title=')[1].split('>')[0].strip()
        elif ',' in boat_type:
            subcategory = boat_type.split(',')[1].split('>')[0].strip()
        else:
            subcategory = 'UNKNOWN'
        
        subcategory = subcategory.replace('"', '').split('</p')[0].strip()
        
        df.at[index, 'SUBCATEGORY'] = subcategory
    
    return df


def get_price(df):
    columns_list = df.columns
    for i in columns_list:
        if 'VAT' in i:
            for row, value in enumerate(df[i]):
                try:
                    if pd.notna(value) and pd.isna(df.at[row, 'PRICE']):
                        df.at[row, 'PRICE'] = value
                except:
                    pass
    try:
        for row, value in enumerate(df['UNNAMED: 5']):
            if pd.notna(value) and pd.isna(df.at[row, 'PRICE']):
                df.at[row, 'PRICE'] = value
    except:
        pass

    try:
         for row, value in enumerate(df['STARTING PRICE']):
            if pd.notna(value) and pd.isna(df.at[row, 'PRICE']):
                df.at[row, 'PRICE'] = value
    except:
        pass
    
    df.drop(columns='UNNAMED: 5', inplace=True)
    
    return df


def get_euros(df):
    df['CURRENCY'] = ""
    df['PRICE_EUR'] = ""
    for index, row in df.iterrows():
        value = row['PRICE']
        if pd.notna(value) and any(char.isdigit() for char in value):
            df.at[index, 'CURRENCY'] = str(value.split(' ')[0].strip())
            df.at[index, 'PRICE_EUR'] = int(value.split(' ')[1].split(',')[0].replace('.', ''))
        else:
            df.at[index, 'CURRENCY'] = 'UNKNOWN'
            df.at[index, 'PRICE_EUR'] = ' UNKNOWN'
    
    exchange = {
        'EUR': 1,
        '€': 1,
        'CHF': 1.02,
        'DKK': 0.13,
        'USD': 0.92,
        '£': 1.16,
        'GDP': 1.16,
        'SEK': 0.085,
        'NOK': 0.085
    }

    for index, row in df.iterrows():
        currency = row['CURRENCY']
        price = row['PRICE_EUR']

        if currency in exchange:
            conversion_rate = exchange[currency]
            price_euros = price * conversion_rate
            df.at[index, 'PRICE_EUR'] = price_euros
        else:
            df.at[index, 'PRICE_EUR'] = 'UNKNOWN'

    df.drop(columns=['PRICE', 'CURRENCY'], inplace=True)
    
    return df
    

def check_nulls(df):
    columns_list = df.columns
    for i in columns_list:
        x = df[i].isna().sum()
        y = (df[i] == 'nan').sum()
        print(i)
        print(f'Number of nulls: {x+y} \n')


def drop_column_by_str(df, *args):
    columns_list = df.columns
    drop_columns = []
    
    for i in columns_list:
        for str in args:
            if str in i:
                drop_columns.append(i)

    df = df.drop(columns=drop_columns)
    
    return df


def drop_row_by_str(df, column_name, *values_list):
    for index, row in df.iterrows():
        for value in values_list:
            if value.lower() in str(row[column_name]).lower():
                df = df.drop(index)
                break
    return df


def get_condition_from_type(df):
    df['CONDITION'] = df['CONDITION'].str.upper()

    for index, value in df['CONDITION'].items():
        if pd.isna(value):
            if df.at[index, 'TYPE'] and re.search(r'New Boat', str(df.at[index, 'TYPE']), flags=re.IGNORECASE):
                df.at[index, 'CONDITION'] = 'NEW BOAT'
            elif df.at[index, 'TYPE'] and re.search(r'Used Boat', str(df.at[index, 'TYPE']), flags=re.IGNORECASE):
                df.at[index, 'CONDITION'] = 'USED BOAT'
            elif df.at[index, 'LINK'] and re.search(r'catalog', str(df.at[index, 'LINK']), flags=re.IGNORECASE):
                df.at[index, 'CONDITION'] = 'NEW BOAT'

    values_to_replace_used = ['GOOD CONDITION', 'VERY GOOD CONDITION', 'AS NEW', 'FAIR CONDITION', 'USED', 'IN NEED OF REPAIR', 'DAMAGED']
    values_to_replace_new = ['NEW']
    df['CONDITION'] = df['CONDITION'].replace(values_to_replace_used, 'USED BOAT')
    df['CONDITION'] = df['CONDITION'].replace(values_to_replace_new, 'NEW BOAT')

    return df


def get_lenght_beam(df):
    df['LENGTH (m)'] = ''
    df['BEAM (m)'] = ''

    for index, value in df['LENGTH X BEAM'].items():
        
        length_beam = str(value)
        
        if 'x' in length_beam:
            length, beam = length_beam.split('x')
            length = length.strip().split(' ')[0]
            beam = beam.strip().split(' ')[0]

            length = float(length) if length else 0.0
            beam = float(beam) if beam else 0.0
            df.at[index, 'LENGTH (m)'] = length
            df.at[index, 'BEAM (m)'] = beam
        
        else:
            df.at[index, 'LENGTH (m)'] = 'UNKNOWN'
            df.at[index, 'BEAM (m)'] = 'UNKNOWN'
    
    #df.drop(columns=['LENGTH X BEAM'], inplace=True)
    
    return df


def get_upper_values(df, *columns):
    for column in columns:
        df[column] = df[column].apply(lambda x: x.upper() if pd.notna(x) and isinstance(x, str) else x)
    
    return df


def convert_value_type(df, data_type, *columns):
    for column in columns:
        df[column] = df[column].apply(lambda x: data_type(x) if (pd.notna(x) and x != '') else (None if x == '' else x))
    return df


def get_year(df):
    for index, value in df['MODEL YEAR'].items():
        if pd.isna(df.at[index, 'YEAR BUILT']) and pd.notna(value):
            df.at[index, 'YEAR BUILT'] = int(value)
        elif pd.notna(df.at[index, 'YEAR BUILT']):
            df.at[index, 'YEAR BUILT'] = int(df.at[index, 'YEAR BUILT'])
    
    for index, value in df['CONDITION'].items():
        if value == 'NEW BOAT' and pd.notna(value):
            if pd.isna(df.at[index, 'YEAR BUILT']):
                df.at[index, 'YEAR BUILT'] = '2023'
    return df


def split_and_select_words(string):
    pattern = r"\d"
    matches = re.split(pattern, string, 1)
    
    if len(matches) > 1:
        words = matches[0].split()[:-1]
        return words
    
    elif len(matches) == 1:
        return words
    
    else:
        return None  # No digit found in the string


def get_manufacturer(df):
    manufacturers_list_1 = ['Abeking & Rasmussen',
 'Amels',
 'Astondoa',
 'Azimut',
 'Baglietto',
 'Baja',
 'Balt',
 'Bavaria',
 'Bayliner',
 'Beneteau',
 'Bertram',
 'Boston Whaler',
 'Cantiere delle Marche',
 'Carver',
 'Catalina',
 'Chaparral',
 'Cheoy Lee',
 'Chris-Craft',
 'Cigarette',
 'Cobalt',
 'Cobia',
 'Contender',
 'Correct Craft',
 'Cruisers',
 'Donzi',
 'Dufour',
 'Eliminator',
 'Everglades',
 'Fairline',
 'Ferretti',
 'Fjord',
 'Formula',
 'Fountain',
 'Fountaine Pajot',
 'Four Winns',
 'GALA',
 'Galeon',
 'Glastron',
 'Grady-White',
 'Grand Banks',
 'Hanse',
 'Hanseyachts',
 'Hatteras',
 'Heysea',
 'Hunter',
 'Intrepid',
 'Jeanneau',
 'Lagoon',
 'Larson',
 'Lürssen',
 'MTI',
 'Malibu',
 'Mangusta',
 'MasterCraft',
 'Monterey',
 'Nautique',
 "Nautor's Swan",
 'Neptunus',
 'Nitro',
 'Nor-Tech',
 'Nordhavn',
 'Numarine',
 'Outerlimits',
 'Oyster',
 'Palm Beach',
 'Pershing',
 'Prestige',
 'Princess',
 'Ranger',
 'Regal',
 'Regulator Marine',
 'Rinker',
 'Riva',
 'Robalo',
 'Sanlorenzo',
 'Scout',
 'Sea Ray',
 'Sealine',
 'Sessa Marine',
 'Silverton',
 'Skeeter',
 'Sunseeker',
 'Tiara',
 'Tracker',
 'Viking',
 'Wally',
 'Westport',
 'X-Yacht',
 'Yellowfin',
 'Zeelander',
"GRAND",
"Motortjalk",
"Archambault",
"Hydrosport",
"De Antonio Yachts",
"Klassisk Sexa",
"Aicon",
"Riverline",
"Varend Woonschip Motor Klipper",
"Searib",
"Majesty",
"Fiart Mare",
"Gobbi",
"Rodi Inflatables",
"Hollandischer Werftbau",
"Brabus Shadow",
"Beaconax Yachtbau GmbH",
"Selene",
"LM",
"Riviera",
"Etap",
"Carlini",
"Loodsboot",
"Doral",
"Vechtkruiser",
"Yam (Yamaha Motor Germany)",
"Hemmes",
"Apreamare",
"Gobbi 21.05",
"Yamaha WaveRunner",
"Scarab",
"Franchini",
"Dean Catamarans",
"X-Shore Eelex",
"YAM",
"Hydrolift",
"SACS",
"Drago",
"Starfisher",
"Diano Cantiere",
"Marian Magic",
"Scarab",
"Madera",
"Luffe",
"Stimson",
"Hai",
"Canados",
"Gobbi",
"Pfeil",
"Mayland",
"Bodrum Centre Cockpit",
"Quarken",
"Innovazione & Progetti",
"Vindo",
"Hoya",
"Olympic",
"YAMAHA",
"Sagitta",
"Rodman",
"Highfield",
"Colin Archer",
"Ocean Yachts",
"3D Tender",
"TendR",
"Caravanboat",
"Terhi",
"Wasa",
"Mostes",
"EVO",
"Bandholm",
"Dellapasqua",
"Sasga Yachts",
"Condor Yachting",
"Hartmann Boote",
"Cayman Yachts",
"Atlantis",
"VTS Boats",
"Fullemann",
"Folkebadcentralen",
"Viko Yachts",
"Viper",
"Maxi",
"Nautor Swan",
"Black Pepper",
"Lami",
"SMT cabinsloep",
"CARNEVALI",
"ZARmini",
"Mercury",
"Aqua House",
"Flying Shark",
"Mahogany Solar Electric Salon Boat",
"Sunrise Yacht",
"Beluga",
"Futuro ZX",
"Adria Event",
"Yam",
"Sandstrom Batar Classic",
"Terhi",
"Williams Minijet",
"Pegazus",
"Terhi",
"CMB",
"Alu plaisance",
"Hille Roda",
"Valkvlet",
"Cayman",
"VBoats",
"Mascot",
"Vaton",
"Fareast",
"Ventusa",
"Nautica Dorado",
"Aqualine",
 "Schochl",
"Firebird",
"Conam",
"Luna",
"Avance",
"Maxum",
"Integrity Trawlers",
"Dahl",
"Faul",
"LakeLife",
"OQS",
"ZAR Formenti",
"Breehorn",
"Brig Inflatable Boats",
"Super Favorite",
"LAGUNA",
"Pirelli",
"Aquaspirit",
"Safir",
"Maxum",
"Lodestar",
"Raised Pilothouse",
"Euroship",
"Brandaris",
"Gruno",
"Brig",
"Botnia Marin",
"Klaassen Super van Craft",
"Tjalk",
"Verlvale",
"Pioner",
"Sunliner",
"Sandstrom",
"Monachus Yachts",
"Barkas",
"Alfastreet Marine",
"Astor",
"Toolycraft",
"Camper & Nicholsons",
"Nor-Dan",
"Auster",
"CUBO",
"Hero",
"Pyxis Yachts",
"Moon Yacht",
"Dale Nelson",
"Technohull",
"Succes",
"Astromar",
"Sciarelli",
"Nord Star",
"Mingolla",
"Koopmans",
"Kaag Kruiser",
"Eryd",
"Sciallino",
"Kaag Kruiser",
"Dagpassagiersschip",
"Desner Sport",
"Korad Scalar",
"Heesen",
"Marine Time",
"Yachtline",
"Fleming Yachts",
"Nomad",
"Luxe Motor",
"Linder",
"Schooner Classic gaff",
"Kimple",
"Finnsailer",
"Alalunga",
"Boathome",
"Corsiva",
"AB Inflatables",
"Steilsteven",
"Cantieri Estensi",
"Carline Yachts",
"Sea-Doo",
"Tullio Abbate",
"Doggersbank",
"Stevens Nautical",
"Williams",
"Lomac Nautica",
"Van Leeuwen Schouw",
"Williams"]
    
    unique_manufacturers = df['MANUFACTURER'].unique()
    unique_manufacturers = list(unique_manufacturers[unique_manufacturers != 'nan'])
    
    for index, row in df.iterrows():
        x = row['MODEL']
        y = row['DESCRIPTION']
        z = row['MANUFACTURER']

        if pd.notna(x) and pd.isna(z):
            for manufacturer in unique_manufacturers:
                if str(manufacturer).lower() in x.lower():
                    df.at[index, 'MANUFACTURER'] = manufacturer
        
        if pd.notna(x) and z == 'nan':
            for manufacturer in unique_manufacturers:
                if str(manufacturer).lower() in x.lower():
                    df.at[index, 'MANUFACTURER'] = manufacturer

        if pd.notna(y) and pd.isna(z):
            for manufacturer in unique_manufacturers:
                if str(manufacturer).lower() in y.lower():
                    df.at[index, 'MANUFACTURER'] = manufacturer
        
        if pd.notna(y) and z == 'nan':
            for manufacturer in unique_manufacturers:
                if str(manufacturer).lower() in y.lower():
                    df.at[index, 'MANUFACTURER'] = manufacturer
        
        for i in manufacturers_list_1:
            
            if str(i).lower() in x.lower() and pd.isna(z):
                df.at[index, 'MANUFACTURER'] = i
            
            if str(i).lower() in x.lower() and z == 'nan':
                df.at[index, 'MANUFACTURER'] = i
    
        if pd.isna(z) or z == 'nan':
            df.at[index, 'MANUFACTURER'] = df.at[index, 'MODEL'].split(' ', 1)[0]
    
    return df


def remove_accents(df, columns):
    for column in columns:
        df[column] = df[column].apply(lambda x: unidecode(str(x)))
    return df


def get_material(df):
    material_list = df['MATERIAL'].unique()
    
    for index, row in df.iterrows():
        x = row['DESCRIPTION']
        y = row['MATERIAL']
     
        if pd.notna(x) and pd.isna(y):
            for material in material_list:
                if str(material).lower() in x.lower():
                    df.at[index, 'MATERIAL'] = material
        
        if pd.notna(x) and y == 'nan':
           for material in material_list:
                if str(material).lower() in x.lower():
                    df.at[index, 'MATERIAL'] = material

    return df

def column_type(df, data_type, *columns):
    for column in columns:
        df[column] = df[column].astype(data_type)
    return df

def get_engine_details(df):
    pattern_num_engines = r"(\d+)\s*x"
    pattern_hp = r"(\d+(?:[.,']\d+)?)\s*(?:HP|CV|PS|hp|cv|ps|Hp|Cv|Ps)"
    pattern_kw = r"(\d+(?:[.,']\d+)?)\s*(?:KW|kw|Kw)"

    df['NUM_ENGINES'] = None
    df['ENGINE_HP'] = None
    df['ENGINE_KW'] = None
    
    for index, value in df['ENGINE PERFORMANCE'].items():
        if isinstance(value, str) and 'x' in value:
            match_num_engines = re.search(pattern_num_engines, value, flags=re.IGNORECASE)
            match_hp = re.search(pattern_hp, value, flags=re.IGNORECASE)
            match_kw = re.search(pattern_kw, value, flags=re.IGNORECASE)
            
            if match_num_engines and pd.isna(df.at[index, 'NUM_ENGINES']):
                num_engines = int(match_num_engines.group(1))
                df.at[index, 'NUM_ENGINES'] = num_engines
            
            if match_hp and pd.isna(df.at[index, 'ENGINE_HP']):
                hp = float(match_hp.group(1).replace(',', '').replace("'", "").replace(".", ""))
                df.at[index, 'ENGINE_HP'] = hp
            
            if match_kw and pd.isna(df.at[index, 'ENGINE_KW']):
                kw = float(match_kw.group(1).replace(',', '').replace("'", "").replace(".", ""))
                df.at[index, 'ENGINE_KW'] = kw

    for index, value in df['ENGINE'].items():
        if pd.notna(value) and value != 'nan':
            match_num_engines = re.search(pattern_num_engines, value, flags=re.IGNORECASE)
            match_hp = re.search(pattern_hp, value, flags=re.IGNORECASE)
            match_kw = re.search(pattern_kw, value, flags=re.IGNORECASE)

            if isinstance(value, str):
                if match_num_engines and pd.isna(df.at[index, 'NUM_ENGINES']):
                    num_engines = int(match_num_engines.group(1))
                    df.at[index, 'NUM_ENGINES'] = num_engines

                if match_hp and pd.isna(df.at[index, 'ENGINE_HP']):
                    hp = float(match_hp.group(1).replace(',', '').replace("'", "").replace(".", ""))
                    df.at[index, 'ENGINE_HP'] = hp

                if match_kw and pd.isna(df.at[index, 'ENGINE_KW']):
                    kw = float(match_kw.group(1).replace(',', '').replace("'", "").replace(".", ""))
                    df.at[index, 'ENGINE_KW'] = kw
    
    for index, row in df[['ENGINE','NUM_ENGINES','ENGINE_HP','ENGINE_KW']].iterrows():
        if pd.notna(row['ENGINE_HP']) and pd.isna(row['NUM_ENGINES']):
            df.at[index, 'NUM_ENGINES'] = 1
         
        if pd.notna(row['ENGINE_KW']) and pd.isna(row['NUM_ENGINES']):
            df.at[index, 'NUM_ENGINES'] = 1
        
        if pd.notna(row['ENGINE']) and pd.isna(row['NUM_ENGINES']):
            df.at[index, 'NUM_ENGINES'] = 1
    
    return df


def get_draught(df):
    for index, value in df['DRAUGHT'].items():
    
        if pd.notna(value) and 'm' in value and '-' in value:
            df.at[index, 'DRAUGHT'] = value.split('-')[1].split('m')[0].strip()
        
        elif pd.notna(value) and 'm' in value:
            df.at[index, 'DRAUGHT'] = value.split('m')[0].strip()
        
        elif pd.notna(value) and '-' in value:
            df.at[index, 'DRAUGHT'] = value.split('-')[1].strip()
        
        elif value == '':
            df.at[index, 'DRAUGHT'] = np.nan
        
        else:
            df.at[index, 'DRAUGHT'] = np.nan
        
    return df


# ------------------------------------  MACHINE LEARNING ----------------------------------- #

def get_dummies(df, *columns):
    encoded_columns = pd.get_dummies(df[list(columns)])
    dummies_df = pd.concat([df, encoded_columns], axis=1)
    dummies_df.drop(columns=list(columns), inplace=True)
    return dummies_df

def label_encoder(df, *columns):
    label_encoder = LabelEncoder()
    for column in columns:
        df[column] = label_encoder.fit_transform(df[column])
    return df

def get_models(df):
    x = df.drop(columns=['PRICE_EUR'])
    y = df.PRICE_EUR
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.1, random_state=50)

    models = {
        "lr": LinReg(),
        "ridge": Ridge(), #lr similar
        "lasso": Lasso(), # lr similar 
        "sgd": SGDRegressor(),
        "knn": KNeighborsRegressor(),
        "grad": GradientBoostingRegressor(),
        "svr": SVR() #potato chip
    }

    for model in models.values():
        print(f"Training: {model}")
        model.fit(x_train, y_train)

    for name, model in models.items():
        y_pred = model.predict(x_test)
        print(f"------------{name}------------\n")
        print(f"MAE, error: {metrics.mean_absolute_error(y_test, y_pred)}")
        print(f"MSE, error: {metrics.mean_squared_error(y_test, y_pred)}")
        print(f"RMSE, error: {np.sqrt(metrics.mean_squared_error(y_test, y_pred))}")
        print(f"r2: {metrics.r2_score(y_test, y_pred)}")
        print("\n")