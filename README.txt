================================================================================
WEATHER QUERY WEB APPLICATION
================================================================================

A simple web application that allows users to enter a city name, fetch current 
weather data from OpenWeatherMap API, and store/display query history in PostgreSQL.

================================================================================
TECHNOLOGY STACK
================================================================================

- Language: Python 3.14
- Web Framework: Flask
- Database: PostgreSQL (via Docker)
- Additional: SQLAlchemy, Alembic, Docker Compose

================================================================================
REQUIREMENTS
================================================================================

Before running the application, make sure you have:

1. Python 3.10 or higher installed
2. Docker Desktop installed and running
3. OpenWeatherMap API key (free)

================================================================================
INSTALLATION AND SETUP
================================================================================

STEP 1: Clone or download the project to your local machine

STEP 2: Create virtual environment and activate it

For Windows:
    python -m venv venv
    venv\Scripts\activate

For Mac/Linux:
    python3 -m venv venv
    source venv/bin/activate

STEP 3: Install dependencies

    pip install flask flask-sqlalchemy psycopg2-binary requests python-dotenv

STEP 4: Configure environment variables

    Rename .env.sample to .env and fill in your values:
    
    DATABASE_URL=postgresql://weather_user:weather_pass@localhost:5432/weather_db
    WEATHER_API_KEY=your_openweathermap_api_key_here
    RATE_LIMIT_PER_MINUTE=30

STEP 5: Start PostgreSQL using Docker Compose

    docker-compose up -d

    This will download PostgreSQL image and start the database container.

STEP 6: Run the application

    python app.py

STEP 7: Open your browser and navigate to:

    http://localhost:5000

================================================================================
DOCKER COMPOSE QUICKSTART
================================================================================

To start the PostgreSQL database only:

    docker-compose up -d

To stop the database:

    docker-compose down

To check if database is running:

    docker ps

================================================================================
USAGE
================================================================================

Main Page (/)
- Enter a city name (e.g., Minsk, Grodno, Slonim)
- Select temperature unit: Celsius (°C) or Fahrenheit (°F)
- Click "Get Weather" to fetch current weather data
- If the same city is queried within 5 minutes, data will be served from cache

History Page (/history)
- View all previous weather queries
- Filter by city name (case-insensitive)
- Filter by date range
- Pagination: 10 records per page
- Export filtered results to CSV

Health Check (/health)
- Check database connectivity
- Check external API reachability
- Returns JSON status

Export (/export/csv)
- Export filtered query history to CSV file

================================================================================
API ENDPOINTS
================================================================================

GET  /           - Main page
GET  /history    - Query history with filters and pagination
GET  /health     - Health check endpoint
GET  /export/csv - CSV export of filtered history
POST /weather    - Get weather for a city (JSON: {"city": "", "unit": "celsius"})

================================================================================
FEATURES IMPLEMENTED
================================================================================

1. Weather data fetching from OpenWeatherMap API
2. PostgreSQL database integration
3. Query history storage (city, timestamp, weather details)
4. History display with pagination (10 per page)
5. Filters: city (case-insensitive) and date range
6. Cache mechanism (5 minutes) with "served from cache" indicator
7. Unit toggle: Celsius/Fahrenheit with persistence
8. Rate limiting: 30 requests per minute per IP (returns 429 on exceed)
9. CSV export of filtered history
10. Health check endpoint with DB and API verification
11. Structured logging (JSON format)
12. Environment variables configuration
13. Docker Compose for PostgreSQL

================================================================================
PROJECT STRUCTURE
================================================================================

weather-app/
├── app.py                 - Main application file
├── docker-compose.yml     - Docker configuration for PostgreSQL
├── .env                   - Environment variables (not in repo)
├── .env.sample            - Sample environment variables
├── requirements.txt       - Python dependencies
├── README.txt             - This file
└── templates/
    ├── index.html         - Main page template
    └── history.html       - History page template

================================================================================
TROUBLESHOOTING
================================================================================

Error: ModuleNotFoundError: No module named 'flask'
    Solution: Run 'pip install flask' or activate virtual environment first

Error: Can't connect to database
    Solution: Make sure Docker is running and execute 'docker-compose up -d'

Error: API key invalid or missing
    Solution: Check .env file has correct WEATHER_API_KEY

Error: Port 5000 already in use
    Solution: Close other applications using port 5000 or change port in app.py

Error: Rate limit exceeded (429)
    Solution: Wait 1 minute before making more requests

================================================================================
TESTING
================================================================================

Unit tests cover:
- Cache reuse vs fresh fetch
- Rate limiting (429 response prevention of DB writes)
- Filtering and pagination logic

To run tests (if implemented):
    python -m unittest discover tests/

================================================================================
NOTES
================================================================================

- The application uses SQLite fallback if PostgreSQL is unavailable
- Cache duration is 5 minutes
- Rate limit default is 30 requests per minute per IP
- API key is required for weather data fetching

================================================================================
CONTACT
================================================================================

For any issues or questions, please refer to the documentation or contact 
the developer.

================================================================================