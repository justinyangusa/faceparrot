#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
from flask_uploads import UploadSet, configure_uploads, IMAGES
import numpy as np
from PIL import Image, ImageSequence
from shapely.geometry import Point, Polygon
from werkzeug.datastructures import FileStorage
import urllib
from io import BytesIO
import os

###
# import matplotlib.pyplot as plt
# import sys
###

app = Flask(__name__)

photos = UploadSet('photos', IMAGES)

app.config['UPLOADED_PHOTOS_DEST'] = 'static/img/'
configure_uploads(app, photos)

cut_loc = 'static/cuts/'
parrot_loc = 'static/parrots/'

@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'photo' in request.files:
        # print type(request.files['photo'])
        filename = photos.save(request.files['photo'])
        url = photos.url(filename)
        # return filename + '<br><br><img src=\'' + url + '\'/>'
        return render_template('image.html', filename=filename, url=url)
    return render_template('upload.html')

@app.route('/cut', methods=['POST'])
def cut():
    # print("Hello world, I am cut.")
    # print(photos.path(request.json['filename']))
    # https://gist.github.com/yosemitebandit/03bb3ae302582d9dc6be
    filename = request.json['filename']
    im = Image.open(photos.path(filename)).convert('RGBA')
    # im.show()
    pixels = np.array(im)
    im_copy = np.array(im)
    xcoords = request.json['xcoords']
    ycoords = request.json['ycoords']
    region = Polygon(zip(xcoords, ycoords))

    for index, pixel in np.ndenumerate(pixels):
        # Unpack the index.
        row, col, channel = index
        # We only need to look at spatial pixel data for one of the four channels.
        if channel != 0:
            continue
        point = Point(row, col)
        if not region.contains(point):
            im_copy[(row, col, 0)] = 255
            im_copy[(row, col, 1)] = 255
            im_copy[(row, col, 2)] = 255
            im_copy[(row, col, 3)] = 0

    cut_image = Image.fromarray(im_copy)

    xmin = min(xcoords)
    xmax = max(xcoords)
    ymin = min(ycoords)
    ymax = max(ycoords)
    crop_image = cut_image.crop((xmin,ymin,xmax,ymax))

    height = 100 # px, const
    width = height*crop_image.width/crop_image.height # calculated to maintain aspect ratio
    width = int(round(width))
    resized_image = crop_image.resize((width,height), resample=Image.BICUBIC)

    dot_idx = filename.rfind('.')
    filename = filename[:dot_idx] + '.png'
    path = cut_loc + filename
    parrotpath = parrot_loc + filename
    # print('path:',path)

    for directory in [cut_loc, parrot_loc]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    resized_image.save(path)

    file = None
    with open(path,'rb') as fp:
        file = FileStorage(fp)
        # print(type(file))
        # print(file)
        # print('--------------------------')
        # file.save('static/cuts/newfile.png')
        wfilename = photos.save(file)
        wurl = photos.url(wfilename)
        print('wurl:',wurl)
    # print(wurl)

    parroturl = ''

    ### PARROT ###
    # https://stackoverflow.com/questions/5607551/how-to-urlencode-a-querystring-in-python
    parroturl = ('https://ppaas.herokuapp.com/partyparrot?overlay=' + urllib.parse.quote_plus(wurl)
        + '&overlayWidth=' + str(width) + '&overlayHeight=' + str(height) + '&overlayOffsetX=-10&overlayOffsetY=-100')
    print('parroturl:',parroturl)

    width = None
    height = None
    def resize(frame):
        width = 128 # px, const
        height = width*crop_image.height/crop_image.width # calculated to maintain aspect ratio
        return frame.resize((width,height), resample=Image.BICUBIC)

    # https://stackoverflow.com/questions/7391945/how-do-i-read-image-data-from-a-url-in-python
    megafile = BytesIO(urllib.request.urlopen(parroturl).read())
    parrotimg = Image.open(megafile)
    # https://stackoverflow.com/questions/12760389/how-can-i-create-an-empty-nm-png-file-in-python
    Image.new('RGBA').save(parrotpath, save_all=True, append_images=[resize(frame) for frame in ImageSequence.Iterator(im)])

    parrotfile = None
    with open(parrotpath,'rb') as fp:
        parrotfile = FileStorage(fp)
        # print(parrotfile)
        # print('lalalala----------------------------')
        parrotfilename = photos.save(parrotfile)
        parroturl = photos.url(parrotfilename)

    ###

    # print('parroturl:',parroturl)

    return jsonify({
        'parrot': parroturl
      , 'cutout': wurl
      })

    # print type(cut_image)
    # newfilename = photos.save(cut_image)
    # print 'new url:', photos.url(newfilename)

    # print photos.url(filename).replace('img', 'cuts', 1)
    # return photos.url(filename).replace('img', 'cuts', 1)

    # print("Hello, I have completed")
    # sys.stdout.flush()

if __name__ == '__main__':
    app.run(debug=True)
