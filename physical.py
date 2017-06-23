'''Physical objects'''
import pandas,datetime
from typing import List
import org,times

class Interval:
    '''Basic object with times and measurements'''
    def __init__(self,timestamps:pandas.DatetimeIndex,measurements:pandas.Series,direction:str='export',unit:str='kwh'):
        '''Initialize interval'''
        self.unit = unit

        self.data = pandas.DataFrame(data=measurements)
        self.data.columns = [unit]
        self.direction = direction
        self.timestamps = timestamps

        self.frequency = self.get_frequency()
    
    def __repr__(self):
        return str(self.data)

    def smooth_spikes(self):
        '''Spikes occur when a meter snoozes, which is evident when there are many zeroes.'''
        # block measurements
        blocking = self.data
        blocking['blocks'] = ((self.data[[self.unit]]==0).cumsum()-(self.data[[self.unit]]==0).cumsum().where(
            ~(self.data[[self.unit]]==0)).fillna(method='pad').fillna(0)).astype(int).shift().where(
                self.data[[self.unit]]!=0).fillna(method='bfill')
        # smooth out demand during snooze
        blocking['smoothed'] = self.data[[self.unit]].where(self.data[[self.unit]]!=0).fillna(method='bfill')
        # replace smoothed intervals when snooze period is longer than minimum span
        blocking['smoothed'] = (blocking['smoothed'].div(blocking['blocks'])).where(
            ((blocking['blocks']>=snooze_min)&((self.data[self.unit]==0)|(self.data[self.unit].shift()==0))),self.data[self.unit])
        blocking = blocking.drop(['blocks',self.unit],axis=1).rename(columns={'smoothed':self.unit})
        self.data = blocking

    def get_frequency(self):
        freq = pandas.Series(self.timestamps).diff().mode()
        return freq

    def convert_to_hourly(self):
        '''Change 60-min interval to 15-min interval'''
        # check that data is not 15-min already
        if self.frequency!='15min':
            daterange = pandas.date_range(self.timestamps.min(),self.timestamps.max(),freq='15min')
            df = pandas.DataFrame(self.data)
            df.index = self.timestamps
            converted = pandas.concat([df.reindex(daterange,method=m) for m in ['ffill','bfill']],axis=1).mean(1)
            self.data = pandas.DataFrame(converted[self.unit])
            self.timestamps = converted.index
            self.freq = self.get_frequency()

class Monitor:
    def __init__(self,name:str,interval:Interval=None):
        self.interval = interval
        self.name = name

    def __repr__(self):
        return str(self.interval)

    def add_historical_interval(self,interval:Interval):
        self.interval = interval

    def get_historical_interval(self) -> Interval:
        return self.interval

class Asset(Monitor):
    '''Physical object that has a function (solar, storage) and measurements resulting from power movement'''
    def __init__(self,name:str,asset_type:str,interval:Interval=None,interver_size:float=None):
        Monitor.__init__(self,name,interval)
        self.asset_type = asset_type
        self.interver_size = interver_size

class SolarArray(Asset):
    '''Solar asset'''
    def __init__(self,name:str,interval:Interval=None,inverter_size:float=None):
        Asset.__init__(self,name,'solar',interval)
    
    def add_base_projection(self,interval:Interval,base_size:float):
        self.projected = interval.div(base_size)
    def project_interval(self) -> Interval:
        return self.project_interval.mul(inverter_size)

class Setpoints:
    pass

class Battery(Asset):
    '''Battery asset'''
    def __init__(self,name:str,interval:Interval=None,interver_size:float=None,capacity:float=None):
        Asset.__init__(self,name,'battery',interval,interver_size)
        self.capacity = capacity

    def add_setpoints(self,setpoints:Setpoints):
        self.setpoints = setpoints
    def project_interval(self,net_interval) -> Interval: # need demand
        return None

class Facility(Monitor):
    '''Physical object that has a name and measurements resulting from customer usage'''
    def __init__(self,name:str,interval:Interval=None,amount:str='gross'):
        Monitor.__init__(self,name,interval)
        self.amount = amount

    def gross_up(self,assets:List[Asset]):
        '''Find the gross demand'''
        if self.amount!='gross':
            baseline = facility
            # if data is given in net, add back asset interval
            for asset in assets:
                baseline.interval.data += asset.interval.data
        self.interval = baseline.interval
        self.amount = 'gross'

