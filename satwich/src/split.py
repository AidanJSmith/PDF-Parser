# -*- coding: utf-8 -*-
import fitz
import sys
import re
import collections 
import os
import json

"""
https://github.com/pymupdf/PyMuPDF-Utilities/tree/master/examples
Steps:
  Prepass:
    Figure out which pages have tables and set them for later handling; put them through some separate functions to handle that. Certain diagram pages (see 28) are a mix of text and diagrams... we'll need to give parsing these more thought.
    Parse images/map them to pages in the big dict. (b64?)
  Primary pass:
    Dump all of the nondiagram pages to image first, save them to the images dir.
    Dump all of the text and cut out "unauthorized use" etc as well as page number + asterisk divisors + "continue" + "stop" + headers. (which should be used internally to decide when certain segments are over)
    Split it into text portions and questions portions. Put them under test "directories" in a big JSON.
    
    Figure out some way to parse inline numbers. I.e: 12 bird. This was a bird that was... (see page 22 of the PDF)
    
    
    To-Do: 🍞🧀🥓🍅🥬🍞
      Further parsing on the actual text to cut out the two question idiosyncrasy of the regexes.
      Retrieve answers.
      Writing section, math w/ calc, math w/out calc
"""

#Remove artifacts from a passed writing object
def sanitize_writing(writing):
    modwriting=writing
    for item in modwriting.keys():
        for num,page in enumerate(modwriting[item]):
            passage=modwriting[item][num][0]
            passage=re.sub("Unauthorized copying or reuse of any part of this page is illegal.","",passage);
            passage=re.sub("\n\d+","",passage);
            questions=modwriting[item][num][1];
            for key in modwriting[item][num][1]:
                question=modwriting[item][num][1][key]
                question=re.sub("\d+\s+","",question)
                questions[key]=re.sub("[\s]{3,}[\s\S]+","",question)
            modwriting[item][num][0]=passage
    return modwriting 
#Remove artifacts from a passed reading object 
def sanitize_reading(reading):
    modreading=reading
    for item in reading.keys():
        passage=modreading[item][0]
        questions=modreading[item][1]
        #sanitize the passage
        passage=re.sub("(CONTINUE)|(STOP)","\n",passage)
        passage=re.sub("\n+\d{1,}","",passage)
        passage=re.sub("\s{3,}","\n\n",passage)
        passage=re.sub("\nLine\n","\n",passage)
        passage=re.sub("Unauthorized copying or reuse of any part of this page is illegal.","",passage)
        modreading[item][0]=passage
        #sanitize questions
        for questionnum in modreading[item][1].keys():
            #Do stuff
            question=modreading[item][1][questionnum]
            question=re.sub("\d+\s+","",question)
            modreading[item][1][questionnum]=re.sub("[\s]{3,}[\s\S]+","",question)
            pass
    return modreading
# Reading parser
def parse_reading(start, end,pages):
    keyword = "are based on the" 
    reading_pages = pages[start:end]
    reading = {}
    # reading.update(section : passage : [ "",{ qnumber : [question,answer]}])
    currentpassage = 0
    currentquestion = 1
    searching_question = False
                    
        #So, I *think* questions are going to look like questionNum\n\n\n?

    for num,page in enumerate(reading_pages):
        if "D)" not in page.split(keyword)[0]:
            searching_question=False
        elif keyword in page.lower():
            questions_on_page = re.findall("\d+[\s\S]+?D\)[\s\S]*?\n+?",page.split(keyword)[0].split("Questions")[0]+"\n1")                 # I'm a regex wizard.  🍞🧀🥓🍅🥬🍞
            for question in questions_on_page:
                if "Figure 1" not in question and "Figure 2" not in question and "D)" in question:  # Ignore figures, if they split through
                    reading[str(currentpassage)][1].update( {str(currentquestion) : re.sub("[\s\S]+?(?=\n{2})","",question) })
                    currentquestion+=1
            searching_question=False        # If this is the start of a passage:
        if keyword in page.lower():         # Start the construction for a passage start
            page = page.split(keyword)[1]   # Remove the bits before the reading passage
            bonusq = page.split(keyword)[0]   # Remove the bits before the reading passage
            if "D)" in bonusq:
                print("AAA")
            # Increment passage & question
            currentpassage += 1
            # Add the passage to the array and set it to the current one
            reading.update( {str(currentpassage) : ["", {},[]]} )
            #passage = reading[currentpassage][0] #I think this is the problem. You can't assign to a mem location like this in python? smh

            formattedquestion = "\n{0}".format(currentquestion)
            if  re.search("A\).*\\nB\).*\\nC\).*\\nD\).*",page) != None:
                reading[str(currentpassage)][0] += page
                searching_question = True # Once we hit the end phrase, start scanning the PDF for questions.
            else:
                reading[str(currentpassage)][0] += page 

            # If this is a page of questions following a passage:
        elif currentpassage > 0:    
            # Format question and set current passage
            formattedquestion = "\n{0}".format(currentquestion)
            if re.search("A\)?",page) != None:
                reading[str(currentpassage)][0] += page[:re.search("A\)?",page).span()[0]]
                searching_question = True
        if (searching_question):                                                                    # Use regexes to find portions that start with at least one digit (?#) and end in the line following D) 
            questions_on_page = re.findall("\d+[\s\S]+?D\)?[\s\S]*?\n+(?=\d)",page)                 # I'm a regex wizard.  🍞🧀🥓🍅🥬🍞
            for question in questions_on_page:
                if "Figure 1" not in question and "Figure 2" not in question and "D)" in question:  # Ignore figures, if they split through
                    reading[str(currentpassage)][1].update( {str(currentquestion) : re.sub("[\s\S]+?(?=\n{2})","",question) })
                    currentquestion+=1
        reading[str(currentpassage)][2].append(num+start)
    return sanitize_reading(reading)
    
