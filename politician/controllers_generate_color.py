from politician.models import Politician
from collections import Counter
import math
from PIL import Image
import requests

def generate_background(politician, base=None, edge_case=None):

    print(edge_case)

    base = base or 3
 
    image = Image.open(requests.get(politician.we_vote_hosted_profile_image_url_large, stream=True).raw)
    image_crop_left = image.crop((0, 0, 20, 20))
    image_crop_right = image.crop((image.width - 20, 0, image.width, 20))

    pixels_left = image_crop_left.convert('RGBA')
    pixels_right = image_crop_right.convert('RGBA')
    left_list = list(pixels_left.getdata())
    right_list = list(pixels_right.getdata())

    for pixel in right_list:
        left_list.append(pixel)
   
    bins = [
            [],[],[],[],[],[],[],[],[],
            [],[],[],[],[],[],[],[],[],
            [],[],[],[],[],[],[],[],[]
            ]
    
    ################# testing
    test_base = 4
    for r in range(test_base-1,-1,-1):
        for g in range(test_base-1,-1,-1):
            for b in range(test_base-1,-1,-1):
                test = (r * (test_base**2)) + (g * test_base) + b
                print(test)
    print("**********")
    for r in range(test_base-1,-1,-1):
        print(r)

    ## TODO nicer way to write this?
    test_bin = []
    for bin in range(base**3,-1,-1):
        test_bin.append([])

    print(test_bin)
    ############################ end testing


    divisor= 255/base
    for r,g,b,a in left_list:
       # turn math.floor etc into a variable
       # document the meaning of variables
       r_binned = min(math.floor(r/divisor),base-1)
       g_binned = min(math.floor(g/divisor),base-1)
       b_binned = min(math.floor(b/divisor),base-1)
       bin_index = (r_binned * (base**2)) + (g_binned * base) + b_binned
       bins[bin_index].append((r,g,b))
    
    bins.sort(key=lambda l: -len(l))

    final_color=[0,0,0,255]
    #todo generate 30 or 50 at a time, viewable
    #todo first make the variables editable
    #add a regen button, as the formula is tweaked
    for rgb in bins[0]:
        final_color[0]+=rgb[0]
        final_color[1]+=rgb[1]
        final_color[2]+=rgb[2]
    
    final_color[0]=final_color[0]/len(bins[0])
    final_color[1]=final_color[1]/len(bins[0])
    final_color[2]=final_color[2]/len(bins[0])
    
    hex = '#{:02x}{:02x}{:02x}'.format(pixel[0], pixel[1], pixel[2])
    return hex
