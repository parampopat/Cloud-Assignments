import boto3
import json
import requests


def dynamo_elastic_sync():
    """
    We read Dynamo DB in batches of 1 MB restarting at last read key and loading
    this data batch by batch into elastic search
    Reference - # https://aws.amazon.com/blogs/compute/indexing-amazon-dynamodb-content-with-amazon-elasticsearch-service-using-aws-lambda/
    :return:
    """

    # Init Clients
    dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
    elastic = boto3.client('es', region_name="us-east-1")
    table = dynamodb.Table('yelp-restaurants')
    subset_keys = ['id', 'cuisine']
    file_name = 'yelp_data_v2.json'

    response = None
    # Read the data
    doc_id = 1
    with open(file_name, 'a') as outfile:
        while True:
            if not response:
                # Scan from the start.
                response = table.scan()
            else:
                # Scan from where you stopped previously.
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])

            # Load Data into Elastic Search
            doc_record = {"create": {"_index": "Restaurants", "_type": "_doc", "_id": "%d"}}
            for record in response["Items"]:
                subset_data = {k: record[k] for k in subset_keys}
                this_doc_record = (json.dumps(doc_record) + "\n") % doc_id
                this_record = json.dumps(subset_data) + "\n"

                outfile.write(this_doc_record)
                outfile.write(this_record)
                doc_id += 1

            if 'LastEvaluatedKey' not in response:
                break

    print("Done writing to file")
    # Bulk Load it to elastic index
    # curl -XPOST elasticsearch_domain_endpoint/_bulk --data-binary @bulk_movies.json -H 'Content-Type: application/json'

    #### DOES NOT WORK YET ##########
    es_url = 'https://search-restaurants-eiskklpby24f4jvruokmxlbwba.us-east-1.es.amazonaws.com/_bulk'
    files = {'file': (file_name, open(file_name, 'rb'), 'application/json')}
    requests.post(es_url, files=files)

    print("Done uploading to Elastic Search Index")


if __name__ == '__main__':
    dynamo_elastic_sync()
