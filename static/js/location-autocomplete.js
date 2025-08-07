/**
 * Location Autocomplete for Country and City Fields
 * Provides typeahead functionality for country/city selection
 */

// Country data - comprehensive list of countries
const countries = [
    'Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola', 'Argentina', 'Armenia', 'Australia', 
    'Austria', 'Azerbaijan', 'Bahrain', 'Bangladesh', 'Belarus', 'Belgium', 'Bolivia', 'Bosnia and Herzegovina',
    'Brazil', 'Bulgaria', 'Cambodia', 'Canada', 'Chile', 'China', 'Colombia', 'Costa Rica', 'Croatia',
    'Czech Republic', 'Denmark', 'Ecuador', 'Egypt', 'Estonia', 'Finland', 'France', 'Georgia', 'Germany',
    'Ghana', 'Greece', 'Hungary', 'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Israel',
    'Italy', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kuwait', 'Latvia', 'Lebanon', 'Lithuania', 'Luxembourg',
    'Malaysia', 'Mexico', 'Morocco', 'Netherlands', 'New Zealand', 'Nigeria', 'Norway', 'Pakistan', 'Peru',
    'Philippines', 'Poland', 'Portugal', 'Qatar', 'Romania', 'Russia', 'Saudi Arabia', 'Singapore', 'Slovakia',
    'Slovenia', 'South Africa', 'South Korea', 'Spain', 'Sri Lanka', 'Sweden', 'Switzerland', 'Taiwan',
    'Thailand', 'Turkey', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States', 'Uruguay',
    'Venezuela', 'Vietnam'
];

