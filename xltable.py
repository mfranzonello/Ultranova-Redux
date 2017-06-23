'''Import data from named Table in local or hosted Excel file to pandas dataframe'''
import pandas,zipfile,fnmatch
import requests,io
from typing import List
from typing import Tuple
from xml.etree import ElementTree

class RawXL:
    def __init__(self,file:str):
        '''Intialize object'''
        self.file = file
        self.tables = {}
        self.sheetnames = []
        self._find_link()
        self._unzip()
        self._get_table_info()
        self._read_tables()
        self._name_sheets()

    def __repr__(self):
        '''Print raw info'''
        string1 = 'Filename: {}\n'.format(self.file)
        string2 = 'Tables:\n' + ''.join(' {}: sheet {}, range {}\n'.format(self.tables[t]['name'],
                                                                           self.tables[t]['sheetname'],
                                                                           self.tables[t]['ref']) for t in self.tables)
        string = string1+string2
        return string

    def __getitem__(self,table_name):
        '''Return specific table'''
        df = self.data[table_name.lower()]
        return df

    def _find_link(self):
        '''Return openable file'''
        if fnmatch.fnmatch(self.file,'http*:*'):
            r = requests.get(self.file,stream=True)
            self.link = io.BytesIO(r.content)
        else:
            self.link = self.file

    def _unzip(self):
        '''Pull from local file or web and read as zip file'''
        self.xl = zipfile.ZipFile(self.link)

    def _get_table_info(self):
        '''Get all files in zip of Excel file'''
        namelist = self.xl.namelist()
        # get all tables
        table_list = fnmatch.filter(namelist,'xl/tables/*.xml') # tables/table*.xml
        # get all sheet relationships
        sheet_list = fnmatch.filter(namelist,'xl/worksheets/_rels/*.xml.rels')
        # set up matching
        tables = {}
        for table in table_list:
            root = ElementTree.parse(self.xl.open(table)).getroot()
            # assign name and range to table id
            tables[self._strip_table(table,'xml')] = {attribute: root.get(attribute) for attribute in ['name','ref']}
        for sheet in sheet_list:
            # get all relationships and keep sheet info
            relationships = ElementTree.parse(self.xl.open(sheet)).findall('*')
            for relationship in relationships:
                items = relationship.items()
                found = False
                for item in items:
                    for i in item:
                        if fnmatch.fnmatch(i,'*table*.xml'):
                            found = True
                            tables[self._strip_table(i,'rels')]['sheet'] = self._strip_sheet(sheet)
                            break
                    if found:
                        break
        self.tables = tables

    def _strip_table(self,table_name:str,source:str) -> int:
        '''Get table number from XML data'''
        if source=='xml':
            strip_part = 'xl'
        elif source=='rels':
            strip_part = '..'
        stripped = int(table_name.replace('{}/tables/table'.format(strip_part),'').replace('.xml',''))
        return stripped

    def _strip_sheet(self,sheet_name:str) -> int:
        '''Get sheet number from XML data (0-indexed)'''
        stripped = int(sheet_name.replace('xl/worksheets/_rels/sheet','').replace('.xml.rels',''))-1
        return stripped

    def _read_tables(self):
        '''Read each named table to a dictionary of dataframes'''
        xl_file = pandas.ExcelFile(self.file)
        self.sheetnames = xl_file.sheet_names

        dataframes = {}
        for table in self.tables:
            xl_range = self.tables[table]['ref']
            sheetnum = self.tables[table]['sheet']
            parse_c,skip_r,height = self.split_range(xl_range)
            df = xl_file.parse(sheetname=sheetnum,skiprows=skip_r,parse_cols=parse_c).iloc[0:height]
            dataframes[self.tables[table]['name'].lower()] = df
        self.data = dataframes

    def _split_range(self,string:str) -> Tuple[int]:
        '''Translate Excel reference to pandas numbers'''
        left = string[0:string.index(':')]
        right = string[string.index(':')+1:]
        letters = []
        numbers = []
        for side in [left,right]:
            letter = ''.join(s for s in side if not s.isdigit())
            number = int(''.join(s for s in side if s.isdigit()))
            letters += [letter]
            numbers += [number]
        parse_c = '{}:{}'.format(letters[0],letters[1])
        skip_r = numbers[0]-1
        height = numbers[1]-numbers[0]
        return parse_c,skip_r,height

    def _name_sheets(self):
        '''Give Excel name to sheets'''
        for table in self.tables:
            sheetnum = self.tables[table]['sheet']
            self.tables[table]['sheetname'] = sheetnum #self.sheetnames[sheetnum]