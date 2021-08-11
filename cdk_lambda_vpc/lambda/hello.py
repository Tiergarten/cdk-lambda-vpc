import json
import requests


def handler(event, context):
    print('request: {}'.format(json.dumps(event)))
    print(requests.get('http://ifconfig.co/json').json())

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/plain'
        },
        'body': 'Hello, CDK! You have hit rock bottom\n'
    }
