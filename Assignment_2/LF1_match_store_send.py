import boto3
from boto3.dynamodb.conditions import Key
from random import sample
import json

VIRTUAL_DOOR_URL = "www.google.com"
GRANT_PAGE_BASE = ""


class Authenticator:
    def __init__(self):
        # Clients
        self.client_ddb = boto3.resource('dynamodb', region_name="us-east-2")
        self.table_passcodes = self.client_ddb.Table('passcodes')
        self.table_visitors = self.client_ddb.Table('visitors')
        self.client_sns = boto3.client('sns')
        self.client_email = boto3.client('ses')

        # Attributes populated later.
        self.face_id = None
        self.visitor_phone = None
        self.visitor_name = None
        self.owner_email = None
        self.visitor_image_link = "https://upload.wikimedia.org/wikipedia/en/e/ed/Nyan_cat_250px_frame.PNG"

        self.is_face_match = None

        self.otp = None
        self.kinesis_face = None

    def get_face_id(self):
        # TODO: Figure out how to read from a kinesis client to get face ID
        self.face_id = "kbhy6534"  # Data from Stream passed into this function

    def match_face(self):
        response = self.table_visitors.query(
            IndexName='faceId-index',
            KeyConditionExpression=Key('faceId').eq(self.face_id),
        )

        if len(response['Items']) > 0:
            # TODO: get path to S3 object and replace here
            details = response['Items'][0]
            self.visitor_phone = details['phoneNumber']
            self.visitor_name = details['name']
            # self.visitor_image_link = "{}/{}".format( "path/to/s3", details['objectKey'])
            self.is_face_match = True
        else:
            self.is_face_match = False

    def store_otp(self):
        # write otp to DynamoDB
        if self.otp is None:
            raise ValueError("otp must be set in the object before invoking this")

        # TODO: Should we make sure there is only one active OTP by flushing previous ?
        with self.table_passcodes.batch_writer() as batch:
            # TODO: visitorid might change - keep track
            item = {'code': self.otp, 'visitorid': self.face_id}
            batch.put_item(Item=item)

    def send_key_or_request(self):
        if self.is_face_match:
            self.generate_otp()
            self.store_otp()

            # TODO: Replace 'visitor' with name on File. Assumes OTP succeeded.
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
                Grant Access by clicking <a href="{}">here</a>
                <img src="{}" alt="headshot">
                """.format(grant_page_url, self.visitor_image_link)
            )
            self.client_email.send_email(
                Source="smartdoorauth@incredible.com",
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
            # TODO: visitorid might change - keep track
            # TODO: What should you do with Photos here ? Confused...
            item = {'faceId': self.face_id, 'name': self.visitor_name, 'phoneNumber': self.visitor_phone}
            batch.put_item(Item=item)

    def is_otp_valid(self):
        response = self.table_passcodes.query(KeyConditionExpression=Key('code').eq(self.otp))

        frontend_data = {
            'is_otp_valid': False,
            'visitor_name': "Unknown"
        }
        if len(response['Items']) > 0:
            frontend_data['is_otp_valid'] = True
            face_id = response['Items'][0]['visitorid']

            # Query for Name
            visitor_det = self.table_visitors.query(
                IndexName='faceId-index',
                KeyConditionExpression=Key('faceId').eq(face_id),
            )
            frontend_data['visitor_name'] = visitor_det['Items'][0]['name']

        return frontend_data


def lambda_handler(event, context):
    # Kinesis Stream Object
    # TODO: Detect process from caller
    process = event['process']
    auth = Authenticator()

    if process == "kinesis event":
        auth.get_face_id()
        auth.match_face()
        auth.send_key_or_request()
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
