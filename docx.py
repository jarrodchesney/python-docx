#!/usr/bin/env python2.6
'''
Open and modify Microsoft Word 2007 docx files (called 'OpenXML' and 'Office OpenXML' by Microsoft)

Part of Python's docx module - http://github.com/mikemaccana/python-docx
See LICENSE for licensing information.
'''

from lxml import etree
import zipfile
import re
import time
import os

# All Word prefixes / namespace matches used in document.xml & core.xml.
# LXML doesn't actually use prefixes (just the real namespace) , but these
# make it easier to copy Word output more easily. 
nsprefixes = {
    # Text Content
    'mv':'urn:schemas-microsoft-com:mac:vml',
    'mo':'http://schemas.microsoft.com/office/mac/office/2008/main',
    've':'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'o':'urn:schemas-microsoft-com:office:office',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'v':'urn:schemas-microsoft-com:vml',
    'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'w10':'urn:schemas-microsoft-com:office:word',
    'wne':'http://schemas.microsoft.com/office/word/2006/wordml',
    # Drawing
    'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic':'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'cp':"http://schemas.openxmlformats.org/package/2006/metadata/core-properties", 
    'dc':"http://purl.org/dc/elements/1.1/", 
    'dcterms':"http://purl.org/dc/terms/",
    'dcmitype':"http://purl.org/dc/dcmitype/",
    'xsi':"http://www.w3.org/2001/XMLSchema-instance",
    # Content Types (we're just making up our own namespaces here to save time)
    'ct':'http://schemas.openxmlformats.org/package/2006/content-types',
    }

def opendocx(file):
    '''Open a docx file, return a document XML tree'''
    mydoc = zipfile.ZipFile(file)
    xmlcontent = mydoc.read('word/document.xml')
    document = etree.fromstring(xmlcontent)    
    return document

def newdocument():
    document = makeelement('document')
    document.append(makeelement('body'))
    return document

def makeelement(tagname,tagtext=None,nsprefix='w',attributes=None,attrnsprefix=None):
    '''Create an element & return it''' 
    if nsprefix:
        namespace = '{'+nsprefixes[nsprefix]+'}'
    else:
        # For when namespace = None
        namespace = ''
    newelement = etree.Element(namespace+tagname)
    # Add attributes with namespaces
    if attributes:
        # If they haven't bothered setting attribute namespace, use an empty string
        # (equivalent of no namespace)
        if not attrnsprefix:
            # Quick hack: it seems every element that has a 'w' nsprefix for its tag uses the same prefix for it's attributes  
            if nsprefix == 'w':
                attributenamespace = namespace
            else:
                attributenamespace = ''
        else:
            attributenamespace = '{'+nsprefixes[attrnsprefix]+'}'
                    
        for tagattribute in attributes:
            newelement.set(attributenamespace+tagattribute, attributes[tagattribute])
    if tagtext:
        newelement.text = tagtext    
    return newelement

def pagebreak(type='page', orient='portrait'):
    '''Insert a break, default 'page'.
    See http://openxmldeveloper.org/forums/thread/4075.aspx
    Return our page break element.'''
    # Need to enumerate different types of page breaks.
    if type not in ['page', 'section']:
        raiseError('Page break style "%s" not implemented.' % type)
    pagebreak = makeelement('p')
    if type == 'page':
        run = makeelement('r')
        br = makeelement('br',attributes={'type':type})
        run.append(br)
        pagebreak.append(run)
    elif type == 'section':
        pPr = makeelement('pPr')
        sectPr = makeelement('sectPr')
        if orient == 'portrait':
            pgSz = makeelement('pgSz',attributes={'w':'12240','h':'15840'})
        elif orient == 'landscape':
            pgSz = makeelement('pgSz',attributes={'h':'12240','w':'15840', 'orient':'landscape'})
        sectPr.append(pgSz)
        pPr.append(sectPr)
        pagebreak.append(pPr)
    return pagebreak    

def paragraph(paratext,style='BodyText',breakbefore=False):
    '''Make a new paragraph element, containing a run, and some text. 
    Return the paragraph element.'''
    # Make our elements
    paragraph = makeelement('p')
    run = makeelement('r')    
    
    # Insert lastRenderedPageBreak for assistive technologies like
    # document narrators to know when a page break occurred.
    if breakbefore:
        lastRenderedPageBreak = makeelement('lastRenderedPageBreak')
        run.append(lastRenderedPageBreak)    
    text = makeelement('t',tagtext=paratext)
    pPr = makeelement('pPr')
    pStyle = makeelement('pStyle',attributes={'val':style})
    pPr.append(pStyle)
                
    # Add the text the run, and the run to the paragraph
    run.append(text)    
    paragraph.append(pPr)    
    paragraph.append(run)    
    # Return the combined paragraph
    return paragraph

