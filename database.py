"""Player and club database generation for Football Manager 26."""

import random
import uuid
from models import Player, Club, Tactic, Position, Formation, Mentality, PlayStyle, LeagueSeason, LeagueTier

ENGLISH_FIRST = ["James", "Jack", "Oliver", "Harry", "Charlie", "Thomas", "George", "Oscar", "William", "Henry", "Daniel", "Samuel", "Joseph", "David", "Luke", "Ben", "Ryan", "Nathan", "Connor", "Ethan", "Alex", "Kyle", "Jordan", "Lewis", "Aaron", "Callum", "Jake", "Liam", "Mason", "Tyler", "Reece", "Marcus", "Dominic", "Bradley", "Scott", "Craig", "Gary", "Wayne", "Paul", "Mark"]
ENGLISH_LAST = ["Smith", "Jones", "Williams", "Taylor", "Brown", "Davies", "Wilson", "Evans", "Thomas", "Johnson", "Roberts", "Walker", "Wright", "Robinson", "Thompson", "White", "Hughes", "Edwards", "Green", "Hall", "Wood", "Harris", "Clark", "Jackson", "Turner", "Hill", "Moore", "Ward", "Baker", "Collins", "Bennett", "Gray", "Dixon", "Cole", "Palmer", "Carter", "Mitchell", "Cooper", "Fox"]
SPANISH_FIRST = ["Carlos", "Miguel", "Alejandro", "Daniel", "Pablo", "David", "Javier", "Adrian", "Sergio", "Diego", "Alvaro", "Raul", "Fernando", "Antonio", "Manuel", "Jorge", "Roberto", "Marcos", "Ivan", "Oscar", "Hugo", "Ruben", "Alberto", "Luis", "Angel", "Victor", "Pedro", "Enrique", "Rafael", "Gonzalo", "Andres", "Iker", "Nacho", "Kiko", "Borja", "Dani", "Juanma", "Santi", "Paco", "Toni"]
SPANISH_LAST = ["Garcia", "Rodriguez", "Martinez", "Lopez", "Gonzalez", "Hernandez", "Perez", "Sanchez", "Ramirez", "Torres", "Flores", "Rivera", "Gomez", "Diaz", "Moreno", "Alvarez", "Romero", "Ruiz", "Jimenez", "Fernandez", "Navarro", "Dominguez", "Vega", "Castillo", "Ortiz", "Molina", "Delgado", "Castro", "Prieto", "Ramos", "Serrano", "Blanco", "Suarez", "Medina", "Iglesias", "Reyes", "Cabrera", "Mora"]
FRENCH_FIRST = ["Lucas", "Hugo", "Mathis", "Nathan", "Thomas", "Leo", "Louis", "Gabriel", "Jules", "Arthur", "Raphael", "Maxime", "Alexandre", "Antoine", "Baptiste", "Clement", "Damien", "Etienne", "Florian", "Guillaume", "Julien", "Kevin", "Laurent", "Nicolas", "Olivier", "Pierre", "Romain", "Sebastien", "Theo", "Vincent", "Yannick", "Adrien", "Bruno", "Cedric", "Fabien", "Henri", "Mathieu", "Philippe", "Quentin", "Xavier"]
FRENCH_LAST = ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David", "Bertrand", "Roux", "Vincent", "Fournier", "Morel", "Girard", "Andre", "Mercier", "Dupont", "Lambert", "Bonnet", "Francois", "Martinez", "Legrand", "Garnier", "Faure", "Rousseau", "Blanc", "Guerin", "Boyer", "Gauthier", "Perrin", "Robin", "Masson"]
GERMAN_FIRST = ["Lukas", "Noah", "Leon", "Finn", "Jonas", "Paul", "Luis", "Felix", "Max", "Niklas", "Julian", "Tim", "Moritz", "Sebastian", "Philipp", "Tobias", "Dennis", "Kevin", "Marc", "Andre"]
GERMAN_LAST = ["Muller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker", "Hoffmann", "Schafer", "Koch", "Bauer", "Richter", "Klein", "Wolf", "Schroder", "Neumann", "Schwarz", "Zimmermann", "Braun"]
ITALIAN_FIRST = ["Luca", "Marco", "Alessandro", "Andrea", "Matteo", "Davide", "Francesco", "Simone", "Federico", "Riccardo", "Giuseppe", "Stefano", "Paolo", "Gabriele", "Nicolo", "Daniele", "Antonio", "Fabio", "Cristian", "Enrico"]
ITALIAN_LAST = ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo", "Ricci", "Marino", "Greco", "Bruno", "Gallo", "Conti", "De Luca", "Mancini", "Lombardi", "Barbieri", "Fontana", "Moretti", "Caruso"]

NAME_POOLS = {
    "England": (ENGLISH_FIRST, ENGLISH_LAST),
    "Spain": (SPANISH_FIRST, SPANISH_LAST),
    "France": (FRENCH_FIRST, FRENCH_LAST),
    "Germany": (GERMAN_FIRST, GERMAN_LAST),
    "Italy": (ITALIAN_FIRST, ITALIAN_LAST),
}

