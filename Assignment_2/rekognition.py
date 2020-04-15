"""
__author__ = "Param Popat"
__version__ = "1.0"
__git__ = "https://github.com/parampopat/"
__reference__ = "https://boto3.amazonaws.com/v1/documentation/api/latest/index.html"
"""

import boto3
import time


def create_collection(collection_id):
    """
    :source: https://docs.aws.amazon.com/rekognition/latest/dg/create-collection-procedure.html
    :param collection_id:
    :return:
    """
    client = boto3.client('rekognition')
    print('Creating collection:' + collection_id)
    response = client.create_collection(CollectionId=collection_id)
    print('Collection ARN: ' + response['CollectionArn'])
    print('Status code: ' + str(response['StatusCode']))
    print('Done...')


def add_faces_to_collection(bucket, photo, collection_id):
    """
    :source: https://docs.aws.amazon.com/rekognition/latest/dg/add-faces-to-collection-procedure.html
    :param bucket:
    :param photo:
    :param collection_id:
    :param access_key:
    :param secret_key:
    :return:
    """
    client = boto3.client('rekognition')
    response = client.index_faces(CollectionId=collection_id,
                                  Image={'S3Object': {'Bucket': bucket, 'Name': photo}},
                                  ExternalImageId=photo,
                                  MaxFaces=1,
                                  QualityFilter="AUTO",
                                  DetectionAttributes=['ALL'])
    print('Results for ' + photo)
    print('Faces indexed:')
    print(response)
    for faceRecord in response['FaceRecords']:
        print('  Face ID: ' + faceRecord['Face']['FaceId'])
        print('  Location: {}'.format(faceRecord['Face']['BoundingBox']))

    print('Faces not indexed:')
    for unindexedFace in response['UnindexedFaces']:
        print(' Location: {}'.format(unindexedFace['FaceDetail']['BoundingBox']))
        print(' Reasons:')
        for reason in unindexedFace['Reasons']:
            print('   ' + reason)

    return len(response['FaceRecords'])


def create_stream(kvs, kds, user, collection_id, stream_name):
    """

    :param kvs:
    :param kds:
    :param user:
    :param collection_id:
    :param stream_name:
    :return:
    """
    client = boto3.client('rekognition')
    print('Creating Stream Processor:' + stream_name)
    response = client.create_stream_processor(Input={'KinesisVideoStream': {'Arn': kvs}},
                                              Output={'KinesisDataStream': {'Arn': kds}},
                                              Name=stream_name,
                                              Settings={
                                                  'FaceSearch': {
                                                      'CollectionId': collection_id,
                                                      'FaceMatchThreshold': 85.5
                                                  }
                                              },
                                              RoleArn=user)
    print(response)
    return response


def start_stream(stream_name):
    """

    :param stream_name:
    :return:
    """
    client = boto3.client('rekognition')
    print('Starting Stream Processor:' + stream_name)
    response = client.start_stream_processor(
        Name=stream_name
    )
    print(response)


def stop_stream(stream_name):
    """

    :param stream_name:
    :return:
    """
    client = boto3.client('rekognition')
    print('Stopping Stream Processor:' + stream_name)
    response = client.stop_stream_processor(
        Name=stream_name
    )
    print(response)


def main(set_collection=False, add=False, generate_stream=False, stream=False, stop=False):
    """

    :param stop:
    :param set_collection:
    :param add:
    :param generate_stream:
    :param stream:
    :return:
    """
    collection_id = 'Collection'
    bucket_id = 'ppkbvisitorvault'
    photo_id = 'param.jpg'
    user_arn = 'arn:aws:iam::041132386971:role/rekognitionrole'
    kvs_arn = 'arn:aws:kinesisvideo:us-east-1:041132386971:stream/kbppstream/1586054873891'
    kds_arn = 'arn:aws:kinesis:us-east-1:041132386971:stream/AmazonRekognition_kbpp'
    stream_name = 'streamProcessorForCam'

    if set_collection:
        try:
            create_collection(collection_id)
        except Exception as e:
            print("Couldn't Create", e)
    if add:
        try:
            records = add_faces_to_collection(bucket=bucket_id, photo=photo_id, collection_id=collection_id)
            print(records, 'Faces Indexed')
        except Exception as e:
            print("Couldn't Add", e)
    if generate_stream:
        try:
            stream = create_stream(kvs=kvs_arn, kds=kds_arn, user=user_arn, collection_id=collection_id,
                                   stream_name=stream_name)
        except Exception as e:
            print("Couldn't Create Stream", e)
    if stream:
        try:
            start_stream(stream_name=stream_name)
        except Exception as e:
            print("Couldn't Start Stream", e)
    if stop:
        try:
            stop_stream(stream_name=stream_name)
        except Exception as e:
            print("Couldn't Stop Stream", e)