#Writing parser
def parse_writing(start, end,pages):
    keyword = " are based on the following passage" 
    writing_pages = pages[start:end]
    writing = {}
    # writing.update(section : [ "pagenum":[text,contents])
    currentpassage = 0
    currentquestion = 1
    temp_info=""
    temp_questions={}
    for num,page in enumerate(writing_pages):
        temp_questions={}
        modpage=page
        if keyword in page.lower():                                                     # Start the construction for a passage start
            # Increment passage & question
            currentpassage += 1
            writing.update( {str(currentpassage) : []} )
            modpage=modpage.split(keyword)[1]
        #Find all questions on the page and append them to the current passage object
        temp_info= re.findall("(?<!A\))[\s\S]+?\s{1}?(?=A\))",modpage)[0]               # What this regex actually does is look for parts of the page that do not have a A) preceding them, followed by only one space before an A) This captures only the passage.
        temp_info= temp_info.split("\n \n ")[0]
        modpage=modpage.replace(temp_info,"")                                           # Once we've cached the passage, remove it such that we can move on to the questions.
        modpage=str(currentquestion)+modpage      
        if currentpassage==1 and "annihilating" in page:
            print(temp_info)                                      # Add a number at the beginning of the question, as the question parsing regex is dependent on it.
        questions_on_page = re.findall("\d+[\s\S]+?D\)?[\s\S]*?\n+(?=\d)",modpage)      # Find all of the valid questions in the remainder of the page       
        for question in questions_on_page:
            temp_questions.update({str(currentquestion) : question })
            currentquestion+=1
        # Find the text, append it to a new page object of the current passage object
        writing[str(currentpassage)].append([temp_info,temp_questions,num+start])                 # Write the current page to the correct passage subheader.
    return sanitize_writing(writing)
 
 
#Math parser (Nemo's Job, lucky him)

#CalcMath parser (Nemo's Job, lucky him)
def getTest(pdf,testname="example"):
    if not os.path.isdir(os.getcwd()+"\\src\\"+"./data/tests/{0}".format(testname)):
        os.makedirs(os.getcwd()+"\\src\\"+"./data/tests/{0}".format(testname))
        os.makedirs(os.getcwd()+"\\src\\"+"./data/tests/{0}/images".format(testname))
    pdffile = pdf  # Some url to PDF
    doc = fitz.open(pdffile)        # This is a generator.
    page = doc.loadPage(1)          # Load some page
    pages=[]                        # Array of all pages
    pages_raw=[]
    for page in doc:                # Init pages
        pages.append(page.getText())
        pages_raw.append(page)
        pix = page.getPixmap()
        output =os.getcwd()+"\\src\\"+"./data/tests/{0}/images/{1}.png".format(testname,page.number)
        pix.writePNG(output)
    lastpage=page
    startread=startwrite=startmath=startcalc=0
    for num,page in enumerate(pages):
        if("reading test" in page.lower()):
            startread=num
        if("writing and language test" in page.lower()):
            startwrite=num
        if("math test" in page.lower() and "no calculator" in page.lower()):
            startmath=num
        elif ("math test" in page.lower() and "calculator" in page.lower()):
            startcalc=num

    reading=parse_reading(startread,startwrite,pages)
    writing=parse_writing(startwrite,startmath,pages)
    #get the number of questions in writing
    reading_qnum=0
    for item in reading:
        for question in reading[item][1]:
            reading_qnum+=1
    #get the number of questions in reading
    writing_qnum=0
    for item in writing.keys():
        for num,page in enumerate(writing[item]):
            for key in writing[item][num][1]:
                writing_qnum+=1
    #get the number of questions in math Note to Nemo: Add your code here to count number of questions
    nocalc_qnum=20
    #get the number of questions in calc.
    calc_qnum=38

    #Use a queue to create a key object
    keyqueue=collections.deque(lastpage.getText().split("\n")[5:])
    key=dict(reading={},writing={},nocalc={},calc={})
    current_question=1
    while current_question<=max(calc_qnum,nocalc_qnum,writing_qnum,reading_qnum):
        if (current_question<=reading_qnum):
            key["reading"][str(current_question)]=keyqueue.popleft()
        if (current_question<=writing_qnum):
            key["writing"][str(current_question)]=keyqueue.popleft()
        if (current_question<=nocalc_qnum):
            key["nocalc"][str(current_question)]=keyqueue.popleft()
        if (current_question<=calc_qnum):
            key["calc"][str(current_question)]=keyqueue.popleft()
        current_question+=1
        keyqueue.popleft()
            
    test={'reading':reading,"writing":writing,"key":key}  
    test = json.dumps(test)  
    with open(os.getcwd()+"\\src\\"+'./data/tests/{0}/test.json'.format(testname), 'w') as f:
        json.dump(test, f)
    return True
    



with open(os.getcwd()+'/src/last_new.json') as f:
  data = json.load(f)
  print(data)
  print(getTest(data["path"],data["name"]))