# Existing playable pyramids
ENGLAND_PYRAMID = [
    {
        "name": "Premier League", "tier": 1, "avg_budget": 120000000, "avg_wage": 120000, "avg_reputation": 82, "ticket_price": 55,
        "sponsor_range": (800000, 2500000), "max_debt": 400000000, "promotion_places": 0, "playoff_places": [], "relegation_places": 3,
        "clubs": [
            ("Arsenal", "ARS", "Emirates Stadium", 60704), ("Aston Villa", "AVL", "Villa Park", 42785), ("Bournemouth", "BOU", "Vitality Stadium", 11379), ("Brentford", "BRE", "Gtech Community Stadium", 17250),
            ("Brighton & Hove Albion", "BHA", "Amex Stadium", 31876), ("Chelsea", "CHE", "Stamford Bridge", 40341), ("Crystal Palace", "CRY", "Selhurst Park", 25486), ("Everton", "EVE", "Goodison Park", 39414),
            ("Fulham", "FUL", "Craven Cottage", 25700), ("Ipswich Town", "IPS", "Portman Road", 29673), ("Leicester City", "LEI", "King Power Stadium", 32312), ("Liverpool", "LIV", "Anfield", 61276),
            ("Manchester City", "MCI", "Etihad Stadium", 53400), ("Manchester United", "MUN", "Old Trafford", 74140), ("Newcastle United", "NEW", "St James Park", 52305), ("Nottingham Forest", "NFO", "City Ground", 30445),
            ("Southampton", "SOU", "St Mary's Stadium", 32384), ("Tottenham Hotspur", "TOT", "Tottenham Hotspur Stadium", 62850), ("West Ham United", "WHU", "London Stadium", 62500), ("Wolverhampton Wanderers", "WOL", "Molineux", 31750),
        ],
    },
    {
        "name": "Championship", "tier": 2, "avg_budget": 12000000, "avg_wage": 18000, "avg_reputation": 62, "ticket_price": 32,
        "sponsor_range": (70000, 250000), "max_debt": 75000000, "promotion_places": 2, "playoff_places": [3, 4, 5, 6], "relegation_places": 3,
        "clubs": [
            ("Blackburn Rovers", "BLB", "Ewood Park", 31367), ("Bristol City", "BRC", "Ashton Gate", 27000), ("Burnley", "BUR", "Turf Moor", 21944), ("Cardiff City", "CAR", "Cardiff City Stadium", 33280),
            ("Coventry City", "COV", "CBS Arena", 32609), ("Derby County", "DER", "Pride Park", 33597), ("Hull City", "HUL", "MKM Stadium", 25586), ("Leeds United", "LEE", "Elland Road", 37908),
            ("Luton Town", "LUT", "Kenilworth Road", 11500), ("Middlesbrough", "MID", "Riverside Stadium", 34988), ("Millwall", "MIL", "The Den", 20146), ("Norwich City", "NOR", "Carrow Road", 27244),
            ("Oxford United", "OXU", "Kassam Stadium", 12500), ("Plymouth Argyle", "PLY", "Home Park", 17384), ("Portsmouth", "POR", "Fratton Park", 20899), ("Preston North End", "PRE", "Deepdale", 23408),
            ("Queens Park Rangers", "QPR", "Loftus Road", 18360), ("Sheffield Wednesday", "SHW", "Hillsborough", 39732), ("Stoke City", "STK", "bet365 Stadium", 30089), ("Sunderland", "SUN", "Stadium of Light", 49000),
            ("Swansea City", "SWA", "Swansea.com Stadium", 21088), ("Watford", "WAT", "Vicarage Road", 22000), ("West Bromwich Albion", "WBA", "The Hawthorns", 26850), ("Sheffield United", "SHU", "Bramall Lane", 32050),
        ],
    },
    {
        "name": "League One", "tier": 3, "avg_budget": 3500000, "avg_wage": 5500, "avg_reputation": 48, "ticket_price": 24,
        "sponsor_range": (18000, 70000), "max_debt": 18000000, "promotion_places": 2, "playoff_places": [3, 4, 5, 6], "relegation_places": 4,
        "clubs": [
            ("Barnsley", "BAR", "Oakwell", 23287), ("Blackpool", "BPL", "Bloomfield Road", 16416), ("Bolton Wanderers", "BOL", "Toughsheet Community Stadium", 28000), ("Bristol Rovers", "BRR", "Memorial Stadium", 9832),
            ("Burton Albion", "BRT", "Pirelli Stadium", 6912), ("Cambridge United", "CAM", "Abbey Stadium", 8127), ("Charlton Athletic", "CHA", "The Valley", 27111), ("Exeter City", "EXE", "St James Park", 8527),
            ("Huddersfield Town", "HUD", "John Smith's Stadium", 24500), ("Leyton Orient", "LEY", "Brisbane Road", 9271), ("Lincoln City", "LIN", "Sincil Bank", 10200), ("Mansfield Town", "MAN", "One Call Stadium", 9186),
            ("Northampton Town", "NHT", "Sixfields", 7798), ("Peterborough United", "PET", "London Road", 15314), ("Reading", "REA", "Select Car Leasing Stadium", 24161), ("Rotherham United", "ROT", "New York Stadium", 12021),
            ("Shrewsbury Town", "SHR", "New Meadow", 9875), ("Stevenage", "STE", "Lamex Stadium", 7224), ("Wigan Athletic", "WIG", "Brick Community Stadium", 25133), ("Wycombe Wanderers", "WYC", "Adams Park", 9948),
            ("Birmingham City", "BIR", "St Andrew's", 29409), ("Crawley Town", "CRA", "Broadfield Stadium", 6134), ("Stockport County", "STC", "Edgeley Park", 10841), ("Wrexham", "WRE", "Racecourse Ground", 10500),
        ],
    },
    {
        "name": "League Two", "tier": 4, "avg_budget": 1200000, "avg_wage": 2200, "avg_reputation": 38, "ticket_price": 18,
        "sponsor_range": (8000, 30000), "max_debt": 6000000, "promotion_places": 3, "playoff_places": [4, 5, 6, 7], "relegation_places": 2,
        "clubs": [
            ("Accrington Stanley", "ACC", "Wham Stadium", 5440), ("AFC Wimbledon", "WIM", "Plough Lane", 9300), ("Barrow", "BRW", "SO Legal Stadium", 6500), ("Bradford City", "BFD", "Valley Parade", 25136),
            ("Carlisle United", "CAR", "Brunton Park", 18202), ("Cheltenham Town", "CHT", "Whaddon Road", 7066), ("Chesterfield", "CHF", "SMH Group Stadium", 10338), ("Colchester United", "COL", "JobServe Community Stadium", 10084),
            ("Crewe Alexandra", "CRE", "Mornflake Stadium", 10153), ("Doncaster Rovers", "DON", "Eco-Power Stadium", 15231), ("Fleetwood Town", "FLE", "Highbury Stadium", 5327), ("Gillingham", "GIL", "Priestfield Stadium", 11582),
            ("Grimsby Town", "GRI", "Blundell Park", 9052), ("Harrogate Town", "HAR", "Wetherby Road", 5000), ("Milton Keynes Dons", "MKD", "Stadium MK", 30500), ("Morecambe", "MOR", "Mazuma Stadium", 6476),
            ("Newport County", "NPT", "Rodney Parade", 7850), ("Notts County", "NOT", "Meadow Lane", 19841), ("Port Vale", "PTV", "Vale Park", 19052), ("Salford City", "SAL", "Moor Lane", 5108),
            ("Swindon Town", "SWI", "County Ground", 15728), ("Tranmere Rovers", "TRA", "Prenton Park", 16567), ("Walsall", "WAL", "Bescot Stadium", 11300), ("Bromley", "BRO", "Hayes Lane", 5000),
        ],
    },
    {
        "name": "National League", "tier": 5, "avg_budget": 500000, "avg_wage": 2000, "avg_reputation": 30, "ticket_price": 15,
        "sponsor_range": (2000, 5000), "max_debt": 200000, "promotion_places": 1, "playoff_places": [2, 3, 4, 5, 6, 7], "relegation_places": 0,
        "clubs": [
            ("Aldershot Town", "ALD", "Recreation Ground", 7100), ("Barnet", "BNT", "The Hive Stadium", 6200), ("Boreham Wood", "BOR", "Meadow Park", 4500), ("Dagenham & Redbridge", "DAG", "Chigwell Construction Stadium", 6000),
            ("Dorking Wanderers", "DOR", "Meadowbank Stadium", 3000), ("Eastleigh", "EAS", "Silverlake Stadium", 5200), ("Ebbsfleet United", "EBB", "Stonebridge Road", 4184), ("FC Halifax Town", "HAL", "The Shay", 10000),
            ("Gateshead", "GAT", "Gateshead International Stadium", 11750), ("Hartlepool United", "HTP", "Suit Direct Stadium", 7856), ("Maidenhead United", "MAI", "York Road", 4500), ("Oldham Athletic", "OLD", "Boundary Park", 13500),
            ("Oxford City", "OXC", "Court Place Farm", 3000), ("Rochdale", "ROC", "Crown Oil Arena", 10249), ("Solihull Moors", "SOL", "Damson Park", 5500), ("Southend United", "SEN", "Roots Hall", 12392),
            ("Wealdstone", "WEA", "Grosvenor Vale", 3000), ("Woking", "WOK", "Laithwaite Community Stadium", 6036), ("York City", "YOR", "LNER Community Stadium", 8256), ("Altrincham", "ALT", "Moss Lane", 6085),
            ("Braintree Town", "BRA", "Cressing Road", 4000), ("Forest Green Rovers", "FGR", "The New Lawn", 5140), ("Sutton United", "SUT", "VBS Community Stadium", 5000), ("Tamworth", "TAM", "The Lamb Ground", 4963),
        ],
    },
]

