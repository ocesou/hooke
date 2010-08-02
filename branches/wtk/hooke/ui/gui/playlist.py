#!/usr/bin/env python

'''
playlist.py

Playlist class for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import os.path
import xml.dom.minidom

import lib.libhooke
import lib.file

class Playlist(object):

    def __init__(self, filename=None):
        self._saved = False
        self.count = 0
        self.figure = None
        self.files = []
        self.generics_dict = {}
        self.hidden_attributes = ['curve', 'data', 'driver', 'fits', 'name', 'plot', 'plots']
        self.index = -1
        self.name = None
        self.path = None
        self.plot_panel = None
        self.plot_tab = None
        if filename is None:
            self.filename = None
        else:
            self.load(filename)

    def add_file(self, filename):
        if os.path.isfile(filename):
            file_to_add = lib.file.File(filename)
            self.files.append(file_to_add)
            self._saved = False
        self.count = len(self.files)

    def delete_file(self, name):
        for index, item in enumerate(self.files):
            if item.name == name:
                del self.files[index]
                self.index = index
        self.count = len(self.files)
        if self.index > self.count - 1:
            self.index = 0

    def filter_curves(self, curves_to_keep=[]):
        playlist = Playlist()
        for curve_index in curves_to_keep:
            playlist.files.append(self.files[curve_index])
        playlist.count = len(playlist.files)
        playlist.index = 0
        return playlist

    def get_active_file(self):
        return self.files[self.index]

    #def get_active_plot(self):
        ##TODO: is this the only active (or default?) plot?
        #return self.files[self.index].plots[0]

    def load(self, filename):
        '''
        Loads a playlist file
        '''
        self.filename = filename
        self.path, self.name = os.path.split(filename)
        playlist_file = lib.libhooke.delete_empty_lines_from_xmlfile(filename)
        self.xml = xml.dom.minidom.parseString(playlist_file)
        #TODO: rename 'element' to 'curve' or something in hkp file
        #TODO: rename 'path' to 'filename'
        #TODO: switch from attributes to nodes, it's cleaner XML in my eyes

        element_list = self.xml.getElementsByTagName('element')
        #populate playlist with files
        for index, element in enumerate(element_list):
            #rebuild a data structure from the xml attributes
            #the next two lines are here for backwards compatibility, newer playlist files use 'filename' instead of 'path'
            if element.hasAttribute('path'):
                #path, name = os.path.split(element.getAttribute('path'))
                #path = path.split(os.sep)
                #filename = lib.libhooke.get_file_path(name, path)
                filename = element.getAttribute('path')
            if element.hasAttribute('filename'):
                #path, name = os.path.split(element.getAttribute('filename'))
                #path = path.split(os.sep)
                #filename = lib.libhooke.get_file_path(name, path)
                filename = element.getAttribute('filename')
            if os.path.isfile(filename):
                data_file = lib.file.File(filename)
                if element.hasAttribute('note'):
                    data_file.note = element.getAttribute('note')
                self.files.append(data_file)
        self.count = len(self.files)
        if self.count > 0:
            #populate generics
            genericsDict = {}
            generics_list = self.xml.getElementsByTagName('generics')
            if generics_list:
                for attribute in generics_list[0].attributes.keys():
                    genericsDict[attribute] = generics_list[0].getAttribute(attribute)
            if genericsDict.has_key('pointer'):
                index = int(genericsDict['pointer'])
                if index >= 0 and index < self.count:
                    self.index = index
                else:
                    index = 0
            self._saved = True

    def next(self):
        self.index += 1
        if self.index > self.count - 1:
            self.index = 0

    def previous(self):
        self.index -= 1
        if self.index < 0:
            self.index = self.count - 1

    def reset(self):
        if self.count > 0:
            self.index = 0
        else:
            self.index = -1

    def save(self, filename):
        '''
        Saves a playlist from a list of files.
        A playlist is an XML document with the following syntax:
        <playlist>
        <element path="/my/file/path/"/ attribute="attribute">
        <element path="...">
        </playlist>
        '''
        try:
            output_file = file(filename, 'w')
        except IOError:
            self.AppendToOutput('Cannot save playlist. Wrong path or filename')
            return
        #create the output playlist, a simple XML document
        implementation = xml.dom.minidom.getDOMImplementation()
        #create the document DOM object and the root element
        self.xml = implementation.createDocument(None, 'playlist', None)
        root = self.xml.documentElement

        #save generics variables
        playlist_generics = self.xml.createElement('generics')
        root.appendChild(playlist_generics)
        self.generics_dict['pointer'] = self.index
        for key in self.generics_dict.keys():
        #for key in generics.keys():
            self.xml.createAttribute(key)
            playlist_generics.setAttribute(key, str(self.generics_dict[key]))

        #save files and their attributes
        for item in self.files:
            #playlist_element=newdoc.createElement("file")
            playlist_element = self.xml.createElement('element')
            root.appendChild(playlist_element)
            for key in item.__dict__:
                if not (key in self.hidden_attributes):
                    self.xml.createAttribute(key)
                    playlist_element.setAttribute(key, str(item.__dict__[key]))
        self._saved = False

        self.xml.writexml(output_file, indent='\n')
        output_file.close()
        self._saved = True