def contenttypes():
    # FIXME - doesn't quite work...read from string as temp hack...
    #types = makeelement('Types',nsprefix='ct')
    types = etree.fromstring('''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>''')

    parts = {
        '/word/theme/theme1.xml':'application/vnd.openxmlformats-officedocument.theme+xml',
        '/word/fontTable.xml':'application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml',
        '/docProps/core.xml':'application/vnd.openxmlformats-package.core-properties+xml',
        '/docProps/app.xml':'application/vnd.openxmlformats-officedocument.extended-properties+xml',
        '/word/document.xml':'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml',
        '/word/settings.xml':'application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml',
        '/word/numbering.xml':'application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml',
        '/word/styles.xml':'application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml',
        '/word/webSettings.xml':'application/vnd.openxmlformats-officedocument.wordprocessingml.webSettings+xml'
        }
    for part in parts:
        types.append(makeelement('Override',nsprefix=None,attributes={'PartName':part,'ContentType':parts[part]}))

    # Add support for filetypes
    filetypes = {'rels':'application/vnd.openxmlformats-package.relationships+xml','xml':'application/xml','jpeg':'image/jpeg','gif':'image/gif','png':'image/png'}
    for extension in filetypes:
        types.append(makeelement('Default',nsprefix=None,attributes={'Extension':extension,'ContentType':filetypes[extension]}))


    return types

def heading(headingtext,headinglevel):
    '''Make a new heading, return the heading element'''
    # Make our elements
    paragraph = makeelement('p')
    pr = makeelement('pPr')
    pStyle = makeelement('pStyle',attributes={'val':'Heading'+str(headinglevel)})    
    run = makeelement('r')
    text = makeelement('t',tagtext=headingtext)
    # Add the text the run, and the run to the paragraph
    pr.append(pStyle)
    run.append(text)
    paragraph.append(pr)   
    paragraph.append(run)    
    # Return the combined paragraph
    return paragraph   


def table(contents):
    '''Get a list of lists, return a table'''
    table = makeelement('tbl')
    columns = len(contents[0][0])    
    # Table properties
    tableprops = makeelement('tblPr')
    tablestyle = makeelement('tblStyle',attributes={'val':'ColorfulGrid-Accent1'})
    tablewidth = makeelement('tblW',attributes={'w':'0','type':'auto'})
    tablelook = makeelement('tblLook',attributes={'val':'0400'})
    for tableproperty in [tablestyle,tablewidth,tablelook]:
        tableprops.append(tableproperty)
    table.append(tableprops)    
    # Table Grid    
    tablegrid = makeelement('tblGrid')
    for _ in range(columns):
        tablegrid.append(makeelement('gridCol',attributes={'gridCol':'2390'}))
    table.append(tablegrid)     
    # Heading Row    
    row = makeelement('tr')
    rowprops = makeelement('trPr')
    cnfStyle = makeelement('cnfStyle',attributes={'val':'000000100000'})
    rowprops.append(cnfStyle)
    row.append(rowprops)
    for heading in contents[0]:
        cell = makeelement('tc')  
        # Cell properties  
        cellprops = makeelement('tcPr')
        cellwidth = makeelement('tcW',attributes={'w':'2390','type':'dxa'})
        cellstyle = makeelement('shd',attributes={'val':'clear','color':'auto','fill':'548DD4','themeFill':'text2','themeFillTint':'99'})
        cellprops.append(cellwidth)
        cellprops.append(cellstyle)
        cell.append(cellprops)        
        # Paragraph (Content)
        cell.append(paragraph(heading))
        row.append(cell)
    table.append(row)            
    # Contents Rows   
    for contentrow in contents[1:]:
        row = makeelement('tr')     
        for content in contentrow:   
            cell = makeelement('tc')
            # Properties
            cellprops = makeelement('tcPr')
            cellwidth = makeelement('tcW',attributes={'type':'dxa'})
            cellprops.append(cellwidth)
            cell.append(cellprops)
            # Paragraph (Content)
            cell.append(paragraph(content))
            row.append(cell)    
        table.append(row)   
    return table                 

