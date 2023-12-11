from politician.models import Politician
from PIL import Image
import requests

def generate_background(politician):
    
    image = Image.open(requests.get(politician.we_vote_hosted_profile_image_url_large, stream=True).raw)
    im_crop = image.crop((0,0,20,20))
    color = im_crop.resize((1,1),resample=Image.Resampling.NEAREST)
    pixel = list(color.convert('RGBA').getdata())
    for r, g, b, a in pixel:
        hex = '#{:02x}{:02x}{:02x}'.format(r, g, b)
    return hex