
import sys,traceback,os
import tornado.ioloop
import tornado.web as web

import base64
import json
import urlparse, urllib
import shutil
import subprocess
import hashlib
import tempfile

import xml.dom.minidom as minidom

import pprint
import cgi

from pdf2xmltojson import pdf2xmltojson

import argparse
import yaml


"""

Library Requirements:

* tornado
* yaml

Executable Requirements:

* poppler
    * pdftocairo
    * pdfinfo
* svgo (nodejs)

    todo: make optional

* imagemagick
* <s>[pdf2json](https://code.google.com/p/pdf2json/)</s>
* [pdf2xml](https://sourceforge.net/projects/pdf2xml/), [2](http://www.mobipocket.com/dev/pdf2xml/)


TODO:

* hard limits on subprocess calls
* limit file download size
* test a filename with percent encoding, or invalid url chars

"""

def encode_url_as_path(url):
    return (base64.b64encode(urlparse.urlparse(url).geturl()))


def get_directory_path(url0,docspath):
    
    
    url = urlparse.urlparse(url0,scheme='http')
    
    
    directorypath = '{docspath}/{domain}/{encurl}'
    directorypath = directorypath.format(docspath = docspath,
                                         domain = url.netloc,
                                         encurl = encode_url_as_path(url0))
    directorypath = os.path.normpath(directorypath)
    if not directorypath.startswith(docspath):
        raise Exception("invalid url")
    return directorypath
def get_directory_url(url0,docsurl):
    
    url0 = urlparse.urlparse(url0).geturl()
    
    url = urlparse.urlparse(url0,scheme='http')
    
    directoryurl = '{domain}/{encurl}/'
    directoryurl = directoryurl.format(docsurl = docsurl,
                                       domain = url.netloc,
                                       encurl = encode_url_as_path(url0))
    
    directoryurl = urlparse.urljoin(docsurl,directoryurl)
    
    return urlparse.urlparse(urllib.quote(directoryurl)).geturl()
    
def get_file_data(datafilepath):
    if not os.path.exists(datafilepath):
        return None
    try:
        with open(datafilepath,'r') as datafile:
            return json.load(fp=datafile)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
    
    return None

def get_json_text_layer(directorypath,jsonfilename):
    jsonfilepath = os.path.join(directorypath,jsonfilename)
    
    #print 'jsonfilepath:',jsonfilepath
    if not os.path.exists(jsonfilepath):
        return None
    try:
        with open(jsonfilepath,'rb') as jsonfile:
            return json.load(fp=jsonfile)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
    
    return None

def get_pdf_info(filepath):
    pdfinfo = {}
    
    pdfinforaw = subprocess.check_output(['pdfinfo', filepath])

    for line in pdfinforaw.splitlines():
        name,_,value = line.partition(':')
        pdfinfo[name.strip()] = value.strip()
    return pdfinfo


def filemd5(filepath):
    md5 = hashlib.md5()
    with open(filepath,'rb') as f: 
        for chunk in iter(lambda: f.read(8192), b''): 
             md5.update(chunk)
    return md5.hexdigest()


def make_json_textlayer_from_pdf2xml(filepath,jtextlayerfilepath,pagenumber,config):
    with tempfile.NamedTemporaryFile() as pdf2xmlfile:
        pdf2xmlfilepath = pdf2xmlfile.name
        
        
        command = [config['pdftoxml'],
                   '-verbose',
                   '-f', '{0}'.format(pagenumber),
                   '-l', '{0}'.format(pagenumber),
                   '-blocks', '-noImage',
                   filepath,
                   pdf2xmlfilepath]
        
        #print 'command:', ' '.join(command)
        errout = subprocess.check_output(command, stderr=subprocess.STDOUT)
        
        with open(jtextlayerfilepath,'w+') as jtextlayerfile:
            
            json.dump(pdf2xmltojson(pdf2xmlfile),fp=jtextlayerfile,indent=4)


def make_json_textlayer_from_pdf2json(filepath,jtextlayerfilepath,pagenumber,config):
    #with tempfile.NamedTemporaryFile() as pdf2jsonfile:
    with open('1.json', 'w+b') as pdf2jsonfile:
        pdf2jsonfilepath = pdf2jsonfile.name
        
        
        command = [config['pdf2json'],
                   '-f', '{0}'.format(pagenumber),
                   '-l', '{0}'.format(pagenumber),
                   filepath,
                   pdf2jsonfilepath]
        
        print 'command:', ' '.join(command)
        errout = subprocess.check_output(command, stderr=subprocess.STDOUT)
        
        with open(jtextlayerfilepath,'w+') as jtextlayerfile:
            
            json.dump(pdf2jsontojson(pdf2jsonfile),fp=jtextlayerfile,indent=4)

