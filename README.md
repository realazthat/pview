pview
=====

WIP

##Description

An attempt at a scalable clone of google docs PDF viewer. Written in python, uses several 3rd party (FOSS) binaries.


<b>Features:</b>

* 

<b>TODO:</b>

* Make scalable
    * Serve exclusively from a proper webserver
    * Properly queue download/extraction jobs
    * Dynamic image loading
    * Scale/compress images
* Make submission page
* Make embeddable
* Google Drive integration
* Zoom


##Library requirements

* [tornado](http://www.tornadoweb.org/)
* [pyyaml](https://pypi.python.org/pypi/PyYAML)


##Binary requirements

* [poppler](http://poppler.freedesktop.org/)
    * pdftocairo
    * pdfinfo
* [imagemagick](http://www.imagemagick.org/)
* [pdf2xml](https://sourceforge.net/projects/pdf2xml/), [\[2?\]](http://www.mobipocket.com/dev/pdf2xml/)
    * Note: bug found while building: <b>[use of std::remove(), should be remove()](https://sourceforge.net/p/pdf2xml/support-requests/12/)</b>.
* [pdf2json](https://code.google.com/p/pdf2json/)

<b>Optional:</b>

* [svgo](https://github.com/svg/svgo) (nodejs)

    Installation: `$ [sudo] npm install -g svgo`


##Running

1. Copy the configuration file, serve_page.default.yml, to another location.
1. Edit the file as necessary.
1. Run: `python serve_page.py /path/to/serve_page.yml`

##Issues

* `pdf2xml` sometimes [crashes](https://sourceforge.net/p/pdf2xml/support-requests/13/)
* `pdf2json` sometimes [crashes](https://code.google.com/p/pdf2json/issues/detail?id=7)






