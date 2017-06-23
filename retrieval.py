'''Opening files and pickled varialbes'''
import fnmatch,pickle,os
import references

class OpenFile:
    '''File that can be opened regardless of location'''
    def __init__(self,file):
        if fnmatch.fnmatch(file,'http*:*'):
            r = requests.get(file,stream=True)
            self.link = io.BytesIO(r.content)
        else:
            self.link = file

class VariableSet:
    def __init__(self,variables,project=None,strict=False):
        # reference file or project specific
        self.path = references.references_p if project is None else '{}/variables'.format(project)
        self.picklename = '{}/{}.p'.format(self.path,variables)
        self._v = {}
        self._strict = strict

    def __getitem__(self,variable):
        return self._v.get(variable)

    def exists(self):
        # check if pickle file exists
        return os.path.isfile(self.picklename)

    def load(self):
        # load variables from pickle file
        with open(self.picklename,'rb') as f:
            self._v = pickle.load(f)

    def extract(self):
        # return loaded variables
        if self._v is None:
            self.load()
        return self._v

    def add(self,name,variable):
        # add or replace variables
        self._v[name] = variable

    def save(self):
        # create needed directory
        if (not os.path.exists(self.path)) and (not self._strict):
            os.makedirs(self.path)
        # save pickle file
        if len(self._v)>0:
            with open(self.picklename,'wb') as f:
                pickle.dump(self._v,f)