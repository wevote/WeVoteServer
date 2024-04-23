from PIL import Image
from io import BytesIO
from urllib import request
import math, re


def generate_background(politician, base=None):
    # specify how many bins will be generated for color sorting, the number of bins is base**3
    base = base or 3
 
    # this is the speed bottleneck, not sure if this can be sped up
    try:
        res = request.urlopen(politician.we_vote_hosted_profile_image_url_large).read()
        image = Image.open(BytesIO(res))

        image_crop_left = image.crop((0, 0, 20, 20))
        image_crop_right = image.crop((image.width - 20, 0, image.width, 20))

        pixels_left = image_crop_left.convert('RGBA')
        pixels_right = image_crop_right.convert('RGBA')
        left_list = list(pixels_left.getdata())
        right_list = list(pixels_right.getdata())

        for pixel in right_list:
            left_list.append(pixel)

        bins = []
        for bin in range(base**3, 0, -1):
            bins.append([])

        divisor = 255/base

        for r, g, b, a in left_list:
           r_binned = min(math.floor(r/divisor), base-1)
           g_binned = min(math.floor(g/divisor), base-1)
           b_binned = min(math.floor(b/divisor), base-1)
           bin_index = (r_binned * (base**2)) + (g_binned * base) + b_binned
           bins[bin_index].append((r,g,b))

        bins.sort(key=lambda l: -len(l))

        final_color = [0, 0, 0, 255]
        denominator = 0

        for bin in range(0, 2, 1):
            for rgb in bins[bin]:
                final_color[0] += rgb[0]
                final_color[1] += rgb[1]
                final_color[2] += rgb[2]
            denominator += len(bins[bin])

        final_color[0]=math.floor(final_color[0]/denominator)
        final_color[1]=math.floor(final_color[1]/denominator)
        final_color[2]=math.floor(final_color[2]/denominator)

        hex = '#{:02x}{:02x}{:02x}'.format(final_color[0], final_color[1], final_color[2])

        return hex
    except Exception as e:
        return ''


def validate_hex(hex):
   return re.search("#[A-Fa-f0-9]{6}", hex[:7])
