'''Extract rate information from tariff PDFs'''
import pandas,fnmatch,re,calendar,slate #PyPDF2 #collections
import retrieval

months = {v.lower(): k for k,v in enumerate(calendar.month_name)}
months.update({v.lower(): k for k,v in enumerate(calendar.month_abbr)})

class ExtractedPDF:
    def __init__(self,open_file):
        self.file = open_file.link
        self.get_contents()

    def get_contents(self):
        #pdf_reader = PyPDF2.PdfFileReader(open(self.file,'rb'))
        self.contents = slate.PDF(open(self.file,'rb'))
        self.numpages = len(self.contents)

    def get_page(self,page):
        return self.contents[page]

class RatePDFPage:
    def __init__(self,extracted_page):
        self.contents = extracted_page
        self.sort_contents(extracted_page)
        self.identify()

    def __repr__(self):
        return 'Rate: {}\nEffective: {}\nData: {}'.format(self.rate,self.effective,self.page_df.head(20))

    def sort_contents(self,extracted_page):
        '''Rebuilds table structure around number values'''
        remove = ['(I)','(I\n)','(\nI)','(R)','(R\n)','(\nR)','*','N/A']
        page_text = extracted_page
        # remove footnote identifiers
        for r in remove:
            page_text = page_text.replace(r,' ')
        # break into pieces
        page_split = page_text.split()
        # change number strings to sublists with floats
        page_split = [self.get_number(p) for p in page_split]
        # unflatten list
        page_split = [p for page in page_split for p in page if (p!='')]
        # rates start with text and end with series of numbers
        splits = [x for x in range(1,len(page_split)) if ((not(self.is_number(page_split[x]))) &\
            self.is_number(page_split[x-1]))]
        page_lines = [page_split[x:y] for (x,y) in list(zip([0]+splits[:-1],splits))]
        page_all = []
        for line in page_lines:
            numstart = min([x for x in range(len(line)) if self.is_number(line[x])])
            header = ''.join(line[:numstart])
            page_all += [[header] + line[numstart:]]
        # merge into dataframe
        self.page_df = pandas.DataFrame(page_all)

    def identify(self):
        '''Finds the effective date of page'''
        text = self.contents.lower()
        split = text.split()
        if 'schedule' in text:
            self.rate = split[split.index('schedule')+1].upper()
        else:
            self.rate = None

        if 'effective' in text:
            m,d,y = split[len(split)-split[::-1].index('effective'):][0:3]
            #try:
            year = int(y.replace(',','').replace('.',''))
            month = months[m]
            day = int(d.replace(',','').replace('.',''))
            self.effective = pandas.Timestamp(year,month,day).date() #to_pydatetime()
            #except:
            #    self.effective = None
        else:
            self.effective = None

    def get_number(self,string):
        '''Changes strings to numbers and negates if usings parentheses'''
        if (re.search(r'\((\d*\.\d*?)\)',string) is not None) | (re.search(r'\((\d*?)\)',string) is not None):
            # parentheses around number found
            neg = -1
        else:
            # any parentheses are not around number
            neg = 1
        # get parts of text
        strings = self.split_number(string)
        for s in range(len(strings)):
            if self.is_number(strings[s]):
                # return number and negate if there were parentheses
                strings[s] = neg * float(strings[s])
            else:
                # return string and remove extra parentheses
                strings[s] = strings[s].replace('()','')
        return strings

    def split_number(self,string):
        '''Breaks out the float from a string'''
        number = re.findall(r"[-+]?\d*\.\d+|\d+|$",string)[0]
        text = string.replace(number,'')
        split = [text,number]
        if (string.index(number)==0) & (number!=''):
            split = split[::-1]
        return split

    def is_number(self,val):
        '''Returns true if string is floatable'''
        try:
            float(val)
        except ValueError:
            return False
        return True

    def clean(self):
        return self.page_df

class SCERatePDFPage(RatePDFPage):
    def __init__(self,extracted_page):
        RatePDFPage.__init__(self,extracted_page)

    #def clean(self):
    #    return None

class PGERatePDFPage(RatePDFPage):
    def __init__(self,extracted_page):
        RatePDFPage.__init__(self,extracted_page)

    #def clean(self):
    #    return None

class SDGERatePDFPage(RatePDFPage):
    def __init__(self,extracted_page):
        RatePDFPage.__init__(self,extracted_page)

    #def clean(self):
    #    return None

class RateExtraction:
    def __init__(self,extracted_pdf,utility):
        Classes = {'SCE':SCERatePDFPage,
                   'PG&E':PGERatePDFPage,
                   'SDG&E':SDGERatePDFPage}
        self.pages = []
        self.numpages = extracted_pdf.numpages
        for page in range(extracted_pdf.numpages):
            rate_pdf_page = Classes[utility](extracted_pdf.get_page(page))
            rate_pdf_clean = rate_pdf_page.clean()
            self.pages += [rate_pdf_clean]

    def __repr__(self):
        return 'Pages: {}\n'.format(self.numpages)

    def __getitem__(self,page):
        return self.pages[page]

def run_pdf():
    print('Opening file')
    open_file = retrieval.OpenFile('C:/Users/Michael/Box Sync/Nova Modeling/Nova Rates/SCE/2017/TOU-8.pdf')
    print('Extracting data')
    extract_pdf = ExtractedPDF(open_file)
    #print('Getting page')
    #page_0 = extract_pdf.get_page(5)
    #print(page_0.encode('utf-8',errors='ignore'))
    #input('')
    #print('Cleaning page')
    print('Reassembling PDF')
    rate_pdf_db = RateExtraction(extract_pdf,'SCE')
    #rate_page = RatePDFPage(page_4)
    #print(rate_page)
    print('Page 10:')
    print(rate_pdf_db[10-1])

run_pdf()