if __name__ == "__main__":
    main(stream=True)

    # hls_stream_ARN = 'arn:aws:kinesisvideo:us-east-1:041132386971:stream/kbppstream/1586054873891'
    #
    # STREAM_NAME = "kbppstream"
    # kvs = boto3.client("kinesisvideo")
    #
    # # Grab the endpoint from GetDataEndpoint
    # endpoint = kvs.get_data_endpoint(
    #     APIName="GET_HLS_STREAMING_SESSION_URL",
    #     StreamARN=hls_stream_ARN)['DataEndpoint']
    #
    # # Grab the HLS Stream URL from the endpoint
    # kvam = boto3.client("kinesis-video-archived-media", endpoint_url=endpoint)
    # url = kvam.get_hls_streaming_session_url(
    #     StreamName=STREAM_NAME,
    #     PlaybackMode="LIVE")['HLSStreamingSessionURL']
    # kvs = boto3.client("kinesisvideo")
    #
    # # Now try getting video chunks using GetMedia
    #
    # response = kvs.get_data_endpoint(
    #     StreamARN=hls_stream_ARN,
    #     APIName='GET_MEDIA'
    # )
    # endpoint_url_string = response['DataEndpoint']
    #
    # streaming_client = boto3.client(
    #     'kinesis-video-media',
    #     endpoint_url=endpoint_url_string,
    #     # region_name='us-east-1'
    # )
    #
    # kinesis_stream = streaming_client.get_media(
    #     StreamARN=hls_stream_ARN,
    #     StartSelector={'StartSelectorType': 'EARLIEST'}
    #     # StartSelector={'StartSelectorType': 'NOW'}
    #
    # )
    #
    # stream_payload = kinesis_stream['Payload']
    #
    # print("Received stream payload.")

    # f = open("fragments_2.mkv", 'w+b')
    # f.write(stream_payload.read())
    # f.close()
    # print("Saved to a file.")

    # client = boto3.client('kinesis-video-media')
    # response = client.get_media(
    #     StreamName='kbppstream',
    #     StreamARN='arn:aws:kinesisvideo:us-east-1:041132386971:stream/kbppstream/1586054873891',
    #     StartSelector={
    #         'StartSelectorType': 'NOW',
    #     }
    # )
    #
    # stream = response['Payload']  # botocore.response.StreamingBody object
    # chunk = stream.read(1024)
    # while chunk is not None:
    #     chunk = stream.read(1024)

    # bucket = 'ppkbvisitorvault'
    # fileName = 'vap.jpg'
    # threshold = 70
    # client = boto3.client('rekognition')
    # response = client.search_faces_by_image(CollectionId='Collection',
    #                                         Image={'S3Object': {'Bucket': 'ppkbvisitorvault', 'Name': fileName}},
    #                                         FaceMatchThreshold=threshold,
    #                                         MaxFaces=1)
    #
    # faceMatches = response['FaceMatches']
    # if len(faceMatches) > 0:
    #     faceId = faceMatches[0]['Face']['FaceId']
    #     print('faceid', faceId)
    #
    # bucket = 'ppkbvisitorvault'
    # fileName = 'DSC04796.JPG'
    # response = client.index_faces(CollectionId='Collection',
    #                               Image={'S3Object': {'Bucket': bucket, 'Name': fileName}},
    #                               ExternalImageId=fileName,
    #                               MaxFaces=1,
    #                               QualityFilter="AUTO",
    #                               DetectionAttributes=['ALL'])
    # for faceRecord in response['FaceRecords']:
    #     print('  Face ID: ' + faceRecord['Face']['FaceId'])
