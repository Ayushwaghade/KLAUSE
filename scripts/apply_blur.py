from PIL import Image, ImageFilter

try:
    image = Image.open('downloaded_image.jpg')
    blurred_image = image.filter(ImageFilter.BLUR)
    blurred_image.save('blurred_image.jpg')
    print('Successfully applied BLUR filter and saved as blurred_image.jpg')
except Exception as e:
    print(f'Error processing image: {e}')