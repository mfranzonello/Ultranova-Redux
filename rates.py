'''Charges and credits for all utility/provider rates'''
import pandas,datetime
import xltable,org,times
from typing import List

class RateTariff:
    '''Basic rules of a rate tariff'''
    def __init__(self,name:str,rate_class:str,tou:times.TOU,
                 default_option:str=None,protect_option:str=None,
                 min_kw:int=0,max_kw:int=None,max_kw_cum:int=0,max_kw_con:int=0,
                 charge_levels=None,timeofuse=True):
        self.name = name
        self.rate_class = rate_class
        self.tou = tou
        self.min_kw = min_kw
        self.max_kw = max_kw
        self.max_kw_cum = max_kw_cum
        self.max_kw_con = max_kw_con
        self.default_option = default_option
        self.protect_option = default_option
        self.charge_levels = charge_levels
        self.timeofuse = timeofuse
        self.close = None
        self.super = None
    def add_end_date(self,date:datetime.date):
        self.close = date
    def check_open(self,date:datetime.date=datetime.date.today()) -> bool:
        return self.close < date
    def add_superseding(self,rate:str):
        self.super = rate
    def get_superseding(self) -> str:
        return self.super

class TariffsDB:
    '''Collection of tariffs for a utility'''
    def __init__(self,utility:org.IOU):
        self.utility = utility
        self.rates = {}
    def add_tariff(self,rate_tariff:RateTariff):
        self.rates[rate_tariff.name] = rate_tariff

class ServiceAgreement:
    '''Combo of rate, option and other parameters'''
    def __init__(self,start:datetime.date,**parameters):
        self.start = start
        self._parameters = parameters
    def __getattr__(self,attribute):
        return self._parameters[attribute]

class RatesDB:
    '''Object that holds all rate tables for a utility'''
    def __init__(self,tables:xltable.RawXL,utility:org.IOU):
        self.utility = utility
        self.data = tables.data
        self._refine_utility()

    def _refine_utility(self):
        for tbl in self.data:
            df = self.data[tbl]
            if 'utility' in df.columns:
                self.data[tbl] = df[df['utility']==self.utility.name].drop('utility',axis=1)

class RateSchedule:
    '''All charges and credits for a set of parameters'''
    def __init__(self,category:str,dataframe:pandas.DataFrame,**parameters):
        self.category = category
        self.schedule = dataframe
        self._parameters = parameters

    def __getattr__(self,attribute):
        return self._parameters[attribute]

    def extract(self,effective:datetime.datetime) -> pandas.DataFrame: # by charge? by component?
        '''Returns a dataframe with charges for effective date'''
        return self.schedule[self.schedule['effective']==effective]

    def get_charge(self,service_agreement:ServiceAgreement,effective:datetime.datetime,unit:str,
                    season:str=None,period:str=None,components:List[str]=None,level:int=None,crs_type:str=None):
        '''Retuns sum of all charges that match parameters'''
        df = self.schedule
        # replace OAT with original tariff
        if (self.category!='utility') & ('OAT' in df['rate']):
            df = self._replace_oat(self,df,service_agreement)
        # replace nonbypassible from CRS with responsibility tariff
        if (self.category=='utility') & ('CRS' in df['rate']):
            df = self._replace_crs(self,df,service_agreement)
        # return slice of dataframe that matches parameters
        truth_value = self._get_truth(df,season,period,components,level,crs_type)
        charge = pandas.to_numeric(df[truth_value]).sum()
        return charge

    def _replace_oat(self,df:pandas.DataFrame,service_agreement:ServiceAgreement) -> pandas.DataFrame:
        merge_cols = ['unit','season','period','component','level']
        utility_df = utility_rates.extract(service_agreement)
        df.loc[df['rate']=='OAT','rate'] = \
            df.merge(utility_df,how='left',on=merge_cols,suffixes=['_',''])['rate']
        return df

    def _get_crs_type(self,service_agreement:ServiceAgreement) -> str:
        if service_agreement.provider is not None:
            crs_type = service_agreement.provider.providing
        elif (service_agreement.standby is not None) | force:
            crs_type = 'pcia'
        else:
            crs_type = None
        return crs_type

    def _replace_crs(self,df,service_agreement:ServiceAgreement) -> pandas.DataFrame:
        crs_type = self._get_crs_type(service_agreement)
        replace_all_nbc = False
        if service_agreement.provider is not None:
            replace_all_nbc = True
        elif service_agreement.standby is not None:
            replace_all_nbc = True
        merge_cols = ['unit','component']
        crs_df = crs_rates.extract(service_agreement)
        crs_df = crs_df[crs_df['type']==crs_type]
        df.loc[(df['rate']=='CRS')&(df['unit']=='nonbypass'),'rate'] = \
            df.merge(utility_df,how='left',on=merge_cols,suffixes=['_',''])['rate']
        return df

    def _get_truth(self,df,season:str,period:str,components:List[str],level:int,crs_type:str) -> pandas.Series:
        truth_value = df['unit']==unit
        if ('season' in df.columns) & (season is not None):
            truth_value = truth_value & ((df['season']==season) if not pandas.isnull(season) else df['season'].isnull())
        if ('period' in df.columns) & (period is not None):
            truth_value = truth_value & ((df['period']==period) if not pandas.isnull(period) else df['period'].isnull())
        if ('component' in df.columns) & (components is not None):
            truth_value = truth_value & (df['component'].isin(components))
        if ('level' in df.columns) & (level is not None):
            truth_value = truth_value & (df['level']==level)
        if ('crs type' in df.columns) & (crs_type is not None):
            truth_value = truth_value & (df['crs type']==crs_type)
        return truth_value

