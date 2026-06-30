import requests

url = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRtjFvwOZr5lBlsSPyrqMhEZXf4lfZeuyq7eHwb8ir99LdqhfLsoea8ipk&s=10'
file_name = 'downloaded_image.jpg'

try:
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(file_name, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f'Successfully downloaded: {file_name}')
except Exception as e:
    print(f'Error downloading image: {e}')