SPAIN_PYRAMID = [
    {
        "name": "La Liga", "tier": 1, "avg_budget": 70000000, "avg_wage": 70000, "avg_reputation": 78, "ticket_price": 42,
        "sponsor_range": (450000, 1600000), "max_debt": 220000000, "promotion_places": 0, "playoff_places": [], "relegation_places": 3,
        "clubs": [
            ("Real Madrid", "RMA", "Santiago Bernabeu", 81044), ("Barcelona", "BAR", "Estadi Olimpic", 54927), ("Atletico Madrid", "ATM", "Metropolitano", 68456), ("Sevilla", "SEV", "Ramon Sanchez-Pizjuan", 43883),
            ("Valencia", "VAL", "Mestalla", 48600), ("Villarreal", "VIL", "Estadio de la Ceramica", 23500), ("Real Sociedad", "RSO", "Reale Arena", 39500), ("Athletic Club", "ATH", "San Mames", 53289),
            ("Real Betis", "BET", "Benito Villamarin", 60721), ("Celta Vigo", "CEL", "Abanca Balaidos", 29000), ("Getafe", "GET", "Coliseum", 17393), ("Osasuna", "OSA", "El Sadar", 23576),
            ("Mallorca", "MAL", "Son Moix", 23142), ("Las Palmas", "LPA", "Gran Canaria", 32000), ("Girona", "GIR", "Montilivi", 14591), ("Alaves", "ALA", "Mendizorrotza", 19840),
            ("Rayo Vallecano", "RAY", "Vallecas", 14708), ("Espanyol", "ESP", "RCDE Stadium", 40500), ("Real Valladolid", "VLL", "Jose Zorrilla", 27000), ("Leganes", "LEG", "Butarque", 12450),
        ],
    },
    {
        "name": "Segunda Division", "tier": 2, "avg_budget": 7000000, "avg_wage": 11000, "avg_reputation": 57, "ticket_price": 24,
        "sponsor_range": (45000, 180000), "max_debt": 35000000, "promotion_places": 2, "playoff_places": [3, 4, 5, 6], "relegation_places": 4,
        "clubs": [
            ("Real Zaragoza", "ZAR", "La Romareda", 33608), ("Sporting Gijon", "GIJ", "El Molinon", 29538), ("Oviedo", "OVI", "Carlos Tartiere", 30500), ("Tenerife", "TEN", "Heliodoro Rodriguez Lopez", 22411),
            ("Albacete", "ALB", "Carlos Belmonte", 17524), ("Burgos", "BUR", "El Plantio", 12200), ("Cadiz", "CAD", "Nuevo Mirandilla", 20724), ("Castellon", "CAS", "Castalia", 15000),
            ("Cordoba", "COR", "El Arcangel", 21822), ("Deportivo La Coruna", "DEP", "Riazor", 32490), ("Eibar", "EIB", "Ipurua", 8164), ("Elche", "ELC", "Martinez Valero", 33732),
            ("Granada", "GRA", "Los Carmenes", 19336), ("Huesca", "HUE", "El Alcoraz", 9100), ("Levante", "LEV", "Ciutat de Valencia", 26354), ("Malaga", "MGA", "La Rosaleda", 30044),
            ("Mirandes", "MIR", "Anduva", 5759), ("Racing Santander", "RAC", "El Sardinero", 22222), ("Almeria", "ALM", "Power Horse Stadium", 21350), ("Cartagena", "CAR", "Cartagonova", 14500),
            ("Ferrol", "FER", "A Malata", 12000), ("Eldense", "ELD", "Nuevo Pepico Amat", 5776),
        ],
    },
    {
        "name": "Primera Federacion", "tier": 3, "avg_budget": 1800000, "avg_wage": 3200, "avg_reputation": 42, "ticket_price": 16,
        "sponsor_range": (10000, 50000), "max_debt": 8000000, "promotion_places": 2, "playoff_places": [3, 4, 5, 6], "relegation_places": 5,
        "clubs": [
            ("Cultural Leonesa", "CUL", "Reino de Leon", 13451), ("Ponferradina", "PON", "El Toralin", 8800), ("Lugo", "LUG", "Anxo Carro", 7800), ("Unionistas", "UNI", "Reina Sofia", 4900),
            ("Celta Fortuna", "CLF", "Balaidos Annex", 4000), ("Barcelona Atletic", "BLA", "Johan Cruyff", 6000), ("Tarazona", "TAR", "Municipal de Tarazona", 2500), ("Arenteiro", "ARE", "Espinedo", 4500),
            ("Sabadell", "SAB", "Nova Creu Alta", 11908), ("Nastic Tarragona", "NAT", "Nou Estadi", 14500), ("Ibiza", "IBI", "Can Misses", 6500), ("Ceuta", "CEU", "Alfonso Murube", 6500),
            ("Antequera", "ANT", "El Mauli", 4500), ("Alcoyano", "ALC", "El Collao", 4850), ("Algeciras", "ALG", "Nuevo Mirador", 7000), ("Murcia", "MUR", "Enrique Roca", 31000),
            ("San Fernando", "SFE", "Iberoamericano", 8000), ("Recreativo Huelva", "REC", "Nuevo Colombino", 21670), ("Fuenlabrada", "FUE", "Fernando Torres", 6000), ("Merida", "MER", "Romano", 12000),
            ("Andorra", "AND", "Estadi Nacional", 3300), ("Real Union", "RUN", "Gal", 5600),
        ],
    },
    {
        "name": "Segunda Federacion", "tier": 4, "avg_budget": 400000, "avg_wage": 1500, "avg_reputation": 28, "ticket_price": 12,
        "sponsor_range": (1500, 4000), "max_debt": 150000, "promotion_places": 1, "playoff_places": [2, 3, 4, 5], "relegation_places": 5,
        "clubs": [
            ("Badajoz", "BAD", "Nuevo Vivero", 12200), ("Numancia", "NUM", "Los Pajaritos", 9500), ("Pontevedra", "PON", "Pasaron", 8000), ("Talavera", "TAL", "El Prado", 5000),
            ("Hercules", "HER", "Rico Perez", 29500), ("Logrones", "LOG", "Las Gaunas", 16000), ("Linares Deportivo", "LIN", "Linarejos", 10000), ("Utebo", "UTE", "Santa Ana", 2500),
            ("Yeclano Deportivo", "YEC", "La Constitucion", 5000), ("Marbella", "MAR", "Dama de Noche", 7000), ("Estepona", "EST", "Francisco Munoz Perez", 3800), ("Orihuela", "ORI", "Los Arcos", 5000),
            ("Compostela", "COM", "Vero Boquete", 15000), ("Torremolinos", "TOR", "El Pozuelo", 3500), ("Aviles", "AVI", "Roman Suarez Puerta", 5200), ("Guijuelo", "GUI", "Municipal", 1500),
            ("Cacereno", "CAC", "Principe Felipe", 7000), ("Getafe B", "GEB", "Ciudad Deportiva", 2000), ("Illescas", "ILL", "Municipal de Illescas", 3000), ("Langreo", "LAN", "Ganzabal", 4500),
            ("Teruel", "TER", "Pinilla", 8000), ("Arandina", "ARA", "El Montecillo", 4500),
        ],
    },
    {
        "name": "Tercera Federacion", "tier": 5, "avg_budget": 180000, "avg_wage": 700, "avg_reputation": 20, "ticket_price": 8,
        "sponsor_range": (800, 2200), "max_debt": 80000, "promotion_places": 1, "playoff_places": [2, 3, 4, 5], "relegation_places": 0,
        "clubs": [
            ("Atletico Mancha Real", "AMR", "La Juventud", 3000), ("Azuaga", "AZU", "Municipal de Azuaga", 2500), ("Caudal Deportivo", "CAU", "Hermanos Anton", 3000), ("Coria", "COR", "La Isla", 3000),
            ("Don Benito", "DBE", "Vicente Sanz", 3500), ("Europa", "EUR", "Nou Sardenya", 7000), ("Gerena", "GER", "Jose Juan Romero Gil", 2500), ("Lealtad", "LEA", "Las Callejas", 3000),
            ("Manresa", "MAN", "Congost", 3000), ("Mollerussa", "MOL", "Municipal", 2500), ("Olot", "OLO", "Municipal d'Olot", 4000), ("Poblense", "POB", "Sa Pobla", 2500),
            ("San Roque de Lepe", "SRL", "Ciudad de Lepe", 3500), ("Tarancón", "TRN", "Municipal", 2500), ("UCAM B", "UCB", "El Mayayo", 2500), ("Villanovense", "VIL", "Romero Cuerda", 4000),
            ("Xerez Deportivo", "XER", "Chapín Annex", 4000), ("Zamora", "ZAM", "Ruta de la Plata", 7813), ("Laredo", "LAR", "San Lorenzo", 3000), ("Sant Andreu", "SAN", "Narcis Sala", 6500),
            ("Ourense CF", "OUR", "O Couto", 5600), ("Utrera", "UTR", "San Juan Bosco", 2500),
        ],
    },
]