class Rates:
    '''Base class for charges and credits of a specific category'''
    def __init__(self,rates_db:RatesDB,table:str):
        self.utility = rates_db.utility
        self.table = self.data['{}rates'.format(table)]
        self._unpivot()

    def _unpivot(self):
        '''Unpivot table based on position of effective date'''
        df = self.table
        df_cols = df.columns.tolist()
        melt_list = df_cols[:df_cols.index('effective')+1]
        df_melted = df.melt(id_vars=melt_list,var_name='charge')
        df_melted = df_melted[(df_melted['value']!=0)&
                                (~df_melted['value'].isnull())]
        for col in clean_cols:
            df_melted[col] = df_melted['charge'].apply(something)
        self.table = df_melted

    def _clean(self,columns:List[str]):
        f_dict = {'unit':self._clean_unit,
                  'season':self._clean_season,
                  'period':self._clean_period,
                  'component':self._clean_component,
                  'level':self._clean_level,
                  'crs type':self._clean_crs}
        functions = [f_dict[c] for c in columns]
        self.table[columns] = self.table['charge'].apply(functions).drop('charge',axis=1)

    def _clean_unit(self,phrase:str) -> str:
        '''Determine base unit'''
        legend = {'customer':'fixed',
                  'kwh':'energy',
                  'kw':'demand',
                  'nbc':'nonbypass'}
        decoded = legend.get(phrase,phrase)
        return decoded

    def _clean_season(self,phrase:str) -> str:
        '''Determine season, if applicable'''
        legend = {'1':'summer',
                  '2':'winter',
                  '3':'spring',
                  '4':'fall'}
        if '-' in phrase:
            decoded = legend.get(phrase[phrase.index('-')-1],pandas.np.nan)
        else:
            decoded = pandas.np.nan
        return decoded

    def _clean_period(self,phrase:str) -> str:
        '''Determine TOU period, if applicable'''
        legend = {'1':'offpeak',
                  '2':'partpeak',
                  '3':'onpeak',
                  '4':'superoffpeak'}
        if '-' in phrase:
            decoded = legend.get(phrase[phrase.index('-')+1],pandas.np.nan)
        else:
            decoded = pandas.np.nan
        return decoded

    def _clean_component(self,phrase:str) -> str:
        '''Determine component, if applicable'''
        legend = {'d':'dist',
                  'u':'urg',
                  't':'bypass',
                  'cr':'credit',
                  'max':'maximum'}
        decoded = pandas.np.nan
        for unit in ['kwh','kw','nbc']:
            if unit in phrase:
                decoded = legend.get(phrase[phrase.index(unit)+len(unit)+1:],pandas.np.nan)
                break
        return decoded
    
    def _clean_level(self,phrase:str) -> str:
        '''Determine level, if applicable'''
        if 'customer' in phrase:
            decoded = int(phrase[-1])
        else:
            decoded = pandas.np.nan
        return decoded

    def _clean_crs(self,phrase:str) -> str:
        '''Strip crs type from component'''
        decoded = None
        return decoded

