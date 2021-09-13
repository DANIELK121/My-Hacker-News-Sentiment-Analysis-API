import boto3


def lambda_handler(event, context):
    try:
        client_sentiment = boto3.client('comprehend')  # create a client object
        text = event['Text']
        response = client_sentiment.batch_detect_sentiment(
            TextList=text,
            LanguageCode='en'
        )
        return {
            'statusCode': 200,
            'response' : response['ResultList']
        }
    except Exception as e:
        return {
            'statusCode':416,
            'response':str(e)
        }