FRANCE_PYRAMID = [
    {
        "name": "Ligue 1", "tier": 1, "avg_budget": 65000000, "avg_wage": 65000, "avg_reputation": 75, "ticket_price": 36,
        "sponsor_range": (400000, 1400000), "max_debt": 180000000, "promotion_places": 0, "playoff_places": [], "relegation_places": 2,
        "clubs": [
            ("Paris Saint-Germain", "PSG", "Parc des Princes", 47929), ("Marseille", "OM", "Velodrome", 67394), ("Lyon", "OL", "Groupama Stadium", 59186), ("Monaco", "ASM", "Stade Louis II", 18523),
            ("Lille", "LIL", "Stade Pierre-Mauroy", 50083), ("Nice", "NIC", "Allianz Riviera", 35624), ("Rennes", "REN", "Roazhon Park", 29194), ("Lens", "LEN", "Bollaert-Delelis", 38058),
            ("Strasbourg", "STR", "Stade de la Meinau", 26109), ("Nantes", "NAN", "La Beaujoire", 35322), ("Montpellier", "MON", "Mosson", 32950), ("Reims", "REI", "Auguste Delaune", 21029),
            ("Brest", "BRE", "Francis-Le Ble", 15931), ("Toulouse", "TOU", "Stadium de Toulouse", 33150), ("Auxerre", "AUX", "Abbe-Deschamps", 18000), ("Angers", "ANG", "Raymond Kopa", 19000),
            ("Le Havre", "HAV", "Stade Oceane", 25178), ("Saint-Etienne", "STE", "Geoffroy-Guichard", 41965),
        ],
    },
    {
        "name": "Ligue 2", "tier": 2, "avg_budget": 6500000, "avg_wage": 9000, "avg_reputation": 54, "ticket_price": 20,
        "sponsor_range": (35000, 140000), "max_debt": 30000000, "promotion_places": 2, "playoff_places": [3, 4, 5], "relegation_places": 2,
        "clubs": [
            ("Bordeaux", "BOR", "Matmut Atlantique", 42115), ("Caen", "CAE", "Michel d'Ornano", 20200), ("Guingamp", "GUI", "Roudourou", 18000), ("Bastia", "BAS", "Armand Cesari", 16000),
            ("Grenoble", "GRE", "Stade des Alpes", 20068), ("Amiens", "AMI", "Licorne", 12097), ("Paris FC", "PFC", "Charlety", 19904), ("Rodez", "ROD", "Paul Lignon", 5955),
            ("Troyes", "TRY", "Stade de l'Aube", 20800), ("Clermont", "CLE", "Gabriel Montpied", 11980), ("Lorient", "LOR", "Moustoir", 18970), ("Metz", "MET", "Saint-Symphorien", 25636),
            ("Pau", "PAU", "Nouste Camp", 4031), ("Laval", "LAV", "Francis Le Basser", 18607), ("Annecy", "ANN", "Parc des Sports", 15500), ("Ajaccio", "AJA", "Francois Coty", 10660),
            ("Martigues", "MAR", "Francis Turcan", 11000), ("Red Star", "RST", "Stade Bauer", 10000), ("Dunkerque", "DUN", "Marcel-Tribut", 4933), ("Valenciennes", "VAL", "Hainaut", 25000),
        ],
    },
    {
        "name": "National", "tier": 3, "avg_budget": 1400000, "avg_wage": 2600, "avg_reputation": 40, "ticket_price": 14,
        "sponsor_range": (9000, 40000), "max_debt": 6000000, "promotion_places": 2, "playoff_places": [3], "relegation_places": 4,
        "clubs": [
            ("Sochaux", "SOC", "Bonal", 20025), ("Nancy", "NAN", "Marcel Picot", 20087), ("Nimes", "NIM", "Costieres", 18482), ("Dijon", "DIJ", "Gaston Gerard", 15995),
            ("Le Mans", "LEM", "Marie-Marvingt", 25064), ("Versailles", "VER", "Montbauron", 7500), ("Orleans", "ORL", "Source", 7439), ("Rouen", "ROU", "Robert Diochon", 12018),
            ("Villefranche", "VIL", "Armand Chouffet", 3200), ("Bourg-en-Bresse", "BOU", "Marcel Verchere", 11400), ("Chateauroux", "CHA", "Gaston Petit", 17072), ("Concarneau", "CON", "Guy Piriou", 7800),
            ("Boulogne", "BOL", "Liberation", 15034), ("Quevilly-Rouen", "QRM", "Robert Diochon", 12018), ("Aubagne", "AUB", "de Lattre", 3000), ("Valenciennes B", "VAB", "Mont Houy", 3000),
            ("Rouen B", "ROB", "Stade Mermoz", 3000), ("Epinal", "EPI", "La Colombiere", 7600),
        ],
    },
    {
        "name": "National 2", "tier": 4, "avg_budget": 350000, "avg_wage": 1400, "avg_reputation": 25, "ticket_price": 10,
        "sponsor_range": (1200, 3500), "max_debt": 120000, "promotion_places": 1, "playoff_places": [2, 3, 4], "relegation_places": 4,
        "clubs": [
            ("Angouleme CFC", "ANG", "Stade Chanzy", 10000), ("AS Beauvais", "BEA", "Stade Pierre Brisson", 10178), ("Lyon-Duchere", "LYD", "Stade Laurent Gerin", 3500), ("Bergerac", "BER", "Costa Sapinho", 5000),
            ("Bourges", "BRG", "Jacques Rimbault", 7000), ("Chamalieres", "CHM", "Philippe Marcombes", 3500), ("Colmar", "COL", "Stade du Ladhof", 8000), ("Bastia-Borgo", "BBO", "Armand Cesari", 10000),
            ("FC Rouen B", "RBN", "Stade Mermoz", 2500), ("Les Herbiers", "HER", "Massonniere", 5000), ("SO Cholet", "CHO", "Stade Omnisports", 6000), ("Stade Briochin", "BRI", "Fred Aubert", 6000),
            ("US Creteil", "CRE", "Duvauchelle", 12150), ("Vannes", "VAN", "de la Rabine", 10800), ("Wasquehal", "WAS", "Henri Seron", 3500), ("Sete", "SET", "Louis Michel", 10000),
            ("Marignane Gignac", "MGF", "Rene Fenouillet", 3500), ("Saint-Quentin", "STQ", "Paul Debreze", 4000), ("RC Grasse", "GRA", "Perdigon", 5000), ("Frejus Saint-Raphael", "FSR", "Louis Hon", 4000),
        ],
    },
    {
        "name": "National 3", "tier": 5, "avg_budget": 160000, "avg_wage": 650, "avg_reputation": 18, "ticket_price": 7,
        "sponsor_range": (700, 1800), "max_debt": 70000, "promotion_places": 1, "playoff_places": [2, 3, 4], "relegation_places": 0,
        "clubs": [
            ("Ales", "ALE", "Pierre Pibarot", 3000), ("Belfort", "BEL", "Serzian", 3500), ("Besancon", "BES", "Léo Lagrange", 3500), ("Blois", "BLO", "Allées", 3000),
            ("Cannes", "CAN", "Pierre de Coubertin", 10000), ("Chartres", "CHA", "James Delarue", 4000), ("Dinan Lehon", "DIN", "Clos Gastel", 2500), ("Feignies Aulnoye", "FEI", "Didier Eloy", 3000),
            ("Furiani", "FUR", "Lucien Massiani", 3000), ("Haguenau", "HAG", "Parc des Sports", 5000), ("Jura Sud", "JUR", "Edouard Guillon", 3000), ("Le Puy", "LPU", "Massot", 4500),
            ("Macon", "MAC", "Pierre Guerin", 2500), ("Mulhouse", "MUL", "Stade de l'Ill", 11000), ("Romorantin", "ROM", "Jules Ladoumegue", 6000), ("Saint-Priest", "SPR", "Jacques Joly", 2500),
            ("Toulon", "TOU", "Bon Rencontre", 8000), ("Virois", "VIR", "Pierre Compte", 2500), ("Yzeure", "YZE", "Bellevue", 3000), ("Auxerre B", "AUB", "Abbe-Deschamps Annex", 2500),
        ],
    },
]

