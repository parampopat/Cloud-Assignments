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
        self.table_emails = self.client_ddb.Table('emails')
        self.client_sns = boto3.client('sns')
        self.client_email = boto3.client('ses', region_name="us-east-1")
        self.client_rek = boto3.client('rekognition')
        self.s3_client = boto3.client('s3')

        # Attributes populated later.
        self.face_id = None
        self.visitor_phone = None
        self.visitor_name = None
        self.owner_email = "saykartik@gmail.com"
        self.visitor_image_link = "https://upload.wikimedia.org/wikipedia/en/e/ed/Nyan_cat_250px_frame.PNG"
        self.collectionId = 'Collection'
        self.is_face_match = None

        self.otp = None
        self.kinesis_face = None

    def get_face_id(self, bucket=None, fileName=None):
        threshold = 70
        response = self.client_rek.search_faces_by_image(CollectionId=self.collectionId,
                                                         Image={'S3Object': {'Bucket': bucket, 'Name': fileName}},
                                                         FaceMatchThreshold=threshold,
                                                         MaxFaces=1)

        faceMatches = response['FaceMatches']
        if len(faceMatches) > 0:
            self.face_id = faceMatches[0]['Face']['FaceId']
            return self.face_id
            # print(self.face_id)
        else:
            self.face_id = self.gen_face_id(bucket=bucket, fileName=fileName)
            return self.face_id
            # print(self.face_id)

    def gen_face_id(self, bucket=None, fileName=None):
        response = self.client_rek.index_faces(CollectionId=self.collectionId,
                                               Image={'S3Object': {'Bucket': bucket, 'Name': fileName}},
                                               ExternalImageId=fileName,
                                               MaxFaces=1,
                                               QualityFilter="AUTO",
                                               DetectionAttributes=['ALL'])
        for faceRecord in response['FaceRecords']:
            # print(faceRecord['Face']['FaceId'])
            return faceRecord['Face']['FaceId']

    def set_face_id(self, faceid):
        self.face_id = faceid

    def save_image_v2(self, bucket=None):
        kvs_client = boto3.client('kinesisvideo', region_name='us-east-1')
        kvs_data_pt = kvs_client.get_data_endpoint(
            StreamARN="arn:aws:kinesisvideo:us-east-1:041132386971:stream/kbppstream/1586054873891",
            # kinesis stream arn
            APIName='GET_MEDIA')

        end_pt = kvs_data_pt['DataEndpoint']
        kvs_video_client = boto3.client('kinesis-video-media', endpoint_url=end_pt,
                                        region_name='us-east-1')  # provide your region
        kvs_stream = kvs_video_client.get_media(
            StreamARN="arn:aws:kinesisvideo:us-east-1:041132386971:stream/kbppstream/1586054873891",
            # kinesis stream arn
            StartSelector={'StartSelectorType': 'NOW'}  # to keep getting latest available chunk on the stream
        )

        name = ''.join(sample("0123456789", 6))
        f = open('/tmp/stream.mkv', 'wb')
        streamBody = kvs_stream['Payload'].read(1024 * 16384)  # reads min(16MB of payload, payload size) - can tweak this
        f.write(streamBody)
        f.close()
        
        # s3_client = boto3.client('s3', region_name='us-east-1')
        
        # s3_client.upload_file(
        #     '/tmp/stream.mkv',
        #     bucket,  # replace with your bucket name
        #     'stream_3.mkv'
        # )

        # use openCV to get a frame
        cap = cv2.VideoCapture('/tmp/stream.mkv')

        # use some logic to ensure the frame being read has the person, something like bounding box or median'th frame of the video etc
        ret, frame = cap.read()
        cv2.imwrite('/tmp/' + name + '.jpg', frame)
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.upload_file(
            '/tmp/' + name + '.jpg',
            bucket,  # replace with your bucket name
            name + '.jpg'
        )
        cap.release()
        print('Image uploaded')
        # url = 's3://' + bucket + '/' + name + '.jpg'
        url = 'https://'+bucket+'.s3.amazonaws.com/'+name+'.jpg'
        self.visitor_image_link = url
        return name + '.jpg'

    def transfer_image(self, bucket):
        response = self.table_emails.query(
            KeyConditionExpression=Key('faceId').eq(self.face_id),
            ConsistentRead=True
        )
        response = response['Items']

        if len(response) == 1:
            response = response[0]
            url = response.get('temp_url')
        else:
            raise ValueError("The Url should have been written to Dynamo. Its not found. Booooo..")

        # Take image from URL and trasnfer it to the new bucket
        name = url.split('/')[-1]
        source = url.split('/')[-2].split('.')[0]
        s3 = boto3.resource('s3')
        copy_source = {
            'Bucket': source,
            'Key': name
        }
        s3.meta.client.copy(copy_source, bucket, name)
        url = 'https://'+bucket+'.s3.amazonaws.com/'+ name
        self.visitor_image_link = url

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

    def store_email_and_url(self):
        with self.table_emails.batch_writer() as batch:
            # TODO: visitorid might change - keep track
            exp_time = int(time.time()) + 5 * 60  # Expiry in 5 mins
            item = {'faceId': self.face_id, 'temp_url': self.visitor_image_link, 'ttl': exp_time}
            batch.put_item(Item=item)

    def send_key_or_request(self):
        # TODO Add to dynamo the timestamp with faceid to avoid epeated mails
        in_process = False

        if self.is_face_match:
            # Check if OTP is sent
            response = self.table_passcodes.query(
                IndexName='visitorid-index',
                KeyConditionExpression=Key('visitorid').eq(self.face_id),
            )
            response = response['Items']
            curr_time = int(time.time())
            response = [item for item in response if item.get('ttl', float('inf')) > curr_time]
            in_process = len(response) > 0
        else:
            # Check if email is sent
            response = self.table_emails.query(
                KeyConditionExpression=Key('faceId').eq(self.face_id),
                ConsistentRead=True
            )
            response = response['Items']
            curr_time = int(time.time())
            response = [item for item in response if item.get('ttl', float('inf')) > curr_time]
            in_process = len(response) > 0

        if not in_process:
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
                self.store_email_and_url()
                print('I Tried Sending EMail')
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
        else:
            print('Email Already Sent')

    def generate_otp(self):
        self.otp = ''.join(sample("0123456789", 4))  # A Very simple Random OTP generator

    def store_visitor_details(self):
        with self.table_visitors.batch_writer() as batch:
            # TODO: What should you do with Photos here ? Confused...
            item = {'faceId': self.face_id, 'name': self.visitor_name, 'phoneNumber': self.visitor_phone}
            batch.put_item(Item=item)

    def is_otp_valid(self):
        response = self.table_passcodes.query(KeyConditionExpression=Key('code').eq(self.otp), ConsistentRead=True)
        response = response['Items']
        curr_time = int(time.time())

        # Filter out expired items because SLA for deletion is 48 hrs.
        response = [item for item in response if item.get('ttl', float('inf')) > curr_time]

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
    auth = Authenticator()
    bucket = 'ppkbvisitorvault'
    temp_bucket = 'tempvisitorvault'

    if event.get('process', None) is None:
        record = event['Records'][0]
        payload = base64.b64decode(record['kinesis']['data'])
        matches = json.loads(payload)['FaceSearchResponse']

        if not matches:
            print('0')
            # Do Something about saving and generating face id
            filename = auth.save_image_v2(temp_bucket)
            faceid = auth.get_face_id(temp_bucket, filename)
            auth.set_face_id(faceid)
            # Update Dynamo With TempURL
            auth.match_face()
            auth.send_key_or_request()
            # Once we have number and name, update URL and Trasnfer photo to main bucket
        else:
            # Detected face
            faceid = matches[0]['MatchedFaces'][0]['Face']['FaceId']
            print(faceid)
            _ = auth.save_image_v2(temp_bucket)
            # Send OTP? But verify if we have number
            auth.set_face_id(faceid)
            auth.match_face()
            auth.send_key_or_request()

        msg = {
            'success': True,
            'error': ""
        }
        return {
            'statusCode': 200,
            'body': json.dumps(msg)
        }
    elif event['process'] == "owner approve":
        # query using faceid to get url
        auth.face_id = event['face_id']
        auth.visitor_name = event['visitor_name']
        auth.visitor_phone = event['visitor_phone']
        auth.store_visitor_details()
        # transfer photo to main bucket

        auth.transfer_image(bucket)  # Here set visitor link to new url

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
    elif event['process'] == "authorize visitor":
        auth.otp = event['otp']
        auth_response = auth.is_otp_valid()
        return {
            'statusCode': 200,
            'body': json.dumps(auth_response)
        }
    else:
        raise ValueError("Dont know how to process '{}'".format(event['process']))
