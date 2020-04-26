import json
import os
from botocore.vendored import requests

def lambda_handler(event, context):
    # TODO implement
    print("Event was:", event)
    print("context was", context)
    
    # doc_id = 1
    # file_name = "/tmp/dummy_data.json"
    
    # dummy_stuff = [ 
    #     {
    #     "objectKey": "cat-photo1.jpg",
    #     "bucket": "my-photo-bucket",
    #     "createdTimestamp": "2018-11-05T12:40:02",
    #     "labels": [
    #     	"cats"
    #     ]
    #     },
    #             {
    #     "objectKey": "cat-photo2.jpg",
    #     "bucket": "my-photo-bucket",
    #     "createdTimestamp": "2018-11-05T12:40:02",
    #     "labels": [
    #     	"cats"
    #     ]
    #     }
    # ]
    
    # with open(file_name, 'w') as outfile:

    #     # Load Data into Elastic Search
    #     doc_record = {"index": {"_index": "photos", "_type": "_doc", "_id": "%d"}}
    #     for record in dummy_stuff:
    #         this_doc_record = (json.dumps(doc_record) + "\n") % doc_id
    #         this_record = json.dumps(record) + "\n"

    #         outfile.write(this_doc_record)
    #         outfile.write(this_record)
    #         doc_id += 1

    # print("Done writing to file")
    # es_url = 'https://vpc-photo-index-6gtjhllhc3y47utn5shxhmfhu4.us-east-1.es.amazonaws.com/_bulk'
    # cmd = 'curl -XPOST %s --data-binary @%s -H "Content-Type: application/json"' % (es_url, file_name)
    # resp = os.system(cmd)
    # print("Done uploading to Elastic Search Index with res: ", resp)
    
    things = event['body']
    es_url = 'https://vpc-photo-index-6gtjhllhc3y47utn5shxhmfhu4.us-east-1.es.amazonaws.com/photos/_search'
    s3_url = 'https://ppkbphotos.s3.amazonaws.com/'
    
    photo_list = []
    url_list = []
    for thing in things:
        query = "{}?q=labels:*{}*".format( es_url, thing )
        print(query)
        res = requests.get(query).json()['hits']['hits']
        print(res)
        this_photo_list = [ a["_source"]["objectKey"] for a in res]
        photo_list = photo_list + this_photo_list
        url_list = url_list + [ s3_url + item for item in this_photo_list]
    
    
    photo_list = list(set(photo_list))
    url_list = list(set(url_list))
    return {
        'statusCode': 200,
        'body': url_list
    }