GERMANY_PYRAMID = [
    {"name": "Bundesliga", "tier": 1, "avg_budget": 85000000, "avg_wage": 80000, "avg_reputation": 79, "ticket_price": 39, "sponsor_range": (500000, 1700000), "max_debt": 220000000, "promotion_places": 0, "playoff_places": [], "relegation_places": 2,
     "clubs": [
         ("Bayern Munich", "FCB", "Allianz Arena", 75000), ("Borussia Dortmund", "BVB", "Signal Iduna Park", 81365), ("RB Leipzig", "RBL", "Red Bull Arena", 47069), ("Bayer Leverkusen", "B04", "BayArena", 30210),
         ("Eintracht Frankfurt", "SGE", "Deutsche Bank Park", 58000), ("Stuttgart", "VFB", "MHPArena", 60469), ("Wolfsburg", "WOB", "Volkswagen Arena", 30000), ("Borussia Monchengladbach", "BMG", "Borussia-Park", 54057),
         ("Hoffenheim", "TSG", "PreZero Arena", 30150), ("Freiburg", "SCF", "Europa-Park Stadion", 34700), ("Mainz 05", "M05", "Mewa Arena", 33305), ("Werder Bremen", "SVW", "Weserstadion", 42100),
         ("Union Berlin", "FCU", "Alte Forsterei", 22012), ("Augsburg", "FCA", "WWK Arena", 30660), ("Bochum", "BOC", "Vonovia Ruhrstadion", 26000), ("Heidenheim", "FCH", "Voith-Arena", 15000),
         ("St Pauli", "STP", "Millerntor", 29546), ("Holstein Kiel", "KIE", "Holstein-Stadion", 15034),
     ]},
    {"name": "2. Bundesliga", "tier": 2, "avg_budget": 9000000, "avg_wage": 12000, "avg_reputation": 58, "ticket_price": 24, "sponsor_range": (45000, 180000), "max_debt": 40000000, "promotion_places": 2, "playoff_places": [3], "relegation_places": 2,
     "clubs": [
         ("Hamburg", "HSV", "Volksparkstadion", 57000), ("Schalke 04", "S04", "Veltins-Arena", 62271), ("Hertha Berlin", "BSC", "Olympiastadion", 74000), ("Fortuna Dusseldorf", "F95", "Merkur Spiel-Arena", 54600),
         ("Hannover 96", "H96", "Heinz von Heiden Arena", 49000), ("Nurnberg", "FCN", "Max-Morlock-Stadion", 50000), ("Karlsruhe", "KSC", "Wildparkstadion", 34302), ("Paderborn", "SCP", "Home Deluxe Arena", 15000),
         ("Greuther Furth", "SGF", "Sportpark Ronhof", 16000), ("Kaiserslautern", "FCK", "Fritz-Walter-Stadion", 49780), ("Magdeburg", "FCM", "MDCC-Arena", 25000), ("Darmstadt 98", "D98", "Merck-Stadion", 17810),
         ("Eintracht Braunschweig", "EBS", "Eintracht-Stadion", 23325), ("Elversberg", "ELV", "Ursapharm-Arena", 10000), ("Preussen Munster", "PRM", "Preussenstadion", 15000), ("Ulm", "ULM", "Donaustadion", 19000),
         ("Koln", "KOE", "RheinEnergieStadion", 50000), ("Regensburg", "SSV", "Jahnstadion", 15210),
     ]},
    {"name": "3. Liga", "tier": 3, "avg_budget": 2200000, "avg_wage": 3500, "avg_reputation": 42, "ticket_price": 16, "sponsor_range": (12000, 50000), "max_debt": 9000000, "promotion_places": 2, "playoff_places": [3], "relegation_places": 4,
     "clubs": [
         ("1860 Munich", "M60", "Grunwalder Stadion", 15000), ("Saarbrucken", "FCS", "Ludwigspark", 16003), ("Dynamo Dresden", "SGD", "Rudolf-Harbig-Stadion", 32000), ("Arminia Bielefeld", "DSC", "SchucoArena", 27300),
         ("Erzgebirge Aue", "AUE", "Erzgebirgsstadion", 16183), ("Ingolstadt", "FCI", "Audi Sportpark", 15800), ("Hansa Rostock", "FCH", "Ostseestadion", 29000), ("Sandhausen", "SVS", "BWT-Stadion", 15000),
         ("Essen", "RWE", "Stadion an der Hafenstrasse", 19600), ("Mannheim", "SVW", "Carl-Benz-Stadion", 24000), ("Osnabruck", "OSN", "Bremer Brucke", 16667), ("Alemannia Aachen", "AAC", "Tivoli", 32960),
         ("Viktoria Koln", "VIK", "Sportpark Höhenberg", 10000), ("Unterhaching", "UNT", "Sportpark Unterhaching", 15053), ("Waldhof Mannheim", "WAL", "Carl-Benz-Stadion", 24000), ("Cottbus", "EFC", "Stadion der Freundschaft", 22528),
         ("Freiburg II", "FR2", "Möslestadion", 3000), ("Dortmund II", "DO2", "Rote Erde", 9999),
     ]},
    {"name": "Regionalliga", "tier": 4, "avg_budget": 500000, "avg_wage": 1400, "avg_reputation": 28, "ticket_price": 10, "sponsor_range": (1500, 5000), "max_debt": 150000, "promotion_places": 1, "playoff_places": [2, 3, 4], "relegation_places": 4,
     "clubs": [
         ("Kickers Offenbach", "KOF", "Sparda-Bank-Hessen-Stadion", 20500), ("Rot-Weiss Oberhausen", "RWO", "Niederrheinstadion", 18000), ("Lokomotive Leipzig", "LOK", "Bruno-Plache-Stadion", 12000), ("Energie Cottbus B", "ECB", "Parzellenstadion", 3500),
         ("Chemnitzer FC", "CFC", "Stadion an der Gellertstrasse", 15000), ("BFC Dynamo", "BFC", "Sportforum Hohenschönhausen", 10000), ("Wuppertaler SV", "WSV", "Stadion am Zoo", 23000), ("Rot-Weiss Erfurt", "RWE", "Steigerwaldstadion", 18599),
         ("Aalen", "AAL", "Centus Arena", 14500), ("Lubeck", "LUB", "Lohmuhle", 17000), ("Tsv Havelse", "HAV", "Wilhelm-Langrehr-Stadion", 3500), ("Furth II", "FU2", "Ronhof Annex", 3500),
         ("Stuttgarter Kickers", "STK", "GAZi-Stadion", 11500), ("Schweinfurt 05", "SWF", "Sachs-Stadion", 15060), ("Mainz II", "MZ2", "Bruchwegstadion", 3000), ("Babelsberg 03", "BAB", "Karl-Liebknecht-Stadion", 10000),
         ("Luckenwalde", "LUC", "Werner-Seelenbinder-Stadion", 5000), ("Aubstadt", "AUB", "NGN Arena", 3000), ("Norderstedt", "NOR", "Edmund-Plambeck-Stadion", 5000), ("Greifswald", "GRE", "Volksstadion", 4000),
     ]},
    {"name": "Oberliga", "tier": 5, "avg_budget": 180000, "avg_wage": 650, "avg_reputation": 18, "ticket_price": 7, "sponsor_range": (700, 1800), "max_debt": 70000, "promotion_places": 1, "playoff_places": [2, 3, 4], "relegation_places": 0,
     "clubs": [
         ("SSV Reutlingen", "REU", "Kreuzeiche", 15400), ("TeBe Berlin", "TEB", "Mommsenstadion", 15100), ("TuS Koblenz", "TUS", "Oberwerth", 9500), ("SV Meppen II", "ME2", "Hänsch Arena Annex", 2500),
         ("Germania Halberstadt", "HAL", "Friedensstadion", 5000), ("FC Homburg", "HOM", "Waldstadion", 15000), ("Wormatia Worms", "WOR", "Wormatia-Stadion", 5500), ("Bahlinger SC", "BAH", "Kaiserstuhlstadion", 4500),
         ("TSV Rain", "RAI", "Georg Weber Stadion", 3000), ("VfB Oldenburg", "OLD", "Marschweg-Stadion", 15400), ("SG Barockstadt", "BAR", "Johannisau", 4000), ("FC Memmingen", "MEM", "Arena", 5200),
         ("Bonner SC", "BON", "Sportpark Nord", 10500), ("SpVgg Bayreuth", "BAY", "Hans-Walter-Wild-Stadion", 21500), ("VfR Aalen", "VRA", "Centus Arena", 14000), ("Lichtenberg 47", "LIC", "Hans-Zoschke-Stadion", 10000),
         ("BSG Chemie Leipzig", "CHE", "Alfred-Kunze-Sportpark", 4999), ("FC 08 Villingen", "VIL", "MS Technologie Arena", 8000),
     ]},
]