// Cities data organized by country
const citiesByCountry = {
    'United States': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose', 'Austin', 'Jacksonville', 'San Francisco', 'Columbus', 'Charlotte', 'Fort Worth', 'Detroit', 'El Paso', 'Memphis', 'Seattle', 'Denver', 'Washington DC', 'Boston', 'Nashville', 'Baltimore', 'Oklahoma City', 'Louisville', 'Portland', 'Las Vegas', 'Milwaukee', 'Albuquerque', 'Tucson', 'Fresno', 'Sacramento', 'Long Beach', 'Kansas City', 'Mesa', 'Atlanta', 'Colorado Springs', 'Raleigh', 'Omaha', 'Miami', 'Oakland', 'Minneapolis', 'Tulsa', 'Cleveland', 'Wichita', 'Arlington', 'New Orleans', 'Bakersfield', 'Tampa', 'Honolulu', 'Anaheim', 'Aurora', 'Santa Ana', 'St. Louis', 'Riverside', 'Corpus Christi', 'Lexington', 'Pittsburgh', 'Anchorage', 'Stockton', 'Cincinnati', 'St. Paul', 'Toledo', 'Greensboro', 'Newark', 'Plano', 'Henderson', 'Lincoln', 'Buffalo', 'Jersey City', 'Chula Vista', 'Fort Wayne', 'Orlando', 'St. Petersburg', 'Chandler', 'Laredo', 'Norfolk', 'Durham', 'Madison', 'Lubbock', 'Irvine', 'Winston-Salem', 'Glendale', 'Garland', 'Hialeah', 'Reno', 'Chesapeake', 'Gilbert', 'Baton Rouge', 'Irving', 'Scottsdale', 'North Las Vegas', 'Fremont', 'Boise', 'Richmond', 'San Bernardino', 'Birmingham', 'Spokane', 'Rochester', 'Des Moines', 'Modesto', 'Fayetteville', 'Tacoma', 'Oxnard', 'Fontana', 'Columbus', 'Montgomery', 'Moreno Valley', 'Shreveport', 'Aurora', 'Yonkers', 'Akron', 'Huntington Beach', 'Little Rock', 'Augusta', 'Amarillo', 'Glendale', 'Mobile', 'Grand Rapids', 'Salt Lake City', 'Tallahassee', 'Huntsville', 'Grand Prairie', 'Knoxville', 'Worcester', 'Newport News', 'Brownsville', 'Overland Park', 'Santa Clarita', 'Providence', 'Garden Grove', 'Chattanooga', 'Oceanside', 'Jackson', 'Fort Lauderdale', 'Santa Rosa', 'Rancho Cucamonga', 'Port St. Lucie', 'Tempe', 'Ontario', 'Vancouver', 'Cape Coral', 'Sioux Falls', 'Springfield', 'Peoria', 'Pembroke Pines', 'Elk Grove', 'Salem', 'Lancaster', 'Corona', 'Eugene', 'Palmdale', 'Salinas', 'Springfield', 'Pasadena', 'Fort Collins', 'Hayward', 'Pomona', 'Cary', 'Rockford', 'Alexandria', 'Escondido', 'McKinney', 'Kansas City', 'Joliet', 'Sunnyvale', 'Torrance', 'Bridgeport', 'Lakewood', 'Hollywood', 'Paterson', 'Naperville', 'Syracuse', 'Mesquite', 'Dayton', 'Savannah', 'Clarksville', 'Orange', 'Pasadena', 'Fullerton', 'Killeen', 'Frisco', 'Hampton', 'McAllen', 'Warren', 'Bellevue', 'West Valley City', 'Columbia', 'Olathe', 'Sterling Heights', 'New Haven', 'Miramar', 'Waco', 'Thousand Oaks', 'Cedar Rapids', 'Charleston', 'Visalia', 'Topeka', 'Elizabeth', 'Gainesville', 'Thornton', 'Roseville', 'Carrollton', 'Coral Springs', 'Stamford', 'Simi Valley', 'Concord', 'Hartford', 'Kent', 'Lafayette', 'Midland', 'Surprise', 'Denton', 'Victorville', 'Evansville', 'Santa Clara', 'Abilene', 'Athens', 'Vallejo', 'Allentown', 'Norman', 'Beaumont', 'Independence', 'Murfreesboro', 'Ann Arbor', 'Fargo', 'Wilmington', 'Provo', 'Lee\'s Summit', 'Peoria', 'Inglewood', 'Fairfield', 'Billings', 'Carlsbad', 'West Palm Beach', 'Columbia', 'El Monte', 'Berkeley', 'Arvada', 'Green Bay', 'Cambridge', 'Clearwater', 'West Jordan', 'Westminster', 'Lowell', 'Temecula', 'Richardson', 'Pueblo', 'Elgin', 'Round Rock', 'Broken Arrow', 'Richmond', 'League City', 'Manchester', 'Lakeland', 'Carlsbad', 'Antioch', 'Norwalk', 'Burbank', 'Rialto', 'Allen', 'El Cajon', 'Las Cruces', 'Renton', 'Davenport', 'South Bend', 'Pearland', 'Roanoke', 'Pompano Beach', 'Jurupa Valley', 'Compton', 'Livermore', 'Brockton', 'Palmdale', 'Woodbridge', 'Hillsboro', 'Lansing', 'Greeley', 'Ventura', 'High Point', 'Everett', 'Richmond', 'Miami Gardens', 'Murrieta', 'Sparks', 'Bend', 'Lewisville', 'West Covina', 'Centennial', 'Odessa', 'Tyler', 'Norwalk', 'Pueblo', 'Gresham', 'Daly City', 'Meridian', 'Burbank', 'Fishers', 'Carmel', 'Sugar Land', 'Edinburg', 'Sandy Springs', 'Clovis', 'Beaumont', 'Menifee', 'Chandler', 'Broomfield', 'Nampa', 'Chico', 'Avondale', 'Redding', 'Hawthorne', 'Lakewood', 'Cicero', 'Kenosha', 'Champaign', 'Quincy', 'Ogden', 'Racine', 'Tuscaloosa', 'Decatur', 'Bloomington', 'Napa', 'Longmont', 'Southfield', 'Pontiac', 'Livonia', 'Buena Park', 'Bellingham', 'Roswell', 'Danbury', 'Yakima', 'Kalamazoo', 'Appleton', 'Gastonia', 'Goodyear', 'Waterloo', 'Edmond', 'Somerville', 'Medford', 'Citrus Heights', 'Largo', 'Westland', 'Freeport', 'Beaverton', 'Plantation', 'Waukegan', 'Jonesboro', 'Asheville', 'Eagan', 'Bethlehem', 'Whittier', 'Coon Rapids', 'Minnetonka', 'Schaumburg', 'Eau Claire', 'Clifton', 'Warwick', 'Hoover', 'Merced', 'Blaine', 'Springdale', 'Walnut Creek', 'Dayton', 'Youngstown', 'Nashua', 'Concord', 'Bellevue', 'Manteca', 'Lakeville', 'Bloomington', 'Redwood City', 'Muncie', 'Bowling Green', 'Greenville', 'Bayonne', 'Wheaton', 'Fond du Lac', 'Janesville', 'Lynchburg', 'Gulfport', 'Duluth', 'Bloomington', 'Boynton Beach', 'Delray Beach', 'Macon', 'Bloomington', 'Noblesville', 'Cranston', 'Dubuque', 'Malden', 'Homestead', 'Moline', 'Waukesha', 'Hoboken', 'Burnsville', 'Dearborn', 'Novi', 'Farmington Hills', 'Edina', 'Sheboygan', 'Evanston', 'Tinley Park', 'Berwyn', 'Plainfield', 'Hoffman Estates', 'Orland Park', 'Bolingbrook', 'Palatine', 'Skokie', 'Wheeling', 'Rockford', 'Joliet', 'Peoria', 'Champaign', 'Urbana', 'Bloomington', 'Rockville', 'Gaithersburg', 'Bowie', 'Hagerstown', 'Annapolis', 'Frederick', 'Towson', 'Catonsville', 'Dundalk', 'Ellicott City', 'Essex', 'Glen Burnie', 'Parole', 'Pikesville', 'Severn', 'Severna Park', 'Woodlawn', 'Arbutus', 'Cockeysville', 'Eldersburg', 'Lansdowne', 'Lochearn', 'Lutherville', 'Owings Mills', 'Parkville', 'Randallstown', 'Reisterstown', 'Rosedale', 'Timonium', 'West Elkridge', 'Westview', 'Woodlawn'],
    'Canada': ['Toronto', 'Montreal', 'Calgary', 'Ottawa', 'Edmonton', 'Mississauga', 'Winnipeg', 'Vancouver', 'Brampton', 'Hamilton', 'Quebec City', 'Surrey', 'Laval', 'Halifax', 'London', 'Markham', 'Vaughan', 'Gatineau', 'Saskatoon', 'Longueuil', 'Kitchener', 'Burnaby', 'Windsor', 'Regina', 'Richmond', 'Richmond Hill', 'Oakville', 'Burlington', 'Sherbrooke', 'Oshawa', 'Saguenay', 'Levis', 'Barrie', 'Abbotsford', 'Coquitlam', 'Trois-Rivières', 'St. Catharines', 'Guelph', 'Cambridge', 'Whitby', 'Kelowna', 'Kingston', 'Ajax', 'Langley', 'Saanich', 'Terrebonne', 'Milton', 'St. John\'s', 'Moncton', 'Thunder Bay', 'Dieppe', 'Waterloo', 'Delta', 'Chatham', 'Red Deer', 'Strathcona County', 'Brantford', 'Saint-Jean-sur-Richelieu', 'Lethbridge', 'Kamloops', 'Airdrie', 'Halton Hills', 'Saint John', 'Dollard-des-Ormeaux', 'Fredericton', 'Sudbury', 'Repentigny', 'Pickering', 'Sault Ste. Marie', 'Sarnia', 'Wood Buffalo', 'New Westminster', 'Châteauguay', 'Saint-Jérôme', 'Drummondville', 'Granby', 'Saint-Hyacinthe', 'Shawinigan', 'Victoriaville', 'Joliette', 'Sorel-Tracy', 'Rimouski', 'Salaberry-de-Valleyfield', 'Val-d\'Or', 'Timmins', 'Rouyn-Noranda', 'Sept-Îles', 'Chicoutimi', 'Jonquière', 'Alma', 'Baie-Comeau', 'Dolbeau-Mistassini', 'Roberval', 'Kapuskasing', 'Hearst', 'Iroquois Falls', 'Cochrane', 'Smooth Rock Falls', 'Moosonee', 'Moose Factory', 'Attawapiskat', 'Kashechewan', 'Fort Albany', 'Peawanuck', 'Webequie', 'Kingfisher Lake', 'Wunnumin Lake', 'Lansdowne House', 'Pickle Lake', 'Cat Lake', 'Slate Falls', 'Sachigo Lake', 'Kasabonika Lake', 'Sandy Lake', 'Deer Lake', 'North Spirit Lake', 'Keewaywin', 'Muskrat Dam', 'Wapekeka', 'Saugeen', 'Neskantaga', 'Eabametoong', 'Nibinamik', 'Bearskin Lake', 'Weagamow Lake', 'Kasabonika', 'Poplar Hill', 'Pikangikum', 'Bloodvein', 'Little Grand Rapids', 'Pauingassi', 'Berens River', 'Poplar River', 'Negginan', 'Hollow Water', 'Manigotagan', 'Seymourville', 'Bissett', 'Lac du Bonnet', 'Pinawa', 'Taché', 'Lorette', 'Niverville', 'Blumenort', 'Kleefeld', 'Grunthal', 'Steinbach', 'Mitchell', 'Hanover', 'Landmark', 'Dugald', 'Anola', 'Libau', 'Beausejour', 'Tyndall', 'Garson', 'Selkirk', 'Petersfield', 'Clandeboye', 'Netley', 'Balmoral', 'Argyle', 'Grosse Isle', 'Rosser', 'Stonewall', 'Teulon', 'Woodlands', 'Marquette', 'Headingley', 'Cartier', 'Elie', 'Springstein', 'Brunkild', 'Sanford', 'Sperling', 'Carman', 'Elm Creek', 'Winkler', 'Morden', 'Altona', 'Gretna', 'Emerson', 'Dominion City', 'Vita', 'Stuartburn', 'Piney', 'Taché', 'Lorette', 'Niverville', 'Blumenort', 'Kleefeld', 'Grunthal', 'Steinbach', 'Mitchell', 'Hanover', 'Landmark', 'Dugald', 'Anola', 'Libau', 'Beausejour', 'Tyndall', 'Garson', 'Selkirk', 'Petersfield', 'Clandeboye', 'Netley', 'Balmoral', 'Argyle', 'Grosse Isle', 'Rosser', 'Stonewall', 'Teulon', 'Woodlands', 'Marquette', 'Headingley', 'Cartier', 'Elie', 'Springstein', 'Brunkild', 'Sanford', 'Sperling', 'Carman', 'Elm Creek', 'Winkler', 'Morden', 'Altona', 'Gretna', 'Emerson', 'Dominion City', 'Vita', 'Stuartburn', 'Piney'],
    'India': ['Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 'Pune', 'Ahmedabad', 'Surat', 'Jaipur', 'Lucknow', 'Kanpur', 'Nagpur', 'Indore', 'Thane', 'Bhopal', 'Visakhapatnam', 'Pimpri-Chinchwad', 'Patna', 'Vadodara', 'Ghaziabad', 'Ludhiana', 'Agra', 'Nashik', 'Faridabad', 'Meerut', 'Rajkot', 'Kalyan-Dombivli', 'Vasai-Virar', 'Varanasi', 'Srinagar', 'Aurangabad', 'Dhanbad', 'Amritsar', 'Navi Mumbai', 'Allahabad', 'Ranchi', 'Howrah', 'Coimbatore', 'Jabalpur', 'Gwalior', 'Vijayawada', 'Jodhpur', 'Madurai', 'Raipur', 'Kota', 'Guwahati', 'Chandigarh', 'Solapur', 'Hubli-Dharwad', 'Bareilly', 'Moradabad', 'Mysore', 'Gurgaon', 'Aligarh', 'Jalandhar', 'Tiruchirappalli', 'Bhubaneswar', 'Salem', 'Mira-Bhayandar', 'Warangal', 'Thiruvananthapuram', 'Guntur', 'Bhiwandi', 'Saharanpur', 'Gorakhpur', 'Bikaner', 'Amravati', 'Noida', 'Jamshedpur', 'Bhilai', 'Cuttack', 'Firozabad', 'Kochi', 'Nellore', 'Bhavnagar', 'Dehradun', 'Durgapur', 'Asansol', 'Rourkela', 'Nanded', 'Kolhapur', 'Ajmer', 'Akola', 'Gulbarga', 'Jamnagar', 'Ujjain', 'Loni', 'Siliguri', 'Jhansi', 'Ulhasnagar', 'Jammu', 'Sangli-Miraj & Kupwad', 'Mangalore', 'Erode', 'Belgaum', 'Ambattur', 'Tirunelveli', 'Malegaon', 'Gaya', 'Jalgaon', 'Udaipur', 'Maheshtala', 'Davanagere', 'Kozhikode', 'Kurnool', 'Rajpur Sonarpur', 'Rajahmundry', 'Bokaro', 'South Dumdum', 'Bellary', 'Patiala', 'Gopalpur', 'Agartala', 'Bhagalpur', 'Muzaffarnagar', 'Bhatpara', 'Panihati', 'Latur', 'Dhule', 'Rohtak', 'Korba', 'Bhilwara', 'Berhampur', 'Muzaffarpur', 'Ahmednagar', 'Mathura', 'Kollam', 'Avadi', 'Kadapa', 'Kamarhati', 'Sambalpur', 'Bilaspur', 'Shahjahanpur', 'Satara', 'Bijapur', 'Rampur', 'Shivamogga', 'Chandrapur', 'Junagadh', 'Thrissur', 'Alwar', 'Bardhaman', 'Kulti', 'Kakinada', 'Nizamabad', 'Parbhani', 'Tumkur', 'Khammam', 'Ozhukarai', 'Bihar Sharif', 'Panipat', 'Darbhanga', 'Bally', 'Aizawl', 'Dewas', 'Ichalkaranji', 'Karnal', 'Bathinda', 'Jalna', 'Eluru', 'Kirari Suleman Nagar', 'Barabanki', 'Purnia', 'Satna', 'Mau', 'Sonipat', 'Farrukhabad', 'Sagar', 'Rourkela', 'Durg', 'Imphal', 'Ratlam', 'Hapur', 'Arrah', 'Karimnagar', 'Anantapur', 'Etawah', 'Ambernath', 'North Dumdum', 'Bharatpur', 'Begusarai', 'New Delhi', 'Gandhidham', 'Baranagar', 'Tiruvottiyur', 'Puducherry', 'Sikar', 'Thoothukudi', 'Rewa', 'Mirzapur', 'Raichur', 'Pali', 'Ramagundam', 'Silchar', 'Jaunpur', 'Uluberia', 'Mango', 'Jalgaon', 'Singrauli', 'Vellore', 'Tezpur', 'Raigarh', 'Haldia', 'Khandwa', 'Morena', 'Amroha', 'Mahbubnagar', 'Saharsa', 'Dibrugarh', 'Jorhat', 'Nagaon', 'Tinsukia', 'Bongaigaon', 'Dhubri', 'Barpeta', 'Golaghat', 'Sivasagar', 'Lakhimpur', 'Diphu', 'Haflong', 'Karimganj', 'Hailakandi', 'Margherita', 'Digboi', 'Duliajan', 'Naharkatiya', 'Doom Dooma', 'Doomdooma', 'Chabua', 'Sonari', 'Silapathar', 'Dhemaji', 'Jonai', 'Dergaon', 'Kaliabor', 'Raha', 'Chaparmukh', 'Jagiroad', 'Marigaon', 'Laharighat', 'Dharamtul', 'Sonitpur', 'Tezpur', 'Rangapara', 'Biswanath Chariali', 'Behali', 'Jamuguri', 'Gohpur', 'Morigaon', 'Nalbari', 'Mushalpur', 'Boko', 'Chaygaon', 'Hajo', 'Sualkuchi', 'Rangia', 'Khoirabari', 'Pub-Kamrup', 'Nagarbera', 'Tarabari', 'Azara', 'Palashbari', 'Chandrapur', 'Kamrup', 'Bhuragaon', 'Palasbari', 'Hajo', 'Sualkuchi', 'Rangia', 'Khoirabari', 'Pub-Kamrup', 'Nagarbera', 'Tarabari', 'Azara', 'Palashbari', 'Chandrapur', 'Kamrup', 'Bhuragaon', 'Palasbari'],
    'United Kingdom': ['London', 'Birmingham', 'Manchester', 'Liverpool', 'Leeds', 'Sheffield', 'Bristol', 'Glasgow', 'Leicester', 'Edinburgh', 'Coventry', 'Bradford', 'Cardiff', 'Belfast', 'Nottingham', 'Hull', 'Newcastle upon Tyne', 'Stoke-on-Trent', 'Southampton', 'Derby', 'Portsmouth', 'Brighton', 'Plymouth', 'Northampton', 'Reading', 'Luton', 'Wolverhampton', 'Bolton', 'Bournemouth', 'Norwich', 'Swindon', 'Swansea', 'Southend-on-Sea', 'Middlesbrough', 'Peterborough', 'Oxford', 'Blackpool', 'Oldham', 'York', 'Poole', 'Ipswich', 'Preston', 'Stockport', 'Rotherham', 'Canterbury', 'Sutton Coldfield', 'St Helens', 'Exeter', 'Scunthorpe', 'Gateshead', 'Crawley', 'Watford', 'Slough', 'Doncaster', 'Dudley', 'Walsall', 'Telford', 'Sunderland', 'Gloucester', 'Grimsby', 'Woking', 'Basildon', 'Worthing', 'Rochdale', 'Solihull', 'Eastbourne', 'Chesterfield', 'Cheltenham', 'Warrington', 'Birkenhead', 'Darlington', 'Hartlepool', 'Hemel Hempstead', 'Barnsley', 'Maidstone', 'Stockton-on-Tees', 'Blackburn', 'Colchester', 'Redditch', 'Lincoln', 'Carlisle', 'Southport', 'Lowestoft', 'Nuneaton', 'Bangor', 'Wrexham', 'Mansfield', 'Gillingham', 'Tamworth', 'Chelmsford', 'Burnley', 'Rhondda', 'Gloucester', 'Wigan', 'Stevenage', 'Chatham', 'Shrewsbury', 'Basingstoke', 'Hastings', 'Kidderminster', 'Aylesbury', 'Carlisle', 'Harlow', 'Folkestone', 'Welwyn Garden City', 'Runcorn', 'Stafford', 'Scarborough', 'Loughborough', 'Widnes', 'Bracknell', 'Hereford', 'Banbury', 'Crewe', 'Weston-super-Mare', 'Rugby', 'Kettering', 'Taunton', 'Aldershot', 'Gravesend', 'Weymouth', 'Corby', 'Farnborough', 'Bognor Regis', 'Waterlooville', 'Merthyr Tydfil', 'Andover', 'Littlehampton', 'Yeovil', 'Paignton', 'Cannock', 'Workington', 'Margate', 'Cwmbran', 'Bridgend', 'Cheshunt', 'Fareham', 'Smethwick', 'Ellesmere Port', 'Salisbury', 'Rayleigh', 'Bishops Stortford', 'Acton', 'Bletchley', 'Braintree', 'Morecambe', 'Horsham', 'Grays', 'Maidenhead', 'Hinckley', 'Arnold', 'Farnham', 'Barrow-in-Furness', 'Chippenham', 'Grantham', 'Abingdon', 'Newbury', 'Beverley', 'Stroud', 'Tonbridge', 'Borehamwood', 'Leamington Spa', 'Stratford-upon-Avon', 'Walton-on-Thames', 'Warwick', 'Wellingborough', 'Wokingham', 'Reigate', 'Hertford', 'Kenilworth', 'Epsom', 'Dorking', 'Camberley', 'Redhill', 'Haywards Heath', 'Burgess Hill', 'Sevenoaks', 'Staines', 'Esher', 'Godalming', 'Egham', 'Leatherhead', 'Woking', 'Guildford', 'Farnham', 'Aldershot', 'Haslemere', 'Cranleigh', 'Oxted', 'Dorking', 'Reigate', 'Redhill', 'Tadworth', 'Banstead', 'Horley', 'Lingfield', 'Godstone', 'Caterham', 'Warlingham', 'Whyteleafe', 'Kenley', 'Coulsdon', 'Purley', 'Sanderstead', 'Selsdon', 'Addington', 'Shirley', 'Wickham', 'Croydon', 'Thornton Heath', 'Norbury', 'Streatham', 'Tooting', 'Mitcham', 'Morden', 'Wimbledon', 'Raynes Park', 'New Malden', 'Kingston upon Thames', 'Surbiton', 'Tolworth', 'Chessington', 'Epsom', 'Ewell', 'Stoneleigh', 'Worcester Park', 'Cheam', 'Sutton', 'Carshalton', 'Wallington', 'Beddington', 'Hackbridge', 'Banstead', 'Tadworth', 'Kingswood', 'Reigate', 'Redhill', 'Merstham', 'Gatwick', 'Horley', 'Salfords', 'Sidlow', 'Leigh', 'Betchworth', 'Brockham', 'Buckland', 'Dorking', 'Westcott', 'Holmwood', 'Capel', 'Ockley', 'Ewhurst', 'Cranleigh', 'Bramley', 'Shalford', 'Chilworth', 'Guildford', 'Merrow', 'Burpham', 'Jacobs Well', 'Woking', 'Knaphill', 'Mayford', 'Horsell', 'Pyrford', 'Byfleet', 'West Byfleet', 'Brookwood', 'Pirbright', 'Normandy', 'Ash', 'Ash Vale', 'Aldershot', 'Farnham', 'Wrecclesham', 'Rowledge', 'Frensham', 'Churt', 'Headley', 'Arford', 'Passfield', 'Conford', 'Whitehill', 'Bordon', 'Bramshott', 'Liphook', 'Haslemere', 'Shottermill', 'Hindhead', 'Beacon Hill', 'Grayswood', 'Witley', 'Milford', 'Godalming', 'Farncombe', 'Busbridge', 'Hascombe', 'Hambledon', 'Chiddingfold', 'Dunsfold', 'Alfold', 'Ifold', 'Loxwood', 'Wisborough Green', 'Billingshurst', 'Rudgwick', 'Bucks Green', 'Slinfold', 'Horsham', 'Broadbridge Heath', 'Warnham', 'Rusper', 'Faygate', 'Ifield', 'Crawley', 'Gatwick', 'Horley', 'Salfords', 'Sidlow', 'Leigh', 'Betchworth', 'Brockham', 'Buckland', 'Dorking', 'Westcott', 'Holmwood', 'Capel', 'Ockley', 'Ewhurst', 'Cranleigh', 'Bramley', 'Shalford', 'Chilworth', 'Guildford', 'Merrow', 'Burpham', 'Jacobs Well', 'Woking', 'Knaphill', 'Mayford', 'Horsell', 'Pyrford', 'Byfleet', 'West Byfleet', 'Brookwood', 'Pirbright', 'Normandy', 'Ash', 'Ash Vale', 'Aldershot', 'Farnham', 'Wrecclesham', 'Rowledge', 'Frensham', 'Churt', 'Headley', 'Arford', 'Passfield', 'Conford', 'Whitehill', 'Bordon', 'Bramshott', 'Liphook', 'Haslemere', 'Shottermill', 'Hindhead', 'Beacon Hill', 'Grayswood', 'Witley', 'Milford', 'Godalming', 'Farncombe', 'Busbridge', 'Hascombe', 'Hambledon', 'Chiddingfold', 'Dunsfold', 'Alfold', 'Ifold', 'Loxwood', 'Wisborough Green', 'Billingshurst', 'Rudgwick', 'Bucks Green', 'Slinfold', 'Horsham', 'Broadbridge Heath', 'Warnham', 'Rusper', 'Faygate', 'Ifield', 'Crawley'],
    'Germany': ['Berlin', 'Hamburg', 'Munich', 'Cologne', 'Frankfurt', 'Stuttgart', 'Düsseldorf', 'Dortmund', 'Essen', 'Leipzig', 'Bremen', 'Dresden', 'Hanover', 'Nuremberg', 'Duisburg', 'Bochum', 'Wuppertal', 'Bielefeld', 'Bonn', 'Münster', 'Karlsruhe', 'Mannheim', 'Augsburg', 'Wiesbaden', 'Gelsenkirchen', 'Mönchengladbach', 'Braunschweig', 'Chemnitz', 'Kiel', 'Aachen', 'Halle', 'Magdeburg', 'Freiburg', 'Krefeld', 'Lübeck', 'Oberhausen', 'Erfurt', 'Mainz', 'Rostock', 'Kassel', 'Hagen', 'Potsdam', 'Saarbrücken', 'Hamm', 'Mülheim an der Ruhr', 'Ludwigshafen', 'Leverkusen', 'Oldenburg', 'Neuss', 'Solingen', 'Heidelberg', 'Herne', 'Darmstadt', 'Paderborn', 'Regensburg', 'Ingolstadt', 'Würzburg', 'Fürth', 'Wolfsburg', 'Offenbach', 'Ulm', 'Heilbronn', 'Pforzheim', 'Göttingen', 'Bottrop', 'Trier', 'Recklinghausen', 'Reutlingen', 'Bremerhaven', 'Koblenz', 'Bergisch Gladbach', 'Jena', 'Remscheid', 'Erlangen', 'Moers', 'Siegen', 'Hildesheim', 'Salzgitter']
};

