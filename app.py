from flask import Flask, render_template, request
from flask_pymongo import PyMongo
import requests
import matplotlib.pyplot as plt
import os
from threading import Thread

app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/your_data_base'
mongo = PyMongo(app)
db = mongo.db

def get_weather_data(city):
    api_key = 'your api code'  
    base_url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {'q': city, 'appid': api_key, 'units': 'metric'}
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data['main'] if 'main' in data else None
    else:
        return None

def get_weather_forecast(city):
    api_key = 'your api code'  
    base_url = 'http://api.openweathermap.org/data/2.5/forecast'
    params = {'q': city, 'appid': api_key, 'units': 'metric', 'cnt': 7}  
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        return data['list'] if 'list' in data else None
    else:
        return None

def generate_forecast_graph(city, forecast_data):
    dates = [forecast['dt_txt'] for forecast in forecast_data]
    temperatures = [forecast['main']['temp'] for forecast in forecast_data]

    plt.figure(figsize=(8, 6))
    plt.plot(dates, temperatures, marker='o', linestyle='-', color='b')
    plt.title(f'7-Day Temperature Forecast for {city}')
    plt.xlabel('Date')
    plt.ylabel('Temperature (°C)')
    plt.xticks(rotation=45)
    
    graph_filename = f"{city}_forecast.png"
    plt.savefig(os.path.join(app.static_folder, graph_filename))
    plt.close()

    return graph_filename

def generate_and_save_graph(city, forecast_data):
    graph_filename = generate_forecast_graph(city, forecast_data)
    return graph_filename

@app.route('/', methods=['GET', 'POST'])
def index():
    graph_filename = None  

    if request.method == 'POST':
        city = request.form['city']
        weather_data = get_weather_data(city)
        forecast_data = get_weather_forecast(city)

        if weather_data and forecast_data:
            weather_collection = db.weather_collection
            existing_weather = weather_collection.find_one({'city': city})

            if existing_weather:
                weather_collection.delete_one({'_id': existing_weather['_id']})

            new_weather = {
                'city': city,
                'temperature': weather_data['temp'],
                'feels_like': weather_data['feels_like'],
                'temp_min': weather_data['temp_min'],
                'temp_max': weather_data['temp_max']
            }
            weather_collection.insert_one(new_weather)

            forecast_collection = db.forecast_collection
            forecast_collection.delete_many({'city': city})

            for forecast in forecast_data:
                new_forecast = {
                    'city': city,
                    'date': forecast['dt_txt'],
                    'temperature': forecast['main']['temp'],
                    'description': forecast['weather'][0]['description']
                }
                forecast_collection.insert_one(new_forecast)

            graph_thread = Thread(target=generate_and_save_graph, args=(city, forecast_data))
            graph_thread.start()

            saved_forecast = list(forecast_collection.find({'city': city}))
            graph_filename = f"{city}_forecast.png"


            return render_template('index.html', weather_data=new_weather, forecast_data=saved_forecast, graph_filename=graph_filename)

    return render_template('index.html')

if __name__ == '__main__':
    
    plt.switch_backend('agg')
    app.run(debug=True)