ITALY_PYRAMID = [
    {"name": "Serie A", "tier": 1, "avg_budget": 72000000, "avg_wage": 72000, "avg_reputation": 77, "ticket_price": 38, "sponsor_range": (450000, 1500000), "max_debt": 220000000, "promotion_places": 0, "playoff_places": [], "relegation_places": 3,
     "clubs": [
         ("Inter", "INT", "San Siro", 75817), ("AC Milan", "MIL", "San Siro", 75817), ("Juventus", "JUV", "Allianz Stadium", 41507), ("Napoli", "NAP", "Diego Armando Maradona", 54726),
         ("Roma", "ROM", "Stadio Olimpico", 70634), ("Lazio", "LAZ", "Stadio Olimpico", 70634), ("Atalanta", "ATA", "Gewiss Stadium", 21000), ("Fiorentina", "FIO", "Artemio Franchi", 43147),
         ("Bologna", "BOL", "Renato Dall'Ara", 36462), ("Torino", "TOR", "Olimpico Grande Torino", 27958), ("Genoa", "GEN", "Luigi Ferraris", 36599), ("Sampdoria", "SAM", "Luigi Ferraris", 36599),
         ("Udinese", "UDI", "Bluenergy Stadium", 25132), ("Cagliari", "CAG", "Unipol Domus", 16416), ("Lecce", "LEC", "Via del Mare", 33876), ("Monza", "MON", "U-Power Stadium", 18568),
         ("Verona", "VER", "Bentegodi", 39211), ("Parma", "PAR", "Ennio Tardini", 27906), ("Como", "COM", "Giuseppe Sinigaglia", 13602), ("Empoli", "EMP", "Carlo Castellani", 16284),
     ]},
    {"name": "Serie B", "tier": 2, "avg_budget": 8000000, "avg_wage": 11000, "avg_reputation": 56, "ticket_price": 21, "sponsor_range": (35000, 140000), "max_debt": 35000000, "promotion_places": 2, "playoff_places": [3, 4, 5, 6], "relegation_places": 4,
     "clubs": [
         ("Palermo", "PAL", "Renzo Barbera", 36349), ("Bari", "BAR", "San Nicola", 58270), ("Spezia", "SPE", "Alberto Picco", 10336), ("Cremonese", "CRE", "Giovanni Zini", 16469),
         ("Venezia", "VEN", "Penzo", 11150), ("Pisa", "PIS", "Arena Garibaldi", 14500), ("Modena", "MOD", "Alberto Braglia", 21312), ("Catanzaro", "CAT", "Nicola Ceravolo", 14650),
         ("Cittadella", "CIT", "Pier Cesare Tombolato", 7623), ("Brescia", "BRE", "Mario Rigamonti", 19550), ("Reggiana", "REG", "Mapei Citta del Tricolore", 21525), ("Sudtirol", "SUD", "Druso", 5500),
         ("Mantova", "MAN", "Danilo Martelli", 14900), ("Cesena", "CES", "Dino Manuzzi", 23860), ("Frosinone", "FRO", "Benito Stirpe", 16227), ("Salernitana", "SAL", "Arechi", 37000),
         ("Sassuolo", "SAS", "Mapei Stadium", 21584), ("Carrarese", "CAR", "Dei Marmi", 5000), ("Cosenza", "COS", "San Vito", 24209), ("Sampdoria B", "SA2", "Mugnaini", 3000),
     ]},
    {"name": "Serie C", "tier": 3, "avg_budget": 1800000, "avg_wage": 3200, "avg_reputation": 40, "ticket_price": 14, "sponsor_range": (9000, 40000), "max_debt": 7000000, "promotion_places": 1, "playoff_places": [2, 3, 4, 5, 6], "relegation_places": 5,
     "clubs": [
         ("Padova", "PAD", "Euganeo", 32420), ("Triestina", "TRI", "Nereo Rocco", 28028), ("Vicenza", "VIC", "Romeo Menti", 17603), ("SPAL", "SPA", "Paolo Mazza", 16134),
         ("Pescara", "PES", "Adriatico", 24000), ("Perugia", "PER", "Renato Curi", 23625), ("Ternana", "TER", "Libero Liberati", 22000), ("Benevento", "BEN", "Ciro Vigorito", 16642),
         ("Avellino", "AVE", "Partenio", 26800), ("Catania", "CAT", "Angelo Massimino", 20016), ("Foggia", "FOG", "Pino Zaccheria", 25152), ("Trapani", "TRP", "Provinciale", 7500),
         ("Lucchese", "LUC", "Porta Elisa", 7400), ("Entella", "ENT", "Comunale di Chiavari", 5535), ("Arezzo", "ARE", "Citta di Arezzo", 13128), ("Rimini", "RIM", "Neri", 9786),
         ("Giugliano", "GIU", "Alberto De Cristofaro", 3000), ("Monopoli", "MON", "Vito Simone Veneziani", 7000),
     ]},
    {"name": "Serie D", "tier": 4, "avg_budget": 400000, "avg_wage": 1400, "avg_reputation": 26, "ticket_price": 10, "sponsor_range": (1200, 3500), "max_debt": 120000, "promotion_places": 1, "playoff_places": [2, 3, 4], "relegation_places": 4,
     "clubs": [
         ("Livorno", "LIV", "Armando Picchi", 19424), ("Casertana", "CAS", "Alberto Pinto", 12000), ("Siena", "SIE", "Artemio Franchi", 15373), ("Piacenza", "PIA", "Garilli", 21000),
         ("Varese", "VAR", "Franco Ossola", 10000), ("Ravenna", "RAV", "Benelli", 12020), ("Campobasso", "CAM", "Nuovo Romagnoli", 25000), ("Matera", "MAT", "XXI Settembre", 7600),
         ("Brindisi", "BRI", "Fanuzzi", 7600), ("Sorrento", "SOR", "Italia", 3600), ("Vibonese", "VIB", "Luigi Razza", 5500), ("Siracusa", "SIR", "Nicola De Simone", 6000),
         ("Asti", "AST", "Censin Bosia", 4000), ("Cavese", "CAV", "Simonetta Lamberti", 8000), ("L'Aquila", "AQU", "Gran Sasso", 10000), ("Ragusa", "RAG", "Aldo Campo", 3500),
         ("San Marino", "SAM", "Serravalle", 7000), ("Sambenedettese", "SAMB", "Riviera delle Palme", 13952),
     ]},
    {"name": "Eccellenza", "tier": 5, "avg_budget": 170000, "avg_wage": 650, "avg_reputation": 18, "ticket_price": 7, "sponsor_range": (700, 1800), "max_debt": 70000, "promotion_places": 1, "playoff_places": [2, 3, 4], "relegation_places": 0,
     "clubs": [
         ("Ancona", "ANC", "Del Conero", 23876), ("Pro Sesto", "PRS", "Breda", 4900), ("Pistoiese", "PIS", "Melani", 13000), ("Imolese", "IMO", "Romeo Galli", 3500),
         ("Prato", "PRA", "Lungobisenzio", 6000), ("Bra", "BRA", "Attilio Bravi", 3500), ("Nocerina", "NOC", "San Francesco", 7500), ("Vastese", "VAS", "Aragona", 5500),
         ("Mariglianese", "MAR", "Comunale", 3000), ("Lodigiani", "LOD", "Francesca Gianni", 4000), ("Sangiovannese", "SAN", "Virgilio Fedini", 7000), ("Legnano", "LEG", "Mari", 5000),
         ("Acireale", "ACI", "Aci e Galatea", 7000), ("Portici", "POR", "San Ciro", 5000), ("Chieri", "CHI", "De Paoli", 4000), ("Tivoli", "TIV", "Olindo Galli", 4500),
         ("Roma City", "RCY", "Riano Athletic Center", 3000), ("Sancataldese", "SCA", "Valentino Mazzola", 3500),
     ]},
]

