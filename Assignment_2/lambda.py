import boto3
from boto3.dynamodb.conditions import Key
from random import sample
import importlib
import sys
import json
import time
import base64


MODULE_PATH = "/opt/numpy/__init__.py"
MODULE_NAME = "numpy"

spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
numpy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = numpy 
spec.loader.exec_module(numpy)

MODULE_PATH = "/opt/cv2/__init__.py"
MODULE_NAME = "cv2"

spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
cv2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cv2 
spec.loader.exec_module(cv2)


VIRTUAL_DOOR_URL = "http://virtualdoorotp.s3-website-us-east-1.amazonaws.com"
GRANT_PAGE_BASE = "http://virtualdoorgrant.s3-website-us-east-1.amazonaws.com"


class Authenticator:
    def __init__(self):
        # Clients
        self.client_ddb = boto3.resource('dynamodb', region_name="us-east-2")
        self.table_passcodes = self.client_ddb.Table('passcodes')
        self.table_visitors = self.client_ddb.Table('visitors')
        self.client_sns = boto3.client('sns')
        self.client_email = boto3.client('ses')
        self.client_rek=boto3.client('rekognition')
        self.s3_client = boto3.client('s3')

        # Attributes populated later.
        self.face_id = None
        self.visitor_phone = None
        self.visitor_name = None
        self.owner_email = "saykartik@gmail.com"
        self.visitor_image_link = "https://upload.wikimedia.org/wikipedia/en/e/ed/Nyan_cat_250px_frame.PNG"
        self.collectionId='Collection'
        self.is_face_match = None

        self.otp = None
        self.kinesis_face = None

    def get_face_id(self, bucket=None, fileName=None):
        # self.face_id = "kbhy6534"  # Data from Stream passed into this function
        bucket='ppkbvisitorvault'
        fileName='frame1.jpg'
        threshold = 70
        response=self.client_rek.search_faces_by_image(CollectionId=self.collectionId,
                                Image={'S3Object':{'Bucket':bucket,'Name':fileName}},
                                FaceMatchThreshold=threshold,
                                MaxFaces=1)

                                
        faceMatches=response['FaceMatches']
        if len(faceMatches) > 0:
            self.face_id = faceMatches[0]['Face']['FaceId']
            print(self.face_id)
        else:
            self.face_id = self.gen_face_id(bucket=bucket, fileName=fileName)
            print(self.face_id)
        
    
    def gen_face_id(self, bucket=None, fileName=None):
        bucket='ppkbvisitorvault'
        response = self.client_rek.index_faces(CollectionId=self.collectionId,
                                  Image={'S3Object': {'Bucket': bucket, 'Name': fileName}},
                                  ExternalImageId=fileName,
                                  MaxFaces=1,
                                  QualityFilter="AUTO",
                                  DetectionAttributes=['ALL'])
        for faceRecord in response['FaceRecords']:
            # print(faceRecord['Face']['FaceId'])
            return faceRecord['Face']['FaceId']
        
        
    def save_image(self):
        # make sure to use the right ARN here:
        hls_stream_ARN = "arn:aws:kinesisvideo:us-west-2:420343293343:stream/MyStream/1563421665582"
        
        STREAM_NAME = "MyStream"
        kvs = boto3.client("kinesisvideo")

        # Grab the endpoint from GetDataEndpoint
        endpoint = kvs.get_data_endpoint(
            APIName="GET_HLS_STREAMING_SESSION_URL",
            StreamARN=hls_stream_ARN)['DataEndpoint']
            
        # Grab the HLS Stream URL from the endpoint
        kvam = boto3.client("kinesis-video-archived-media", endpoint_url=endpoint)
        url = kvam.get_hls_streaming_session_url(
            StreamName=STREAM_NAME,
            PlaybackMode="LIVE")['HLSStreamingSessionURL']
        kvs = boto3.client("kinesisvideo")

        # Now try getting video chunks using GetMedia
        
        response = kvs.get_data_endpoint(
            StreamARN=hls_stream_ARN,
            APIName='GET_MEDIA'
        )
        endpoint_url_string = response['DataEndpoint']
        
        streaming_client = boto3.client(
        	'kinesis-video-media', 
        	endpoint_url=endpoint_url_string, 
        	#region_name='us-east-1'
        )
        
        kinesis_stream = streaming_client.get_media(
        	StreamARN=hls_stream_ARN,
        # 	StartSelector={'StartSelectorType': 'EARLIEST'}
        	StartSelector={'StartSelectorType': 'NOW'}
        
        )
        
        stream_payload = kinesis_stream['Payload']

        f = open("fragments.mkv", 'w+b')
        f.write(stream_payload.read())
        f.close() 
        print("Saved to a file.")
        
        
        vidcap = cv2.VideoCapture('fragments.mkv')
        success,image = vidcap.read()
        cv2.imwrite("iframe.jpg", image)
        
        response = self.s3_client.upload_file('iframe0.jpg', 'ppkbvisitorvault', 'iframe0.jpg')
        
        vidcap.release()
        # TODO
        
        
    def save_image_v2(self): 
        kvs_client = boto3.client('kinesisvideo', region_name='us-east-1')
        kvs_data_pt = kvs_client.get_data_endpoint(
            StreamARN="arn:aws:kinesisvideo:us-east-1:041132386971:stream/kbppstream/1586054873891", # kinesis stream arn
            APIName='GET_MEDIA')

        print(kvs_data_pt)

        end_pt = kvs_data_pt['DataEndpoint']
        kvs_video_client = boto3.client('kinesis-video-media', endpoint_url=end_pt, region_name='us-east-1') # provide your region
        kvs_stream = kvs_video_client.get_media(
            StreamARN="arn:aws:kinesisvideo:us-east-1:041132386971:stream/kbppstream/1586054873891", # kinesis stream arn
            StartSelector={'StartSelectorType': 'NOW'} # to keep getting latest available chunk on the stream
        )
        print(kvs_stream)

        # with open('/tmp/stream.mkv', 'wb') as f:
        f = open('/tmp/stream.mkv', 'wb')
        streamBody = kvs_stream['Payload'].read(1024*16384) # reads min(16MB of payload, payload size) - can tweak this
        f.write(streamBody)
        f.close()
        
        # s3_client = boto3.client('s3', region_name='us-east-1')
        # s3_client.upload_file(
        #       '/tmp/stream.mkv',
        #       'ppkbvisitorvault', # replace with your bucket name
        #       'stream1.mkv'
        # )
        
        # use openCV to get a frame
        cap = cv2.VideoCapture('/tmp/stream.mkv')

        # use some logic to ensure the frame being read has the person, something like bounding box or median'th frame of the video etc
        ret, frame = cap.read() 
        cv2.imwrite('/tmp/frame.jpg', frame)
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.upload_file(
              '/tmp/frame.jpg',
              'ppkbvisitorvault', # replace with your bucket name
              'frame1.jpg'
        )
        cap.release()
        print('Image uploaded')
        
        
        
    def match_face(self):
        response = self.table_visitors.query(
            IndexName='faceId-index',
            KeyConditionExpression=Key('faceId').eq(self.face_id),
        )

        if len(response['Items']) > 0:
            # TODO: get path to S3 object and replace here
            # Check for Email ID or Phone Number as well 
            details = response['Items'][0]
            if len(details['phoneNumber']) > 0:
                self.visitor_phone = details['phoneNumber']
                self.visitor_name = details['name']
                # self.visitor_image_link = "{}/{}".format( "path/to/s3", details['objectKey'])
                self.is_face_match = True
            else:
                self.is_face_match = False
        else:
            self.is_face_match = False

    def store_otp(self):
        # write otp to DynamoDB
        if self.otp is None:
            raise ValueError("otp must be set in the object before invoking this")

        # TODO: Should we make sure there is only one active OTP by flushing previous ?
        with self.table_passcodes.batch_writer() as batch:
            # TODO: visitorid might change - keep track
            exp_time = int(time.time()) + 5 * 60  # Expiry in 5 mins
            item = {'code': self.otp, 'visitorid': self.face_id, 'ttl': exp_time}
            batch.put_item(Item=item)

    def send_key_or_request(self):
        if self.is_face_match:
            self.generate_otp()
            self.store_otp()

            msg = (
                    'Hello {}! Your OTP to open the virtual door is {}.' +
                    'Expiry in 5 min' +
                    'Click link to enter virtual door.{}'
            ).format(self.visitor_name, self.otp, VIRTUAL_DOOR_URL)

            self.client_sns.publish(PhoneNumber=self.visitor_phone, Message=msg)
        else:
            grant_page_url = "{}?face_id={}".format(GRANT_PAGE_BASE, self.face_id)
            html = (
                """
                A new visitor has requested access to your apartment.
                Grant Access by clicking <a href="{}">here</a><br>
                <img src="{}" alt="headshot">
                """.format(grant_page_url, self.visitor_image_link)
            )
            self.client_email.send_email(
                Source="saykartik@gmail.com",
                Destination={'ToAddresses': [self.owner_email]},
                Message={
                    'Subject': {
                        'Data': 'Door Access Request',
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': html,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )

    def generate_otp(self):
        self.otp = ''.join(sample("0123456789", 4))  # A Very simple Random OTP generator

    def store_visitor_details(self):
        with self.table_visitors.batch_writer() as batch:
            # TODO: What should you do with Photos here ? Confused...
            item = {'faceId': self.face_id, 'name': self.visitor_name, 'phoneNumber': self.visitor_phone}
            batch.put_item(Item=item)

    def is_otp_valid(self):
        response = self.table_passcodes.query(KeyConditionExpression=Key('code').eq(self.otp))
        response = response['Items']
        curr_time = int(time.time())

        # Filter out expired items because SLA for deletion is 48 hrs.
        response = [item for item in response if item.get('ttl', int('inf')) > curr_time]

        frontend_data = {
            'is_otp_valid': False,
            'visitor_name': "Unknown"
        }
        if len(response) > 0:
            frontend_data['is_otp_valid'] = True
            face_id = response[0]['visitorid']

            # Query for Name
            visitor_det = self.table_visitors.query(
                IndexName='faceId-index',
                KeyConditionExpression=Key('faceId').eq(face_id),
            )
            frontend_data['visitor_name'] = visitor_det['Items'][0]['name']

        return frontend_data


def lambda_handler(event, context):
    # Kinesis Stream Object
    # TODO: Detect process from caller for Kinesis.

    if event.get('process') is None:
        record = event['Records'][0]
        auth = Authenticator()
        payload = base64.b64decode(record['kinesis']['data'])
        matches = json.loads(payload)['FaceSearchResponse']
        
        if not matches:
            print('0')
            # Do Something
        else:
            # Detected face
            print(matches[0]['MatchedFaces'][0]['Face']['FaceId'])
        auth.get_face_id()
        # auth.save_image_v2()
        
        # auth.match_face()
        # auth.send_key_or_request()
        msg = {
            'success': True,
            'error': ""
        }
        return {
            'statusCode': 200,
            'body': json.dumps(msg)
        }
    elif process == "owner approve":
        auth.face_id = event['face_id']
        auth.visitor_name = event['visitor_name']
        auth.visitor_phone = event['visitor_phone']
        auth.store_visitor_details()
        auth.is_face_match = True  # We dont need to lookup the table we just inserted the record
        auth.send_key_or_request()
     
        msg = {
            'success': True,
            'error': ""
        }
        return {
            'statusCode': 200,
            'body': json.dumps(msg)
        }
    elif process == "authorize visitor":
        auth.otp = event['otp']
        auth_response = auth.is_otp_valid()
        return {
            'statusCode': 200,
            'body': json.dumps(auth_response)
        }
    else:
        raise ValueError("Dont know how to process '{}'".format(process))
