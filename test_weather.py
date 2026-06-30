from weather_service import get_weather

if __name__ == '__main__':
    city = 'London'
    try:
        weather = get_weather(city)
        print(f'Current weather in {city}: {weather}')
    except Exception as e:
        print(f'An error occurred: {e}')