LEAGUE_DATA = {
    "England": {"league_name": "National League", "tier": 5, "currency": "GBP", "clubs": ENGLAND_PYRAMID[-1]["clubs"], "avg_budget": ENGLAND_PYRAMID[-1]["avg_budget"], "avg_wage": ENGLAND_PYRAMID[-1]["avg_wage"], "avg_reputation": ENGLAND_PYRAMID[-1]["avg_reputation"], "ticket_price": ENGLAND_PYRAMID[-1]["ticket_price"], "sponsor_range": ENGLAND_PYRAMID[-1]["sponsor_range"], "max_debt": ENGLAND_PYRAMID[-1]["max_debt"], "pyramid": ENGLAND_PYRAMID},
    "Spain": {"league_name": "Tercera Federacion", "tier": 5, "currency": "EUR", "clubs": SPAIN_PYRAMID[-1]["clubs"], "avg_budget": SPAIN_PYRAMID[-1]["avg_budget"], "avg_wage": SPAIN_PYRAMID[-1]["avg_wage"], "avg_reputation": SPAIN_PYRAMID[-1]["avg_reputation"], "ticket_price": SPAIN_PYRAMID[-1]["ticket_price"], "sponsor_range": SPAIN_PYRAMID[-1]["sponsor_range"], "max_debt": SPAIN_PYRAMID[-1]["max_debt"], "pyramid": SPAIN_PYRAMID},
    "France": {"league_name": "National 3", "tier": 5, "currency": "EUR", "clubs": FRANCE_PYRAMID[-1]["clubs"], "avg_budget": FRANCE_PYRAMID[-1]["avg_budget"], "avg_wage": FRANCE_PYRAMID[-1]["avg_wage"], "avg_reputation": FRANCE_PYRAMID[-1]["avg_reputation"], "ticket_price": FRANCE_PYRAMID[-1]["ticket_price"], "sponsor_range": FRANCE_PYRAMID[-1]["sponsor_range"], "max_debt": FRANCE_PYRAMID[-1]["max_debt"], "pyramid": FRANCE_PYRAMID},
    "Germany": {"league_name": "Oberliga", "tier": 5, "currency": "EUR", "clubs": GERMANY_PYRAMID[-1]["clubs"], "avg_budget": GERMANY_PYRAMID[-1]["avg_budget"], "avg_wage": GERMANY_PYRAMID[-1]["avg_wage"], "avg_reputation": GERMANY_PYRAMID[-1]["avg_reputation"], "ticket_price": GERMANY_PYRAMID[-1]["ticket_price"], "sponsor_range": GERMANY_PYRAMID[-1]["sponsor_range"], "max_debt": GERMANY_PYRAMID[-1]["max_debt"], "pyramid": GERMANY_PYRAMID},
    "Italy": {"league_name": "Eccellenza", "tier": 5, "currency": "EUR", "clubs": ITALY_PYRAMID[-1]["clubs"], "avg_budget": ITALY_PYRAMID[-1]["avg_budget"], "avg_wage": ITALY_PYRAMID[-1]["avg_wage"], "avg_reputation": ITALY_PYRAMID[-1]["avg_reputation"], "ticket_price": ITALY_PYRAMID[-1]["ticket_price"], "sponsor_range": ITALY_PYRAMID[-1]["sponsor_range"], "max_debt": ITALY_PYRAMID[-1]["max_debt"], "pyramid": ITALY_PYRAMID},
}


def generate_player_name(country):
    firsts, lasts = NAME_POOLS.get(country, NAME_POOLS["England"])
    return random.choice(firsts), random.choice(lasts)