class UtilityRates(Rates):
    '''Unbundled IOU charges and credits'''
    def __init__(self,rates_db:RatesDB):
        Rates.__init__(self,rates_db,'utility')
        self._clean(['unit','season','period','component','level'])

    def extract(self,service_agreement:ServiceAgreement) -> RateSchedule:
        df = self.table[(self.table['subTOU']==service_agreement.subTOU)&
                        (self.table['rate']==service_agreement.rate.name)&
                        (self.table['option']==service_agreement.option)&
                        (self.table['connection']==service_agreement.connection)]
        return RateSchedule('utility',df,
                            service_agreement.subTOU,
                            service_agreement.rate.name,
                            service_agreement.option,
                            service_agreement.connection)

class StandbyRates(Rates):
    '''Unbundled standby charges and credits'''
    def __init__(self,rates_db:RatesDB):
        Rates.__init__(self,rates_db,'standby')
        self._clean(['unit','season','period','component','level'])

    def extract(self,service_agreement:ServiceAgreement) -> RateSchedule:
        rate_m = pandas.np.nan
        option_m = pandas.np.nan
        if service_agreement.rate.name in self.table['rate'].values:
            rate_m = service_agreement.rate.name
            if service_agreement.option in self.table[self.table['rate']==service_agreement.rate.name]['option'].values:
                option_m = service_agreement.option

        df = self.table[(self.table['subTOU']==service_agreement.subTOU)&
                        ((self.table['rate']==rate_m) if pandas.isnull(rate_m) else (self.table['rate'].isnull()))&
                        ((self.table['option']==option_m) if pandas.isnull(option_m) else (self.table['option'].isnull()))&
                        (self.table['connection']==service_agreement.connection)]
        return RateSchedule('standby',df,
                            service_agreement.subTOU,
                            service_agreement.rate.name,
                            service_agreement.option,
                            service_agreement.connection)

class CRSRates(Rates):
    '''Alternate generation source surcharges'''
    def __init__(self,rates_db:RatesDB):
        Rates.__init__(self,rates_db,'crs')
        self.clean(['unit','season','period','component','crs type']) # pcia, xxx da

    def extract(self,service_agreement:ServiceAgreement) -> RateSchedule: # no subTOU
        df = self.table[(self.table['group']==service_agreement.group)&
                        (self.table['vintage']==service_agreement.vintage)]
        return RateSchedule('crs',df,
                            group=service_agreement.group,
                            vintage=service_agreement.vintage)

class CCARates(Rates):
    '''Community choice aggregation charges'''
    def __init__(self,rates_db:RatesDB,provider:org.CCA):
        Rates.__init__(self,rates_db,'dacca')
        self.provider = provider
        self._refine_provider()
        self._clean(['unit','season','period','component'])

    def _refine_provider():
        self.table = self.table[self.table['provider']==self.provider.name].drop('provider',axis=1)

    def extract(self,service_agreement:ServiceAgreement) -> RateSchedule:
        df = self.table[(self.table['subTOU']==service_agreement.subTOU)&
                        (self.table['rate']==service_agreement.rate.name)&
                        (self.table['option']==service_agreement.option)&
                        (self.table['connection']==service_agreement.connection)]
        return RateSchedule('cca',df,
                            subTOU=service_agreement.subTOU,
                            rate=service_agreement.rate.name,
                            option=service_agreement.option,
                            connection=service_agreement.connection)

class PKPRates(Rates):
    '''Community choice aggregation charges'''
    def __init__(self,rates_db:RatesDB):
        Rates.__init__(self,rates_db,'pkp')
        self._clean(['unit','season','period','component'])

    def extract(self,service_agreement:ServiceAgreement) -> RateSchedule:
        df = self.table[(self.table['subTOU']==service_agreement.subTOU)&
                        (self.table['rate']==service_agreement.rate.name)&
                        (self.table['option']==service_agreement.option)&
                        (self.table['connection']==service_agreement.connection)]
        return RateSchedule('pkp',df,
                            subTOU=service_agreement.subTOU,
                            rate=service_agreement.rate.name,
                            option=service_agreement.option,
                            connection=service_agreement.connection)

