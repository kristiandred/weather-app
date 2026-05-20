import os
import json
import csv
from io import StringIO
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, Response, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from dotenv import load_dotenv
import requests
from collections import defaultdict
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'secret-key-for-session'

database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('sqlite'):
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'check_same_thread': False}}
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

rate_limit_cache = defaultdict(list)

class WeatherQuery(db.Model):
    __tablename__ = 'weather_queries'
    
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    weather_description = db.Column(db.String(200))
    humidity = db.Column(db.Integer)
    wind_speed = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    from_cache = db.Column(db.Boolean, default=False)
    unit = db.Column(db.String(10), default='celsius')
    
    def to_dict(self):
        temp_value = self.temperature
        if self.unit == 'fahrenheit':
            temp_value = self.celsius_to_fahrenheit(temp_value)
            
        return {
            'id': self.id,
            'city': self.city,
            'temperature': temp_value,
            'weather_description': self.weather_description,
            'humidity': self.humidity,
            'wind_speed': self.wind_speed,
            'timestamp': self.timestamp.isoformat(),
            'from_cache': self.from_cache,
            'unit': self.unit
        }
    
    @staticmethod
    def celsius_to_fahrenheit(celsius):
        return round((celsius * 9/5) + 32, 1)

def rate_limit(max_per_minute=30):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            
            rate_limit_cache[ip] = [t for t in rate_limit_cache[ip] if t > minute_ago]
            
            if len(rate_limit_cache[ip]) >= max_per_minute:
                logger.warning(f"Rate limit exceeded for IP: {ip}")
                return jsonify({'error': 'Слишком много запросов. Попробуйте через минуту.'}), 429
            
            rate_limit_cache[ip].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_cached_weather(city):
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    cached = WeatherQuery.query.filter(
        WeatherQuery.city.ilike(city),
        WeatherQuery.timestamp >= five_minutes_ago,
        WeatherQuery.from_cache == False
    ).order_by(WeatherQuery.timestamp.desc()).first()
    
    if cached:
        logger.info(f"Cache hit for city: {city}")
        return cached
    return None

def fetch_from_api(city, unit):
    api_key = os.getenv('WEATHER_API_KEY')
    if not api_key:
        raise ValueError("WEATHER_API_KEY не настроен")
    
    unit_param = 'metric' if unit == 'celsius' else 'imperial'
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units={unit_param}&lang=ru"
    
    start_time = datetime.now()
    try:
        response = requests.get(url, timeout=5)
        logger.info(f"External API latency: {(datetime.now() - start_time).total_seconds()}s")
        
        if response.status_code == 200:
            data = response.json()
            return {
                'temperature': data['main']['temp'],
                'description': data['weather'][0]['description'],
                'humidity': data['main']['humidity'],
                'wind_speed': data['wind']['speed']
            }
        elif response.status_code == 404:
            return None
        else:
            raise Exception(f"API error: {response.status_code}")
    except requests.Timeout:
        logger.error("External API timeout")
        raise Exception("API timeout")
    except Exception as e:
        logger.error(f"External API error: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/weather', methods=['POST'])
@rate_limit(max_per_minute=int(os.getenv('RATE_LIMIT_PER_MINUTE', 30)))
def get_weather():
    data = request.get_json()
    city = data.get('city', '').strip()
    unit = data.get('unit', 'celsius')
    
    if not city:
        return jsonify({'error': 'Введите название города'}), 400
    
    logger.info(f"Weather request: city={city}, unit={unit}")
    
    try:
        cached = get_cached_weather(city)
        
        if cached:
            new_query = WeatherQuery(
                city=city,
                temperature=cached.temperature,
                weather_description=cached.weather_description,
                humidity=cached.humidity,
                wind_speed=cached.wind_speed,
                from_cache=True,
                unit=unit
            )
            db.session.add(new_query)
            db.session.commit()
            
            result_temp = cached.temperature
            if unit == 'fahrenheit':
                result_temp = WeatherQuery.celsius_to_fahrenheit(result_temp)
            
            return jsonify({
                'city': city,
                'temperature': result_temp,
                'description': cached.weather_description,
                'humidity': cached.humidity,
                'wind_speed': cached.wind_speed,
                'from_cache': True,
                'unit': unit
            })
        
        weather_data = fetch_from_api(city, unit)
        
        if not weather_data:
            return jsonify({'error': f'Город "{city}" не найден'}), 404
        
        query = WeatherQuery(
            city=city,
            temperature=weather_data['temperature'],
            weather_description=weather_data['description'],
            humidity=weather_data['humidity'],
            wind_speed=weather_data['wind_speed'],
            from_cache=False,
            unit=unit
        )
        db.session.add(query)
        db.session.commit()
        
        result_temp = weather_data['temperature']
        if unit == 'fahrenheit':
            result_temp = WeatherQuery.celsius_to_fahrenheit(result_temp)
        
        return jsonify({
            'city': city,
            'temperature': result_temp,
            'description': weather_data['description'],
            'humidity': weather_data['humidity'],
            'wind_speed': weather_data['wind_speed'],
            'from_cache': False,
            'unit': unit
        })
        
    except Exception as e:
        logger.error(f"Error in get_weather: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def history():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    city_filter = request.args.get('city', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = WeatherQuery.query
    
    if city_filter:
        query = query.filter(WeatherQuery.city.ilike(f'%{city_filter}%'))
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(WeatherQuery.timestamp >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(WeatherQuery.timestamp <= to_date)
        except ValueError:
            pass
    
    # Пагинация
    paginated = query.order_by(WeatherQuery.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    queries = [q.to_dict() for q in paginated.items]
    
    return render_template(
        'history.html',
        queries=queries,
        pagination={
            'page': page,
            'pages': paginated.pages,
            'total': paginated.total,
            'per_page': per_page
        },
        filters={
            'city': city_filter,
            'date_from': date_from,
            'date_to': date_to
        }
    )

@app.route('/export/csv')
def export_csv():
    city_filter = request.args.get('city', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = WeatherQuery.query
    
    if city_filter:
        query = query.filter(WeatherQuery.city.ilike(f'%{city_filter}%'))
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(WeatherQuery.timestamp >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(WeatherQuery.timestamp <= to_date)
        except ValueError:
            pass
    
    queries = query.order_by(WeatherQuery.timestamp.desc()).all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Город', 'Температура (°C)', 'Описание', 'Влажность (%)', 'Скорость ветра', 'Время запроса', 'Из кэша', 'Единицы'])
    
    for q in queries:
        writer.writerow([
            q.id, q.city, q.temperature, q.weather_description,
            q.humidity, q.wind_speed, q.timestamp, q.from_cache, q.unit
        ])
    
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=weather_history.csv'}
    )

@app.route('/health')
def health():
    status = {'status': 'healthy', 'database': 'ok', 'timestamp': datetime.utcnow().isoformat()}
    
    try:
        db.session.execute(text('SELECT 1'))
        db.session.commit()
    except Exception as e:
        status['status'] = 'unhealthy'
        status['database'] = f'error: {str(e)}'
        return jsonify(status), 500
    
    try:
        response = requests.get('https://api.openweathermap.org/data/2.5/weather?q=London', timeout=2)
        status['external_api'] = 'reachable' if response.status_code == 401 else 'error'
    except:
        status['external_api'] = 'unreachable'
    
    return jsonify(status)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)