def generate_player(country, position, tier_level, age=None):
    first, last = generate_player_name(country)
    if age is None:
        age = random.randint(17, 35)
    rating_floor = {1: 58, 2: 48, 3: 38, 4: 28, 5: 18}.get(tier_level, 18)
    rating_ceiling = {1: 88, 2: 75, 3: 66, 4: 58, 5: 50}.get(tier_level, 50)
    if age < 21:
        rating_ceiling += 3
    if age > 31:
        rating_ceiling -= 3
    overall_target = random.randint(max(10, rating_floor), max(rating_floor + 1, rating_ceiling))

    def clamp99(v):
        return max(1, min(99, v))

    if position == Position.GK:
        goalkeeping = clamp99(overall_target + random.randint(3, 10))
        defending = clamp99(overall_target + random.randint(-6, 4))
        passing = clamp99(overall_target + random.randint(-8, 4))
        shooting = clamp99(overall_target + random.randint(-18, -4))
        pace = clamp99(overall_target + random.randint(-10, 3))
        physical = clamp99(overall_target + random.randint(-4, 6))
    elif position == Position.DEF:
        goalkeeping = clamp99(random.randint(1, 8))
        defending = clamp99(overall_target + random.randint(2, 10))
        passing = clamp99(overall_target + random.randint(-6, 5))
        shooting = clamp99(overall_target + random.randint(-10, 2))
        pace = clamp99(overall_target + random.randint(-4, 6))
        physical = clamp99(overall_target + random.randint(0, 8))
    elif position == Position.MID:
        goalkeeping = clamp99(random.randint(1, 8))
        defending = clamp99(overall_target + random.randint(-4, 6))
        passing = clamp99(overall_target + random.randint(2, 10))
        shooting = clamp99(overall_target + random.randint(-3, 7))
        pace = clamp99(overall_target + random.randint(-3, 6))
        physical = clamp99(overall_target + random.randint(-2, 6))
    else:
        goalkeeping = clamp99(random.randint(1, 8))
        defending = clamp99(overall_target + random.randint(-10, 2))
        passing = clamp99(overall_target + random.randint(-4, 6))
        shooting = clamp99(overall_target + random.randint(2, 10))
        pace = clamp99(overall_target + random.randint(0, 8))
        physical = clamp99(overall_target + random.randint(-2, 7))

    player = Player(id=str(uuid.uuid4())[:8], first_name=first, last_name=last, age=age, nationality=country, position=position, goalkeeping=goalkeeping, defending=defending, passing=passing, shooting=shooting, pace=pace, physical=physical)
    ovr = player.overall
    player.value = int(max(2500, ovr * ovr * random.randint(350, 1400)))
    player.wage = int(max(80, ovr * random.randint(8, 40)))
    player.contract_years = random.randint(1, 4)
    player.potential = min(99, max(ovr, ovr + random.randint(2, 12)))
    return player


def generate_squad(country, tier):
    squad = []
    for pos, count in [(Position.GK, 3), (Position.DEF, 8), (Position.MID, 8), (Position.FWD, 6)]:
        for _ in range(count):
            squad.append(generate_player(country, pos, tier))
    return squad


def create_ai_club(name, short_name, country, stadium, capacity, league_data):
    tier = league_data["tier"]
    rep_base = league_data["avg_reputation"]
    reputation = max(5, min(90, rep_base + random.randint(-10, 10)))
    budget = int(league_data["avg_budget"] * random.uniform(0.6, 1.5))
    wage_budget = int(league_data["avg_wage"] * 25 * random.uniform(0.7, 1.3))
    sponsor_lo, sponsor_hi = league_data["sponsor_range"]
    sponsor = random.randint(sponsor_lo, sponsor_hi)
    club = Club(id=str(uuid.uuid4())[:8], name=name, short_name=short_name, country=country, league_tier=tier, reputation=reputation, budget=budget, wage_budget_weekly=wage_budget, stadium_name=stadium, stadium_capacity=capacity, sponsor_income_weekly=sponsor, ticket_price=league_data["ticket_price"], max_debt=league_data["max_debt"])
    club.players = generate_squad(country, tier)
    club.tactic = Tactic(formation=random.choice(list(Formation)), mentality=random.choice(list(Mentality)), style=random.choice(list(PlayStyle)))
    club.infrastructure.stadium.seating_level = min(10, max(1, 1 + (6 - tier)))
    club.infrastructure.stadium.pitch_quality = min(10, max(2, 2 + (6 - tier)))
    club.infrastructure.stadium.facilities_level = min(10, max(2, 2 + (6 - tier)))
    club.infrastructure.training.level = min(10, max(2, 2 + (6 - tier)))
    club.infrastructure.training.medical_level = min(10, max(2, 2 + (6 - tier)))
    club.infrastructure.training.training_ground_level = min(10, max(2, 2 + (6 - tier)))
    club.infrastructure.youth.level = min(10, max(2, 2 + (6 - tier)))
    club.infrastructure.youth.recruitment_level = min(10, max(2, 2 + (6 - tier)))
    club.infrastructure.youth.scouting_level = min(10, max(2, 2 + (6 - tier)))
    return club


def create_player_club(name, short_name, country, stadium_name):
    league_data = LEAGUE_DATA[country]
    tier = league_data["tier"]
    budget = int(league_data["avg_budget"] * 0.5)
    wage_budget = int(league_data["avg_wage"] * 18)
    sponsor_lo, sponsor_hi = league_data["sponsor_range"]
    sponsor = random.randint(sponsor_lo, int((sponsor_lo + sponsor_hi) / 2))
    club = Club(id=str(uuid.uuid4())[:8], name=name, short_name=short_name, country=country, league_tier=tier, reputation=max(5, league_data["avg_reputation"] - 8), budget=budget, wage_budget_weekly=wage_budget, stadium_name=stadium_name, stadium_capacity=3000, is_player_club=True, sponsor_income_weekly=sponsor, ticket_price=league_data["ticket_price"], max_debt=int(league_data["max_debt"] * 0.6))
    club.players = generate_squad(country, tier)
    for p in club.players:
        for attr_name in ("defending", "passing", "shooting", "pace", "physical", "goalkeeping"):
            setattr(p, attr_name, max(1, getattr(p, attr_name) - random.randint(0, 4)))
        p.value = int(max(2500, p.overall * p.overall * random.randint(250, 900)))
        p.wage = int(max(60, p.overall * random.randint(6, 25)))
        p.potential = min(99, max(p.overall, p.overall + random.randint(1, 10)))
    club.infrastructure.stadium.seating_level = 1
    club.infrastructure.stadium.pitch_quality = 3
    club.infrastructure.stadium.facilities_level = 2
    club.infrastructure.training.level = 3
    club.infrastructure.training.medical_level = 2
    club.infrastructure.youth.level = 3
    club.infrastructure.youth.recruitment_level = 3
    club.infrastructure.youth.scouting_level = 2
    return club


def setup_league(country, player_club):
    league_data = LEAGUE_DATA[country]
    clubs = {}
    for name, short, stadium, cap in league_data["clubs"]:
        club = create_ai_club(name, short, country, stadium, cap, league_data)
        clubs[club.id] = club
    clubs[player_club.id] = player_club
    league = LeagueSeason(name=league_data["league_name"], country=country, tier=league_data["tier"], club_ids=list(clubs.keys()))
    return clubs, league


def setup_league_system(country, player_club):
    data = LEAGUE_DATA[country]
    pyramid = data.get("pyramid")
    if not pyramid:
        clubs, league = setup_league(country, player_club)
        league_system = [LeagueTier(country=country, name=league.name, tier=league.tier, club_ids=list(league.club_ids), promotion_places=1)]
        return clubs, league, league_system

    all_clubs = {}
    tiers = []
    active_league = None
    for tier_data in pyramid:
        tier_club_ids = []
        for name, short, stadium, cap in tier_data["clubs"]:
            club = create_ai_club(name, short, country, stadium, cap, tier_data)
            all_clubs[club.id] = club
            tier_club_ids.append(club.id)
        if tier_data["tier"] == player_club.league_tier:
            all_clubs[player_club.id] = player_club
            if tier_club_ids:
                tier_club_ids = tier_club_ids[:-1]
            tier_club_ids.append(player_club.id)
            active_league = LeagueSeason(name=tier_data["name"], country=country, tier=tier_data["tier"], club_ids=list(tier_club_ids))
        tiers.append(LeagueTier(country=country, name=tier_data["name"], tier=tier_data["tier"], club_ids=list(tier_club_ids), promotion_places=tier_data.get("promotion_places", 0), playoff_places=list(tier_data.get("playoff_places", [])), relegation_places=tier_data.get("relegation_places", 0)))
    return all_clubs, active_league, tiers
