import json

from classes.request_manager import RequestManager


# sentiment analysis of comments of HackerNews' top stories in which
# contain "phrase" in their title
def hn_sentiment_analysis(event, context):
    try:
        phrase = event['queryStringParameters']['phrase']
        hnTopStoriesURL = "https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty"
        requestManager = RequestManager(phrase, hnTopStoriesURL)
        requestManager.make_request()

        statusCode = 200
        response = requestManager.get_response()
    except Exception as e:
        statusCode = 416
        response = str(e)

    return dict(
        statusCode=statusCode,
        body=json.dumps(response)
    )