class InterruptRates(Rates):
    '''Base interruptible rates'''
    def __init__(self,rates_db:RatesDB):
        Rates.__init__(self,rates_db,'interrupt')
        self._clean(['unit','season','period','component'])

    def extract(self,service_agreement:ServiceAgreement) -> RateSchedule:
        df = self.table[(self.table['subTOU']==service_agreement.subTOU)&
                        (self.table['incentive']==service_agreement.rate.name)&
                        (self.table['option']==service_agreement.interrupt_option)&
                        (self.table['connection']==service_agreement.connection)]
        return RateSchedule('interrupt',df,
                            subTOU=service_agreement.subTOU,
                            incentive=service_agreement.interrupt_incentive,
                            option=service_agreement.interrupt_option,
                            connection=service_agreement.connection)

class ShiftRates(Rates):
    '''Power shifting rates'''
    def __init__(self,rates_db:RatesDB):
        Rates.__init__(self,rates_db,'aps')
        self._clean(['unit'])

    def extract(self,service_agreement:ServiceAgreement) -> RateSchedule:
        df = self.table[(self.table['incentive']==service_agreement.shift_incentive)&
                        (self.table['option']==service_agreement.shift_option)&
                        (self.table['cycling']==service_agreement.cycling)]
        return RateSchedule('shift',df,
                            incentive=service_agreement.shift_incentive,
                            option=service_agreement.shift_option,
                            cycling=service_agreement.cycling)

class GroupsDB:
    '''Tables linking rates, options, standby and connections to S and CRS'''
    def __init__(self,groupings:xltable.RawXL,utility:org.IOU):
        self.groupings = groupings
        self.refine()

    def refine(self):
        self.groupings = None

class Groups:
    '''Grouping of rates'''
    def __init__(self,groups_db:GroupsDB):
        self.groupings = groups_db
        self.table = None
    def refine(self,table):
        self.table = self.groupings[table]

class StandbyGroups(Groups):
    '''Grouping of rates for standby'''
    def __init__(self,groups_db:GroupsDB):
        Groups.__init__(self,groups_db)
        self.refine('standby')
    def extract(self,service_agreement:ServiceAgreement) -> str:
        # match if rate, rate + option, conn appears
        return #self.table[rate]

class CRSGroups:
    '''Grouping of rates for CRS'''
    def __init__(self,groups_db:GroupsDB):
        Groups.__init__(self,groups_db)
        self.refine('crs')
    def extract(self,service_agreement:ServiceAgreement) -> str:
        # match if S, conn or rate appears
        return #self.table[rate]

#class CCAColorsDB:
#    '''Color options for CCA'''
#    def __init__(self,tables=xltable.RawXL,provider=org.CCA):
#        self.tables = tables

class CCAColors:
    '''Color options for CCA'''
    def __init__(self,tables=xltable.RawXL,provider=org.CCA):
        self.tables = tables

class DemandResponse:
    '''Links of rates to DR programs'''
    def __init__(self,utility:org.IOU,responses:List[str]):
        self.utility = utility
        self.responses = responses
        self.mutual_exclusions = []
        self.allowed = {}
        self.minimum_kw = {}

    def add_mutual_exclusion(self,response1:str,response2:str):
        self.mutual_exclusions += [(response1,response2)]
    
    def mutually_excluded(self,response1:str,response2:str):
        excluded = ((response1,response2) in self.mutual_exclusions) or \
            ((response2,response1) in self.mutual_exclusions)
    
    def add_allowed(self,response:str,rate:RateTariff):
        self.allowed
    
    def check_allowed(self,response:str,rate:RateTariff) -> bool:
        allowed = False
        free = self.allowed.get(response,True)
        if free:
            allowed = True
        elif not free==False:
            allowed = free.get(rate,False)
        return allowed

    def add_minimum(self,response:str,min_kw:float):
        self.minimum_kw[response] = min_kw
    
    def check_minimum(self,response:str) -> bool:
        return self.minimum_kw.get(response)