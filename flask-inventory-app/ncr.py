import requests
import urllib
import datetime
import base64
import hmac
import hashlib
import json

SHARED = '63f4fc90aed9413d804f5db9ce93dd41'
SECRET = '0bcc54040c394945815ffd675f9ab7ae'

MENU_ID = '10428520067787896001'

def createHMAC(req):
    print(urllib.parse.urlsplit(req.url).path)
    toSign = req.method + "\n" + urllib.parse.urlsplit(req.url).path

    hmac_headers = [
        'content-type',
        'content-md5',
        'nep-application-key',
        'nep-correlation-id',
        'nep-organization',
        'nep-service-version',
    ]

    for header in req.headers.keys():
        if header in hmac_headers:
            toSign += '\n' + req.headers[header]

    key = bytes(SECRET + datetime.datetime.strptime(
        req.headers['date'], "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%dT%H:%M:%S.000Z"), 'utf-8')
    
    message = bytes(toSign, 'utf-8')

    digest = hmac.new(key, msg=bytes(message),
                      digestmod=hashlib.sha512).digest()
    signature = base64.b64encode(digest)
    return "AccessKey {}:{}".format(SHARED, signature.decode('ascii'))


class NCRRequester():
    def __init__(self, shared=SHARED, secret=SECRET):
        self.sess = requests.Session()
        self.baseURL = 'https://gateway-staging.ncrcloud.com{}'
        self.site_id = 'de0ebf8075484018af65c4eb6e9c462d'

    def make_headers(self, headers):
        headers['date'] = datetime.datetime.now(
            datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %Z")
        headers['accept'] = 'application/json'
        headers['content-type'] = 'application/json'
        headers['nep-organization'] = '992ac8ce56fa4e30b3eb3367dc2c3693'
        headers['nep-enterprise-unit'] = 'de0ebf8075484018af65c4eb6e9c462d'
        return headers

    def send(self, req):
        preparedRequest = req.prepare()
        preparedRequest.headers['Authorization'] = createHMAC(preparedRequest)
        return self.sess.send(preparedRequest)

    def get(self, endpoint, headers={}):
        headers = self.make_headers(headers)
        request = requests.Request('GET', endpoint, headers=headers)
        return self.send(request)

    def post(self, endpoint, body, headers={}):
        headers = self.make_headers(headers)
        request = requests.Request(
            'POST', endpoint, headers=headers, data=json.dumps(body))
        return self.send(request)

    def put(self, endpoint, body, headers={}):
        headers = self.make_headers(headers)
        request = requests.Request(
            'PUT', endpoint, headers=headers, data=json.dumps(body))
        return self.send(request)

    def getIngredientNames(self):
        items = self.get('https://gateway-staging.ncrcloud.com/catalog/items').json()['pageContent']
        names = set()
        for item in items:
            if item['merchandiseCategory']['nodeId'] == 'ingredient':
                names.add(item['itemId']['itemCode'])
        return names 
    
    def getIngredientData(self, name):
        item = self.get(f'https://gateway-staging.ncrcloud.com/catalog/items/{name}').json()
        return {
            'version' : int(item['version']), 
            'count' : int(item['dynamicAttributes'][0]['attributes'][0]['value']), 
            'date' : item['auditTrail']['lastUpdated']
        }

    def getIngredients(self):
        names = self.getIngredientNames()
        data = {}
        for name in names:
            data[name] = self.getIngredientData(name)
        return data

    def putIngredient(self, name, count):
        data = {
            "version": 1 if name not in self.getIngredientNames() else self.getIngredientData(name)['version']+1,
            "shortDescription": {
                "values": [
                    {
                        "locale": "en-us",
                        "value": name
                    }
                ]
            },
            "departmentId": "TheDepartmentId",
            "merchandiseCategory": {
                "nodeId": "ingredient"
            },
            "nonMerchandise": "true",
            "dynamicAttributes": [
                {
                    "type": "ab1",
                    "attributes": [
                        {
                            "key": "count",
                            "value": count, 
                        }
                    ]
                }
            ]
        }
        return self.put(f'https://gateway-staging.ncrcloud.com/catalog/items/{name}', body=data)

    def getOrders(self):
        res = self.post(
            'https://gateway-staging.ncrcloud.com/order/3/orders/1/find', body={}).json()
        return [order['comments'].replace("'", '"') for order in res['pageContent'] if 'status' in order and 'name' in order['comments'] and order['status'] != 'Validated']
    
    def putOrders(self):
        order = {
            "name" : "avocado bowl", 
            "quantity": 3, 
        }

        body = {
            'comments': json.dumps(order), 
            'orderStatus': 'OrderPlaced'
        }

        res = self.post('https://gateway-staging.ncrcloud.com/order/3/orders/1', body=body)
        return res

    def putMenu(self): 
        menu = {
            'salmon bowl': {
                'price': 24.00, 
                'ingredients': {
                    'salmon': 2,
                    'spinach': 2, 
                    'rice': 10, 
                }
            }, 
            'spring bowl': {
                'price': 22.10, 
                'ingredients': {
                    'tomato': 2,
                    'chicken': 4, 
                }
            }, 
            'avocado bowl': {
                'price': 26.10, 
                'ingredients': {
                    'avocado': 2,
                    'potato': 3,
                }
            },
            'berry bowl': {
                'price': 24.10, 
                'ingredients': {
                    'blueberries': 2,
                    'strawberries': 3, 
                }
            }
        }
        
        body = {
            "status": "Validated", 
            "comments": json.dumps(menu) 
        }

        res = self.put(f'https://gateway-staging.ncrcloud.com/order/3/orders/1/{MENU_ID}', body=body).json()
        return res

    def getMenu(self):
        res = json.loads(self.get(f'https://gateway-staging.ncrcloud.com/order/3/orders/1/{MENU_ID}').json()['comments'])
        return res


if __name__ == '__main__': 
    ncr = NCRRequester()