def picture():
    '''Create a pragraph containing an image - FIXME - not implemented yet'''
    # Word uses paragraphs to contain images
    # http://openxmldeveloper.org/articles/462.aspx
    #resourceid = rId5
    #newrelationship = makeelement('Relationship',attributes={'Id':resourceid,'Type':'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'},Target=filename)
    
    # Now make drawing element

    
    blipfill = makeelement('blipFill',nsprefix='pic')
    blipfill.append(makeelement('blip',nsprefix='a',attributes={'embed':'rId7'}))
    stretch = makeelement('stretch',nsprefix='a')
    stretch.append(makeelement('fillRect',nsprefix='a'))
    blipfill.append(stretch)

    sppr = makeelement('spPr',nsprefix='pic')
    xfrm = makeelement('xfrm',nsprefix='a')
    xfrm.append(makeelement('off',nsprefix='a',attributes={'x':'0','y':'0'}))
    xfrm.append(makeelement('ext',nsprefix='a',attributes={'cx':'2672715','cy':'900430'}))
    prstgeom = makeelement('prstGeom',nsprefix='a',attributes={'prst':'rect'})
    prstgeom.append(makeelement('avLst',nsprefix='a'))
    sppr.append(xfrm)
    sppr.append(prstgeom)

    nvpicpr = makeelement('nvPicPr',nsprefix='pic')
    # FIXme: why id 2?
    cnvpr = makeelement('cNvPr',nsprefix='pic',attributes={'id':'2','name':'image1.png'})
    cnvpicpr = makeelement('cNvPicPr',nsprefix='pic')
    nvpicpr.append(cnvpicpr)
    nvpicpr.append(cnvpr)
    
    pic = makeelement('pic',nsprefix='pic')
    pic.append(blipfill)
    pic.append(sppr)
    pic.append(nvpicpr)

    graphicdata = makeelement('graphicData',nsprefix='a',attributes={'uri':'http://schemas.openxmlformats.org/drawingml/2006/picture'})
    graphicdata.append(pic)

    graphic = makeelement('graphic',nsprefix='a')
    graphic.append(graphicdata)

    framepr = makeelement('cNvGraphicFramePr',nsprefix='wp')
    framelocks = makeelement('graphicFrameLocks',nsprefix='a',attributes={'noChangeAspect':'1'})
    framepr.append(framelocks)

    makeelement('drawing')
    inline = makeelement('inline',attributes={'distT':"0",'distB':"0",'distL':"0",'distR':"0"},nsprefix='wp')
    extent = makeelement('extent',nsprefix='wp',attributes={'cx':'5486400','cy':'3429000'})
    effectextent = makeelement('effectExtent',nsprefix='wp',attributes={'l':'25400','t':'0','r':'0','b':'0'})
    docpr = makeelement('docPr',nsprefix='wp',attributes={'id':'1','name':'Picture 0','descr':'image1.png'})
    inline.append(extent)
    inline.append(effectextent)
    inline.append(docpr)
    inline.append(framepr)
    inline.append(graphic)    
    
    # Add the text the run, and the run to the paragraph
    '''Getting rid of the string, step by step...'''

    
    precut = etree.fromstring('''
    			<wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
    				<wp:extent cx="2672715" cy="900430"/>
    				<wp:effectExtent l="25400" t="0" r="0" b="0"/>
    				<wp:docPr id="2" name="Picture 1" descr="http://github.com/mikemaccana/python-docx/raw/master/template/word/media/image1.png"/>
    				<wp:cNvGraphicFramePr>
    					<a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>
    				</wp:cNvGraphicFramePr>
    				<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    					<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
    						<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
    							<pic:nvPicPr>
    								<pic:cNvPr id="0" name="Picture 1" descr="http://github.com/mikemaccana/python-docx/raw/master/template/word/media/image1.png"/>
    								<pic:cNvPicPr>
    									<a:picLocks noChangeAspect="1" noChangeArrowheads="1"/>
    								</pic:cNvPicPr>
    							</pic:nvPicPr>
    							<pic:blipFill>
    								<a:blip r:embed="rId5" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>
    								<a:srcRect/>
    								<a:stretch>
    									<a:fillRect/>
    								</a:stretch>
    							</pic:blipFill>
    							<pic:spPr bwMode="auto">
    								<a:xfrm>
    									<a:off x="0" y="0"/>
    									<a:ext cx="2672715" cy="900430"/>
    								</a:xfrm>
    								<a:prstGeom prst="rect">
    									<a:avLst/>
    								</a:prstGeom>
    								<a:noFill/>
    								<a:ln w="9525">
    									<a:noFill/>
    									<a:miter lim="800000"/>
    									<a:headEnd/>
    									<a:tailEnd/>
    								</a:ln>
    							</pic:spPr>
    						</pic:pic>
    					</a:graphicData>
    				</a:graphic>
    			</wp:inline>
    ''')
    # Make element, add it's children
    drawing = makeelement('drawing')
    drawing.append(precut)
    run = makeelement('r')
    run.append(drawing)
    paragraph = makeelement('p')
    paragraph.append(run)
    
    
    #run.append(drawing)
        
    
    return paragraph
    