def make_json_textlayer(filepath,jtextlayerfilepath,pagenumber,config):
    
    textlayer_converters = [
        make_json_textlayer_from_pdf2xml,
        #make_json_textlayer_from_pdf2json,
                            ]
    
    for textlayer_converter in textlayer_converters:
        try:
            textlayer_converter(filepath,jtextlayerfilepath,pagenumber,config)
            
            return
        except Exception as e:

            
            print >> sys.stderr
            print >> sys.stderr, 'Error producing json. Details:'
            print >> sys.stderr, 'textlayer_converter:',textlayer_converter
            print >> sys.stderr, 'filepath:',filepath
            print >> sys.stderr, 'jtextlayerfilepath:',jtextlayerfilepath
            print >> sys.stderr
            
            traceback.print_exc(file=sys.stderr)
    
    raise Exception("All pdf => textlayer conversions failed")
    
class MainHandler(web.RequestHandler):
    
    def get(self):
        
        try:
            config = self.application.config
            
            pdfurl = self.get_argument("url")
            
            
            if len(pdfurl) > 100:
                raise Exception("url is too long")
            
            pdfurl = urlparse.urlparse(pdfurl,scheme='http').geturl()
                
            docsurl = '/docs/'
            docspath = 'docs/'
            docspath = os.path.abspath(docspath)
            
            directorypath = get_directory_path(url0=pdfurl,docspath=docspath)
            directoryurl = get_directory_url(url0=pdfurl,docsurl=docsurl)
            
            datafilepath = os.path.join(directorypath,'data.json')
            
            filename = os.path.basename(pdfurl)
            filepath = os.path.join(directorypath,filename)
            fileurl = urlparse.urlparse(urlparse.urljoin(directoryurl,urllib.quote(filename))).geturl()
            
            if not filepath.startswith(directorypath):
                filename = 'file.pdf'
                filepath = os.path.join(directorypath,filename)
                
                assert filepath.startswith(directorypath)
            
            if not os.path.exists(directorypath):
                os.makedirs(directorypath)
            
            
            
            filedata = get_file_data(datafilepath)
            
            if filedata is None:
                filedata = {'url': pdfurl,
                           'filename':filename,
                           'pages':[],
                           'textlayers':[],
                           'thumbs':[],}
                
                def download_file():
                    (filepath1,headers) = urllib.urlretrieve(pdfurl, filepath)
                    
                    if filepath1 != filepath:
                        shutil.copyfile(filepath1,filepath)
                
                    
                download_file()
                
                filedata['md5'] = filemd5(filepath)
                
                pdfinfo = get_pdf_info(filepath)
                
                filedata['pdfinfo'] = pdfinfo
                
                page_count = int(pdfinfo['Pages'])
                
                for i in range(page_count):
                    """
                    jsonfilename = '{0}.json'.format(i+1)
                    jsonfilepath = os.path.join(directorypath,jsonfilename)
                    
                    command = ['pdf2json',
                               '-f', '{0}'.format(i+1),
                               '-l', '{0}'.format(i+1),
                               filepath,
                               jsonfilepath]
                    """
                    
                    
                        
                        
                        
                    jtextlayerfilename = '{0}.json'.format(i+1)
                    jtextlayerfilepath = os.path.join(directorypath,jtextlayerfilename)
                    
                    
                    make_json_textlayer(filepath,jtextlayerfilepath,pagenumber=i+1,config=config)
                    
                            
                            
                    
                    
                    
                    svgfilename = '{0}.svg'.format(i+1)
                    svgfilepath = os.path.join(directorypath,svgfilename)
                    
                    
                    command = [config['pdftocairo'],
                               '-svg',
                               '-f', '{0}'.format(i+1),
                               '-l', '{0}'.format(i+1),
                               '-origpagesizes',
                               filepath,
                               svgfilepath]
                    
                    errout = subprocess.check_output(command, stderr=subprocess.STDOUT)
                    
                    
                    
                    
                    thumbwidth = config['thumbwidth'] if 'thumbwidth' in config else 300
                    thumbfilename = '{0}.{1}xY.png'.format(i+1,thumbwidth)
                    thumbfilepath = os.path.join(directorypath,thumbfilename)
                    command = [config['convert'], svgfilepath, '-resize', str(thumbwidth), thumbfilepath]
                    
                    subprocess.check_output(command, stderr=subprocess.STDOUT)
                    
                    if 'svgo' in config:
                        command = [config['svgo'], svgfilepath]
                        errout = subprocess.check_output(command, stderr=subprocess.STDOUT)
                    
                    filedata['pages'] += [svgfilename]
                    filedata['thumbs'] += [thumbfilename]
                    filedata['textlayers'] += [jtextlayerfilename]
                
                with open(datafilepath,'w+') as datafile:
                    json.dump(filedata,fp=datafile)
                
            
                filedata = get_file_data(datafilepath)
                
                
                
                
                if filedata is None:
                    raise Exception("data is None after creating data file (datafilepath: {datafilepath})".format(datafilepath=datafilepath))
            
            
            thumbbar = ['<ul class="thumb-bar">\n']
            
            for i,thumb in enumerate(filedata['thumbs']):
                thumburl = urlparse.urlparse(urlparse.urljoin(directoryurl,thumb)).geturl()
                thumbbar += ['    ','<li>\n',
                             '        ', '<div class="thumb-frame"><img src="',thumburl,'" /></div>\n',
                             '        ', '<div class="thumb-underbar">{0}</div>\n'.format(i+1),
                             '    ','</li>','\n']
            
            thumbbar += ['</ul>\n']
            
            
            
            viewpanel = ['<ul class="view-panel">\n']
            
            if 'textlayers' in filedata:
                for pageimage,pdfxmljsonfilename in zip(filedata['pages'],filedata['textlayers']):
                    
                    pageimageurl = urlparse.urlparse(urlparse.urljoin(directoryurl,pageimage)).geturl()
                    
                    textlayer = get_json_text_layer(directorypath, pdfxmljsonfilename)
                    
                    
                    
                    indent = '    '
                    
                    viewpanel += [indent * 1,'<li>\n']
                    viewpanel += [indent * 2, '<div class="page-frame">\n',]
                    viewpanel += [indent * 3, '<div class="text-layer">\n',]
                                 
                    
                    div = u'<div class="token"' \
                          + 'style="top:{top}%; ' \
                          + 'left:{left}%; width:{width}%; height:{height}%; ' \
                          + '{styles}">' \
                          + '{text}</div>'
                    
                    pagewidth = float(textlayer['width'])
                    pageheight = float(textlayer['height'])
                    for bi,block in enumerate(textlayer['blocks']):
                        block_texts = block['texts']
                        for ti,text in enumerate(block_texts):
                            text_tokens = text['tokens']
                            for ki,token in enumerate(text_tokens):
                                
                                x = float(token['x'])/pagewidth
                                y = float(token['y'])/pageheight
                                width = float(token['width'])/pagewidth
                                height = float(token['height'])/pageheight
                                
                                text = token['text'].strip()
                                
                                    
                                text = cgi.escape(text).encode('ascii', 'xmlcharrefreplace')
                                
                                if len(text) > 0:
                                    if text[-1] != '-' and ti + 1 != len(block_texts):
                                        #text += '&nbsp;'
                                        pass
                                
                                styles = []
                                
                                if 'angle' in token and token['angle'] != '0':
                                    text = ''
                                    #angle = -float(token['angle'])
                                    #styles += ['-webkit-transform: rotate({0}deg);'.format(angle)]
                                    #styles += ['-moz-transform: rotate({0}deg);'.format(angle)]
                                    #styles += ['-o-transform: rotate({0}deg);'.format(angle)]

                                
                                styles = ''.join(styles)
                                
                                viewpanel += [
                                    indent * 4,
                                    div.format(top=100* y,
                                               left=100* x,
                                               width=100* width,
                                               height=100* height,
                                               text=text,
                                               styles=styles),
                                    '\n',
                                            ]
                    
                    
                    
                    viewpanel += [indent * 3, '</div>\n',]
                    viewpanel += [indent * 3, '<img src="',pageimageurl,'" />\n']
                    viewpanel += [indent * 2, '</div>\n',
                                  indent * 1,'</li>','\n']
            else:
                for pageimage in filedata['pages']:
                    pageimageurl = urlparse.urlparse(urlparse.urljoin(directoryurl,pageimage)).geturl()
                    
                    
                    viewpanel += [indent * 1, '<li>\n',
                                  indent * 2, '<div class="page-frame">',
                                  indent * 3, '<img src="',pageimageurl,'" />\n']
                    
                    
                    
                    viewpanel += [indent * 2, '</div>\n',
                                  indent * 1,'</li>','\n']
                
            viewpanel += ['</ul>\n']
            
            
            
            self.render('pdfview.html',
                        filename=filename,
                        downloadurl=fileurl,
                        thumbbar=''.join(thumbbar),
                        viewpanel=''.join(viewpanel))
            
            
            
            
            
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            raise
            





        
if __name__ == "__main__":
    
    
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('config', type=argparse.FileType('r'),help="configuration file")
    
    parsed_args = parser.parse_args()

    config_file = parsed_args.config

    config = {}

    try:
        config = yaml.load(config_file)
    except:
        print >> sys.stderr
        print >> sys.stderr, "ERROR: parsing configuration"
        print >> sys.stderr
        
        raise
    
    
    template_directory = os.path.abspath(config['templates'])
    
    

    application = web.Application([
        (r"/viewer", MainHandler),
        (r"/docs/(.*)", web.StaticFileHandler, {"path": config['docs']}),
        (r"/style/(.*)", web.StaticFileHandler, {"path": './style'}),
        (r"/script/(.*)", web.StaticFileHandler, {"path": './script'}),
    ])
    application.config = config


    
    application.settings['template_path'] = template_directory
    application.listen(config['port'])
    tornado.ioloop.IOLoop.instance().start()




