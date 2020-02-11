"""
__author__ = "Param Popat"
__version__ = "1.0"
__git__ = "https://github.com/parampopat/"
"""
import requests
import boto3
import time


def get_data(term, location, limit=50, offset=0):
    URL = "https://api.yelp.com/v3/businesses/search"
    api_key = 'YUw0TfMSp0qlExEg-rn93f5AJTXSTO8g2WU6moogqXX1IUXBlNu-70G1VovWXTRA7j8K3CXBVh2VBapKzu-NyoIOtHu5HkyLuDf7Wjt3eJXUITn1bYUBmPHo6PI9XnYx'
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
                businesses[iter]['insertedAtTimestamp'] = str(time.time())
                bus.append(businesses[iter])
        except:
            continue
    print("Final Tally for ", keyword, " is ", len(bus))
    return bus


if __name__ == '__main__':
    max_offset = 1000
    # cuisines = ["chinese", "italian", "indian"]
    cuisines = ["japanese", "thai", "mexican"]
    location = 'Manhattan'
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('yelp-restaurants')
    for cuisine in cuisines:
        businesses = scrap_yelp(max_offset=max_offset, cuisine=cuisine, location=location)
        with table.batch_writer(overwrite_by_pkeys=['insertedAtTimestamp']) as batch:
            for item in businesses:
                for key in item.keys():
                    item[key] = ' ' if item[key] == '' else str(item[key])
                try:
                    batch.put_item(Item=item)
                except:
                    continue