def search(document,search):
    '''Search a document for a regex, return '''
    results = False
    searchre = re.compile(search)
    for element in document.iter():
        if element.tag == 'w'+'t':
            if element.text:
                if searchre.match(element.text):
                    results = True
    return results

def replace(document,search,replace):
    '''Replace all occurences of string with a different string, return updated document'''
    newdocument = document
    searchre = re.compile(search)
    for element in newdocument.iter():
        if element.tag == 'w'+'t':
            if element.text:
                if searchre.search(element.text):
                    element.text = re.sub(search,replace,element.text)
    return newdocument


def getdocumenttext(document):
    '''Return the raw text of a document, as a list of paragraphs.'''
    paratextlist=[]   
        
    # Compile a list of all paragraph (p) elements
    paralist = []
    for element in document.iter():
        # Find p (paragraph) elements
        if element.tag == '{'+nsprefixes['w']+'}p':
            paralist.append(element)
    
    # Since a single sentence might be spread over multiple text elements, iterate through each 
    # paragraph, appending all text (t) children to that paragraphs text.     
    for para in paralist:      
        paratext=u''  
        # Loop through each paragraph
        for element in para.iter():
            # Find t (text) elements
            if element.tag == '{'+nsprefixes['w']+'}t':
                if element.text:
                    paratext = paratext+element.text

        # Add our completed paragraph text to the list of paragraph text    
        if not len(paratext) == 0:
            paratextlist.append(paratext)                    
    return paratextlist        

def docproperties(title,subject,creator,keywords,lastmodifiedby=None):
    '''Makes document properties. '''
    # OpenXML uses the term 'core' to refer to the 'Dublin Core' specification used to make the properties.  
    docprops = makeelement('coreProperties',nsprefix='cp')    
    docprops.append(makeelement('title',tagtext=title,nsprefix='dc'))
    docprops.append(makeelement('subject',tagtext=subject,nsprefix='dc'))
    docprops.append(makeelement('creator',tagtext=creator,nsprefix='dc'))
    docprops.append(makeelement('keywords',tagtext=','.join(keywords),nsprefix='cp'))    
    if not lastmodifiedby:
        lastmodifiedby = creator
    docprops.append(makeelement('lastModifiedBy',tagtext=lastmodifiedby,nsprefix='cp'))
    docprops.append(makeelement('revision',tagtext='1',nsprefix='cp'))
    docprops.append(makeelement('category',tagtext='Examples',nsprefix='cp'))
    docprops.append(makeelement('description',tagtext='Examples',nsprefix='dc'))
    currenttime = time.strftime('%Y-%m-%dT-%H:%M:%SZ')
    # FIXME - creating these items manually fails - but we can live without them for now.
    '''	What we're going for:
    <dcterms:created xsi:type="dcterms:W3CDTF">2010-01-01T21:07:00Z</dcterms:created>
    <dcterms:modified xsi:type="dcterms:W3CDTF">2010-01-01T21:20:00Z</dcterms:modified>
    currenttime'''
    edittimes = {'created':'2010-01-01T21:07:00Z','modified':'2010-01-01T21:07:00Z'}
    for edit in edittimes:
        #docprops.append(makeelement(edit,nsprefix='dcterms',attrnsprefix='xsi',
        #attributes={'type':'W3CDTF'},tagtext=edittimes[edit]))
        pass
    return docprops

def websettings():
    '''Generate websettings'''
    web = makeelement('webSettings')
    web.append(makeelement('allowPNG'))
    web.append(makeelement('doNotSaveAsSingleFile'))
    return web

def savedocx(document,properties,contenttypes,websettings,docxfilename):
    '''Save a modified document'''
    docxfile = zipfile.ZipFile(docxfilename,mode='w')
    # Serialize our trees into out zip file
    treesandfiles = {document:'word/document.xml',properties:'docProps/core.xml',contenttypes:'[Content_Types].xml',websettings:'word/webSettings.xml'}
    for tree in treesandfiles:
        treestring = etree.tostring(tree, pretty_print=True)
        docxfile.writestr(treesandfiles[tree],treestring)
    
    # Add & compress support files
    for dirpath,dirnames,filenames in os.walk('template'):
        for filename in filenames:
            templatefile = os.path.join(dirpath,filename)
            archivename = templatefile.lstrip('/template/')   
            print 'Saving: '+archivename          
            docxfile.write(templatefile, archivename, zipfile.ZIP_DEFLATED)
    print 'Saved new file to: '+docxfilename
    return
    