// Global variables to track current selections
let currentCountry = '';
let currentCity = '';

/**
 * Initialize autocomplete functionality for location inputs
 */
function initializeLocationAutocomplete() {
    // Initialize country autocomplete
    const countryInputs = document.querySelectorAll('input[name="country"]');
    countryInputs.forEach(input => {
        initializeCountryAutocomplete(input);
    });

    // Initialize city autocomplete
    const cityInputs = document.querySelectorAll('input[name="city"]');
    cityInputs.forEach(input => {
        initializeCityAutocomplete(input);
    });
}

/**
 * Initialize country autocomplete for a specific input
 */
function initializeCountryAutocomplete(input) {
    const dropdown = createDropdown(input, 'country');
    
    input.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        currentCountry = this.value;
        
        // Clear city when country changes
        const cityInput = this.closest('form').querySelector('input[name="city"]');
        if (cityInput) {
            cityInput.value = '';
            currentCity = '';
        }
        
        if (query.length < 2) {
            hideDropdown(dropdown);
            return;
        }
        
        const matches = countries.filter(country => 
            country.toLowerCase().includes(query)
        ).slice(0, 10);
        
        showDropdown(dropdown, matches, input, 'country');
    });
    
    // Hide dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !dropdown.contains(e.target)) {
            hideDropdown(dropdown);
        }
    });
}

