#!/usr/bin/env python

from __future__ import print_function
import sys, os
import copy
from bs4 import BeautifulSoup
from collections import OrderedDict

import regex as re

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from bs4.element import NavigableString, Tag, Comment
from docutils.nodes import comment

def set(d, set, value):
    keys = list(set)
    keys.append(value)
    for k in keys:
        d = d.setdefault(k, OrderedDict())


        
        
def reformatSectionHeader(soup, section, TOCMap, TOCDesc):
    
    body = soup.find('div',class_="toctree-wrapper compound")
    
    tag = body.find(id=section)
    
    # FROM        
    # <span id="document-Introduction"></span><div class="section" id="introduction">
    # <h2>Introduction<a class="headerlink" href="#introduction" title="Permalink to this headline"></a></h2>
    # <p>Slamdunk maps and analyzes SLAM-Seq data.</p>
    # </div>
    
    # TO
    
    # <div class="docs_section">
    # <h1 class="section-header" id="document-Introduction"><a href="#document-Introduction" class="header-link"><span class="glyphicon glyphicon-link"></span></a>Introduction</h1>
    # <div class="docs_block" id="Introduction.rst"><p>Slamdunk maps and analyzes SLAM-Seq data.</p>
    # </div>
    # </div>

    if tag.name == "span":
              
        content = tag.next_sibling
        content['class'] = "docs_section"
        del content['id']
        sectionName = content.h2.contents[0]
        
        TOCDesc[section] = sectionName
        
        header = content.h2
        header.name = "h1"
        header['class'] = "section-header"
        header['id'] = section
        header.contents[0] = ""
        permalink = content.a
        permalink['class'] = "header-link"
        permalink['href'] = "#" + section
        del permalink['title']
        permalink.string = ""
        
        glyphlink = soup.new_tag("span")
        glyphlink["class"] = "glyphicon glyphicon-link"
        permalink.append(glyphlink)
        
        header.append(str(sectionName))
        
        data = soup.new_tag("div", class_="docs_block", id = section)
        
        sibling = glyphlink.parent.parent.next_sibling
        
        while sibling :
            data.append(sibling)
            sibling = glyphlink.parent.parent.next_sibling
            
        content.append(data)
        
        tag.decompose()
        
    # FROM
        
    # <div class="section" id="requirements">
    # <h3>Requirements<a class="headerlink" href="#requirements" title="Permalink to this headline"></a></h3>
    # TO
    # <h1 id="requirements"><a href="#requirements" class="header-link"><span class="glyphicon glyphicon-link"></span></a>Requirements</h1>
    # <div class="section" id="requirements">

    elif tag.name == "div":
        
        header = tag.find(re.compile("^h"))
        header.name = "h" + str(TOCMap[section] - 1)
        header["id"] = section

        for child in header.children:
            if isinstance(child, NavigableString):
                sectionName = child
            if isinstance(child, Tag) and child.name == "a":
                permalink = child
         
        TOCDesc[section] = sectionName
            
        permalink['class'] = "header-link"
        permalink['href'] = "#" + section
        del permalink['title']
        permalink.string = ""
        
        glyphlink = soup.new_tag("span")
        glyphlink["class"] = "glyphicon glyphicon-link"
        permalink.append(glyphlink)
        
        header.contents[0] = ""
        
        if len(header.contents) < 3 :
        
            header.append(str(sectionName))

# TOC FORMAT

# <ul class="nav nav-stacked">
# <li><a href="#document-Introduction">Introduction</a>
# <li><a href="#installation">installation</a>
# <ul class="nav nav-stacked">
# <li><a href="#requirements">Requirements</a>
# <li><a href="#python-package-index">PyPI</a>
# <li><a href="#source">Source</a></li>
# </ul>

def buildTOC(tocContent, toc, TOCDesc, curNode, level = 0) :
    for k, v in toc.iteritems():
        
        list = tocContent.new_tag("li")
        link = tocContent.new_tag("a", href="#" + k)
        link.string = TOCDesc[k]
        curNode.append(list)
        list.append(link)

        if v:
            ul = tocContent.new_tag("ul")
            ul['class'] = "nav nav-stacked"
            list.append(ul)
            buildTOC(tocContent, v, TOCDesc, ul, level + 1)
    
def walkthroughTOC(soup, toc, TOCMap, TOCDesc, level = 0):
    for k, v in toc.iteritems():
        reformatSectionHeader(soup, k, TOCMap, TOCDesc)
        if v:
            walkthroughTOC(soup, v, TOCMap, TOCDesc, level + 1)


 # Info
usage = "Parsing SingleHtml sphinx-build into documentation html"
version = "1.0"

# Main Parsers
parser = ArgumentParser(description=usage, formatter_class=RawDescriptionHelpFormatter, version=version)

parser.add_argument("-s", "--singleHtml", type=str, required=True, dest="singleHtmlFile", help="singleHtml file from sphinx-build")
parser.add_argument("-t", "--templateHtml", type=str, required=True, dest="templateHtmlFile", help="Template html file to insert docs into")

args = parser.parse_args()

########################################
# Read template
########################################

templateDocTree = BeautifulSoup(open(args.templateHtmlFile), "lxml")

tocNode = None
contentNode = None

# Find hooks for content and toc

for comment in templateDocTree.findAll(text=lambda text:isinstance(text, Comment)):
    if comment.string == "CONTENT-PLACEHOLDER":
        contentNode = comment.parent
    if comment.string == "TOC-PLACEHOLDER":
        tocNode = comment.parent

########################################
# Read docs
########################################

soup = BeautifulSoup(open(args.singleHtmlFile), "lxml")

########################################
# Parse TOC
########################################

TOC = OrderedDict()
TOCMap = {}
TOCDesc = {}

# This marks the beginning of the TOC <div class="sphinxsidebarwrapper">

tocTag = soup.find("div", class_="sphinxsidebarwrapper")

# TOC entries look like this <li class="toctree-l1">

tocLevels = []

prevLevel = 1
prevName = ""

for li in tocTag.find_all("li"):
    
    name = ""
    
    for child in li.children:
        if child.name == "a":
            name = child['href']
            name = re.sub("index.html#","",name)
    
    if (prevLevel < int(li['class'][0][-1])):
        tocLevels.append(prevName)
        set(TOC, tocLevels, name)
        prevLevel = int(li['class'][0][-1])
        
    elif (prevLevel > int(li['class'][0][-1])):
        diff = prevLevel - int(li['class'][0][-1])
        for x in range(0, diff):
            tocLevels.pop()
        set(TOC, tocLevels, name)
        prevLevel = int(li['class'][0][-1])
        
    else :
        set(TOC, tocLevels, name)
        
    TOCMap[name] = int(li['class'][0][-1])
    
    prevName = name

####################################################
# Replace headers in doc content and add to template
####################################################

walkthroughTOC(soup, TOC, TOCMap, TOCDesc)

docContent = soup.find('div',class_="toctree-wrapper compound")

contentNode.append(docContent)

####################################################
# Build TOC and add to template
####################################################

tocContent = BeautifulSoup("", 'lxml')

ul = tocContent.new_tag("ul")
ul['class'] = "nav nav-stacked"
tocContent.append(ul)
list = tocContent.new_tag("li")
curNode = ul
curNode.append(list)

buildTOC(tocContent, TOC, TOCDesc, list)

tocNode.append(tocContent)

print(templateDocTree.prettify('utf-8'))