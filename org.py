'''Customers and companies'''
from typing import List
#from typing import Dict

class Entity:
    def __init__(self,name:str,org_type:str):
        self.name = name
        self.type = org_type
    def __repr__(self):
        return str(name)

class IOU(Entity):
    def __init__(self,name:str,nameplate_multiplier:float=1.0):
        Entity.__init__(self,name,'IOU')
        self.nameplate = nameplate_multiplier

class Provider(Entity):
    def __init__(self,name:str,dacca_type:str,utilites:List[IOU]):
        Entity.__init__(self,name,dacca_type)
        self.providing = dacca_type
        self.associated = utilites

class Direct(Provider):
    def __init__(self,name:str,utilities:List[IOU]):
        Provider.__init__(self,name,'da',utilites)

class CCA(Provider):
    def __init__(self,name:str,utilities:List[IOU],colors:dict):
        Provider.__init__(self,name,'cca',utilites)
        self.colors = colors

class Customer(Entity):
    def __init__(self,name:str,customer_type:str,zipcode:int):
        if customer_type.lower() in ['school','district','city']:
            self.category = customer_type.lower()
        else:
            self.category = None
        Entity.__init__(self,name,'customer')
        self.zipcode = zipcode
        self.portfolio = None

    def add_portfolio(self,portfolio:"physical.Portfolio"): #  maybe remove Class references
        self.portfolio = portfolio

class User:
    def __init__(self,username:str,permissions:List[str]=None):
        self.username = username
        self.permissions = permissions
        self.customers = {}

    def add_customer(self,customer:Customer):
        self.customers[customer.name] = customer

    def get_customer(self,customer_name:str):
        return self.customers[customer_name]