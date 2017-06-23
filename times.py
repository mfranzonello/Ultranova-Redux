'''Classify seasons and periods'''
import pandas,datetime
import org,xltable
from typing import List

class TOUdb:
    def __init__(self,tables,utility):
        self.utility = utility
        self.data = tables.data
        self._refine()

    def __getattr__(self,attribute):
        return self.data.get(attribute)

    def _refine(self):
        for tbl in self.data:
            df = self.data[tbl]
            if 'utility' in df.columns:
                self.data[tbl] = df[df['utility']==self.utility.name].drop('utility',axis=1)

    def extract(self,subTOU,schedule):
        tables = ['seasons','periods','daysoff','holidays','dstadj']
        extracted = {}
        for table in tables:
            tbl = self[table]
            truth = tbl[tbl.columns[0]]==tbl[tbl.columns[0]]
            if 'subTOU' in tbl.columns:
                truth = truth & (tbl['subTOU']==subTOU)
                if 'schedule' in tbl.columns:
                    truth = truth & (tbl['schedule']==schedule)
            extracted[table] = tbl[truth]

        tou = TOU(subTOU,schedule,seasons=extracted['seasons'],periods=extracted['periods'],
                  daysoff=extracted['daysoff'],holidays=extracted['holidays'],dstadj=extracted['dstadj'])
        return tou

class TOU:
    def __init__(self,subTOU,schedule,**tables):
        self.subTOU = subTOU
        self.schedule = schedule
        self.tables = tables
    def __getattr__(self,attribute):
        return self.tables.get(attribute)

class EventsDB:
    def __init__(self,tables:xltable.RawXL,utility:org.IOU):
        self.utility = utility.org
        self.tables = tables
    def _refine():
        self.tables = self.tables
    def extract(table:str) -> pandas.DataFrame:
        return

class Events:
    def __init__(self,event_type:str,events:pandas.DataFrame):
        self.event_type = event_type
        self.events = events
    def add_historical_events(self,new_events:pandas.DataFrame):
        self.events = pandas.concat([self.events,new_events]).first()
    def extract(self,span:List[datetime.datetime]) -> pandas.DataFrame:
        max_time = self.events.index.max()
        max_needed = max(span)
        if max_needed > max_time:
            projected_events = _project(self,[max_time,max_needed])
    def _project(self,span:List[datetime.datetime]) -> pandas.DataFrame:
        # write rules for determining next periods
        return None

class PKPEvents(Events):
    def __init__(self,events:pandas.DataFrame):
        Events.__init__(self,'pkp',events)
    def _project(self,span:List[datetime.datetime]) -> pandas.DataFrame:
        # write rules for determining next periods
        return None

class InterruptEvents(Events):
    def __init__(self,events:pandas.DataFrame):
        Events.__init__(self,'interrupt',events)
    def _project(self,span:List[datetime.datetime]) -> pandas.DataFrame:
        # write rules for determining next periods
        return None