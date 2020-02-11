"""
__author__ = "Param Popat"
__version__ = "1.1"
__git__ = "https://github.com/parampopat/"
"""
import requests
import boto3
import time


def get_data(term, location, limit=50, offset=0):
    URL = "https://api.yelp.com/v3/businesses/search"
    api_key = 'api-key'
    headers = {
        'Authorization': 'Bearer %s' % api_key,
    }
    url_params = {
        'term': term.replace(' ', '+'),
        'location': location.replace(' ', '+'),
        'limit': limit,
        'offset': offset
    }
    r = requests.get(url=URL, headers=headers, params=url_params)
    return r.json()


def get_business(response):
    businesses = response.get('businesses')
    if not businesses:
        return None
    else:
        return businesses


def scrap_yelp(max_offset, cuisine, location):
    keyword = cuisine + ' restaurants'
    bus = []
    for i in range(0, max_offset, 50):
        try:
            data = get_data(keyword, location, offset=i)
            businesses = get_business(data)
            for iter in range(len(businesses)):
                businesses[iter]['cuisine'] = cuisine
                item = {key: businesses[iter][key] for key in
                        businesses[iter].keys() & {'id', 'name', 'cuisine', 'rating', 'review_count', 'coordinates',
                                                   'location'}}
                for key in item.keys():
                    item[key] = ' ' if item[key] == '' else str(item[key])
                bus.append(item)
        except:
            continue
    print("Final Tally for ", keyword, " is ", len(bus))
    return bus


if __name__ == '__main__':
    max_offset = 1000
    cuisines = ["chinese", "italian", "indian", "japanese", "thai", "mexican"]
    location = 'Manhattan'
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('yelp-restaurants')

    iterator = 0
    for cuisine in cuisines:
        businesses = scrap_yelp(max_offset=max_offset, cuisine=cuisine, location=location)
        with table.batch_writer() as batch:
            for item in businesses:
                item['insertedAtTimestamp'] = str(iterator)
                batch.put_item(Item=item)
                iterator += 1