class Portfolio:
    '''Collection of meters belonging to a customer, including those not in a scenario'''
    def __init__(self,customer:org.Customer,facilities:List[Facility]):
        self.customer = customer
        self.facilities = facilities


class Meter:
    '''Collection of facility and assets with an identifier'''
    def __init__(self,id:str,facility:Facility,assets:List[Asset]=None): # what about RES-BCT with no building drop
        self.id = id
        self.facility = facility
        if assets == None:
            self.assets = []
        else:
            self.assets = assets
        self.timestamps = self.facility.interval.timestamps
        self.index = facility.interval.data.index

    def __repr__(self):
        '''Show interval'''
        return str(self.interval)

    def add_assets(self,assets:List[Asset]):
        self.assets += assets

    def combine_intervals(self,solarnames:List[str],storagenames:List[str]) -> Interval:
        '''Subtract interval data from assets associated at stage to get net'''
        interval = self.facility.interval
        for asset in self.assets:
            # subtract meters in stage
            if ((asset.name in solarnames) & (asset.asset_type=='solar')) | \
                ((asset.name in storagenames) & (asset.asset_type=='storage')):
                interval.data -= asset.interval.data.mul(1 if asset.interval.direction=='export' else -1)
        return interval

class Interconnection:
    '''Combination of assets and facility at one meter'''
    def __init__(self,meter:Meter,solarnames:List[str]=[],storagenames:List[str]=[]):
        self.meter = meter
        self.interval = meter.combine_intervals(solarnames,storagenames)

        self.calendar = pandas.DataFrame()
        self.calendar['month'] = meter.timestamps.month
        self.calendar['date'] = meter.timestamps.date
        self.calendar['dayofweek'] = meter.timestamps.dayofweek
        self.calendar['time'] = meter.timestamps.time

        self.timesofuse = pandas.DataFrame(index=meter.index,columns=['season','period'])

    def classify_periods(self,tou:times.TOU,span:List[datetime.datetime]=None):
        '''Identify seasons and times of use'''
        span_index = self._get_span_index(self,span)
        interval = pandas.DataFrame(index = span_index)
        interval['holiday'] = 0

        # classify days on/off
        interval['dayoff'] = pandas.merge(self.calendar,tou.daysoff.weekdays,how='left',on=['dayofweek'])['dayoff']

        if TOU.daysoff.holidaysoff:
            interval['holiday'] = pandas.merge(self.calendar,tou.daysoff.holidays,how='left',on=['date'])['holiday']
            interval['dayoff'] = interval['holiday'] | interval['dayoff']
   
        # classify seasons
        interval['season'] = pandas.merge_asof(self.calendar,tou.seasons,
                                               left_on=['month'],right_on=['start'],
                                               how='left')['season']

        # classify TOUs
        interval['period'] = pandas.merge_asof(self.calendar,tou.periods,
                                               left_on=['season','dayoff','time'],right_on=['season','dayoff','start'],
                                               how='left')['period']

        # add to interval
        self.timesofuse.loc[span_index,:] = interval[['season','period']]

    def bucket_quantities(self,span:List[datetime.datetime]=None) -> dict:
        '''Bucket quantities over a timespan'''
        span_index = self._get_span_index(self,span)
        # stitch together dataframe
        interval = pandas.concat([self.data,self.calendar],axis=1)
        interval = interval[span_index,:]
        # group by time of use for energy and demand
        quantity_gb = interval.groupby(['season','period'])[[self.unit]]
        # calculate values
        quantity = {'days': interval['date'].nunique(),
                    'kw': quantity_gb.max().mul(self._multiplier(self.unit)['kw']).reset_index(),
                    'kwh': quantity_gb.sum().mul(self._multiplier(self.unit)['kwh']).reset_index(),
                    'nbc': interval[interval[self.unit]>0][self.unit].sum()}
        return quantity

    def _get_span_index(self,span:List[datetime.datetime]) -> pandas.Int64Index:
        '''Returns part of dataframe relevant to timespan'''
        if span is not None:
            span_index = self.data[(self.data.index>=span.min())&
                                   (self.data.index<=span.max())].index
        else:
            span_index = self.data.index
        return span_index

    def _multiplier(self,unit:str) -> int:
        m = {'kw': 4 if unit=='kwh' else 1,
             'kwh': 1 if unit=='kwh' else 1/4}
        return m

class Scenario:
    '''Group of various simultaneous interconnections of meters and assets'''
    def __init__(self,name:str,interconnections:List[Interconnection]):
        self.name = name
        self.interconnections = interconnections