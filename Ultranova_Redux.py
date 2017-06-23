'''Physics and finance engine'''
import pandas
import physical,times,xltable,org,references,rates,retrieval

def setup_references(**refreshes) -> xltable.RawXL:
    '''Extract times of use, translations library and rates database.
    Pull from pickle file unless forced refresh or file DNE.'''
    refs = {'tou':references.times_and_seasons,
            'translations':references.translations,
            'rates':references.rates}
    raw = {}
    for ref in refs:
        vs = retrieval.VariableSet(ref)
        if refreshes.get(ref) or not vs.exists():
            raw[ref] = xltable.RawXL(refs[ref])
            vs.add(ref,raw[ref])
            vs.save()
        else:
            vs.load()
            raw[ref] = vs[ref]

    return raw['tou'],raw['translations'],raw['rates']

def run_main():
    print('Setting up references')
    tou_raw,translations_raw,rates_raw = setup_references()

    print('Setting up project')
    project_utility = org.IOU('SCE')
    start_subTOU = 'I'
    meter_schedule = '' # tie to meter later
    
    project_customer = org.Customer('Union-Endicott','school',13760)

    print('Assigning TOU')
    tou_db = times.TOUdb(tou_raw,project_utility)
    
    print('Creating facilities')
    interval_1 = physical.Interval(pandas.date_range('1/1/17',periods=200,freq='15min'),pandas.DataFrame([0]*200),'export','kwh')
    facility_1 = physical.Facility('George H Nichols',interval_1,amount='net')
    print('Consolidating portfolio')
    portfolio = physical.Portfolio(project_customer,[facility_1])

    print('Creating baseline scenario')
    meter_1 = physical.Meter(000,facility_1)
    intercon_1 = physical.Interconnection(meter_1)
    scenario_1 = physical.Scenario('baseline',[intercon_1])

    print('Creating solar assets')
    interval_2 = physical.Interval(pandas.date_range('1/1/17',periods=250,freq='15min'),pandas.DataFrame([0]*250),'import','kwh')
    asset_1 = physical.SolarArray('ground',interval_2)
    
    print('Creating solar stage')
    meter_1.add_assets([asset_1])
    intercon_2  = physical.Interconnection(meter_1,['ground'])
    scenario_2 = physical.Scenario('solar',[intercon_2])

run_main()