/**
 * Initialize city autocomplete for a specific input
 */
function initializeCityAutocomplete(input) {
    const dropdown = createDropdown(input, 'city');
    
    input.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        currentCity = this.value;
        
        if (query.length < 2) {
            hideDropdown(dropdown);
            return;
        }
        
        // Get country from the form
        const countryInput = this.closest('form').querySelector('input[name="country"]');
        const selectedCountry = countryInput ? countryInput.value : '';
        
        let cities = [];
        if (selectedCountry && citiesByCountry[selectedCountry]) {
            cities = citiesByCountry[selectedCountry];
        } else {
            // If no country selected, search all cities
            cities = Object.values(citiesByCountry).flat();
        }
        
        const matches = cities.filter(city => 
            city.toLowerCase().includes(query)
        ).slice(0, 10);
        
        showDropdown(dropdown, matches, input, 'city');
    });
    
    // Hide dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !dropdown.contains(e.target)) {
            hideDropdown(dropdown);
        }
    });
}

/**
 * Create dropdown element for autocomplete
 */
function createDropdown(input, type) {
    const dropdown = document.createElement('div');
    dropdown.className = `autocomplete-dropdown ${type}-dropdown`;
    dropdown.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #dee2e6;
        border-top: none;
        border-radius: 0 0 0.375rem 0.375rem;
        box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
        max-height: 200px;
        overflow-y: auto;
        z-index: 9999;
        display: none;
        width: 100%;
        min-width: 200px;
    `;
    
    // Create wrapper for positioning - ensure it doesn't interfere with Bootstrap grid
    const wrapper = document.createElement('div');
    wrapper.className = 'location-autocomplete-wrapper';
    wrapper.style.cssText = `
        position: relative;
        display: block;
        width: 100%;
    `;
    
    // Insert wrapper and move input
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);
    wrapper.appendChild(dropdown);
    
    return dropdown;
}

/**
 * Show dropdown with matches
 */
function showDropdown(dropdown, matches, input, type) {
    dropdown.innerHTML = '';
    
    if (matches.length === 0) {
        dropdown.style.display = 'none';
        return;
    }
    
    matches.forEach(match => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.textContent = match;
        item.style.cssText = `
            padding: 0.5rem 0.75rem;
            cursor: pointer;
            border-bottom: 1px solid #f8f9fa;
            transition: background-color 0.15s ease-in-out;
            font-size: 0.875rem;
            color: #495057;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        `;
        
        item.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8f9fa';
            this.style.color = '#212529';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.backgroundColor = 'white';
            this.style.color = '#495057';
        });
        
        item.addEventListener('click', function() {
            input.value = match;
            if (type === 'country') {
                currentCountry = match;
                // Clear city when country is selected
                const cityInput = input.closest('form').querySelector('input[name="city"]');
                if (cityInput) {
                    cityInput.value = '';
                    currentCity = '';
                }
            } else {
                currentCity = match;
            }
            hideDropdown(dropdown);
        });
        
        dropdown.appendChild(item);
    });
    
    // Ensure dropdown is visible and properly positioned
    dropdown.style.display = 'block';
    dropdown.style.position = 'absolute';
    dropdown.style.zIndex = '9999';
    
    // Position dropdown relative to input
    const inputRect = input.getBoundingClientRect();
    const dropdownRect = dropdown.getBoundingClientRect();
    
    // If dropdown would go off-screen bottom, position it above the input
    const spaceBelow = window.innerHeight - inputRect.bottom;
    const spaceAbove = inputRect.top;
    
    if (spaceBelow < 200 && spaceAbove > 200) {
        dropdown.style.top = 'auto';
        dropdown.style.bottom = '100%';
        dropdown.style.borderTop = '1px solid #dee2e6';
        dropdown.style.borderBottom = 'none';
        dropdown.style.borderRadius = '0.375rem 0.375rem 0 0';
    } else {
        dropdown.style.top = '100%';
        dropdown.style.bottom = 'auto';
        dropdown.style.borderTop = 'none';
        dropdown.style.borderBottom = '1px solid #dee2e6';
        dropdown.style.borderRadius = '0 0 0.375rem 0.375rem';
    }
}

/**
 * Hide dropdown
 */
function hideDropdown(dropdown) {
    dropdown.style.display = 'none';
}

/**
 * Get selected location data
 */
function getSelectedLocation() {
    return {
        country: currentCountry,
        city: currentCity
    };
}

/**
 * Build location string from country and city
 */
function buildLocationString(country, city) {
    if (country && city) {
        return `${city}, ${country}`;
    } else if (country) {
        return country;
    } else if (city) {
        return city;
    }
    return '';
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeLocationAutocomplete();
});

// Export functions for external use
window.locationAutocomplete = {
    initialize: initializeLocationAutocomplete,
    getSelectedLocation: getSelectedLocation,
    buildLocationString: buildLocationString
};