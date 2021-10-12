# Hacker News Sentiment Analysis API
Welcome to Hacker News (HN) Sentiment Analysis API!

Here you can query an API with a certain phrase and get a sentiment analysis of all comments users had to stories with that phrase in the title, from HN "top stories".
Use this link: 

https://ljk650ods9.execute-api.us-east-1.amazonaws.com/prod/projects/hn_sentiment_analysis?phrase=Epic%20Games

to get the sentiment analysis of the comments users had to stories with "Epic Games" in the title. Change the value of `phrase` to make your own search!
# Response
The response will be aggregated statistics of the sentiment analysis of comments to stories with `phrase` in title.

e.g.

`GET https://dhtmde8gs5.execute-api.us-east-1.amazonaws.com/dev/exabeam/hn_sentiment_analysis?phrase=Epic%20Games`

response:
```
  {
    "comments": 79, 
    "positive": {
      "avg": 0.05, 
      "median": 0.01
    }, 
    "neutral": {
      "avg": 0.34, 
      "median": 0.29
    }, 
    "negative": {
      "avg": 0.47, 
      "median": 0.45
    },
    "mixed": {
      "avg": 0.15, 
      "median": 0.03
    }
  }
```

where `comments` is the number of total comments analyzed, from all the stories that contained the phrase "Epic Games" in its title (case insensitive).

If there are no stories in HN top stories with `phrase` in the title, or it doesn't have any comments yet - all the fields in the response will be with value `0`. 

Otherwise, when there are comments to analyze and no comment was analyzed due to any reason - error code 416 is returned with an error message.

**Another kind of response** is the 504 error code from the serverless server after 30 seconds with no response from the deployed function. The error message will be "Endpoint request timed out". This can happen when searching for phrases that appear in many stories' title (like common words).

# Frameworks, API's, Classes And Libraries I Used In This Project
## Frameworks and Services
I used the [serverless framework](https://www.serverless.com/) to deploy my `hn_sentiment_analysis` function.

For the sentiment analysis I made a user at AWS and used a Lambda Function service I called ComprehendLambda. In this function, the analysis is made with the `boto3.client('comprehend').batch_detect_sentiment()` method, that can take a batch of up to 25 different text segments and returns a JSON object that holds a sentiment analysis for each text segment in the batch given (code for the ComprehendLambda function can be found in `/aws/comprehend_lambda.py`). I also used threads to make several requests from the service in parallel, to make the job faster (I will explain where and how I did it in the **Classes** section).

I decided to work with AWS since `batch_detect_sentiment()` returns a nice and clean result for each text segment in the batch it is given. Besides that, choosing AWS as the services provider on the serverless framework was easy going, so that also had its affect.

## API's
I used two different API's for getting HN top stories that have `phrase` in their title. 

First, to get their top stories' ids I used their [v0 public API](https://github.com/HackerNews/API). Especially, I used this request to get their top stories' ids: https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty. This API is good for getting single items or [Live Data](https://github.com/HackerNews/API#live-data) groups of ids from HN, but it is not so easy when you want to get dozens or hundredes of items quickly. 

For the last task I used their [v1 public API](https://hn.algolia.com/api). This API enables you to make full-text queries on their data bases and filter on various tags, so once I had top stories' ids I made a request like this: 

`http://hn.algolia.com/api/v1/search?query=Epic%20Games&restrictSearchableAttributes=title&tags=story,(f'story_{id}' for id in top stories' ids)`

The response will be a JSON object containing a JSON object with details for every top stories with `phrase` in their title. The response may hold additional objects with stories that doesn't have `phrase` in their title, so there should be a correctness check after getting the response. Still, this is much faster than asking for one top story at a time and checking it's title (this is how I found it to be done using the v0 public API). 

After I have the top stories' ids with `phrase` in their title I use this request: http://hn.algolia.com/api/v1/items/:id to get a JSON object with details about the story with `story id = id`. This object is actually the root of a tree containing **all the comments** to the story. So for each story, extracting the comments is done in-memory(!) instead of reaching HN's v0 API for each comment.

At last, I used threads to make several requests from the v1 public API in parallel to make the job faster.

## Classes and Libraries

### Main Function

`handler.hn_sentiment_analysis(event, context)`

This is the function that is being executed when a user is querying this API for a certain phrase. It initializes a `RequestManager` object that handles the request and finally getting the response from it. It returns the response with a `statusCode=200` or an error message with `statusCode=416` if something went wrong.

### Classes

#### request_manager.RequestManager

Given a `phrase` and a HN `live_data_url` of a Live Data ids group, this class manages the request and using the `hn_request_manager` module and `aws_request_manger` module as needed. It holds the final result in a dictionary that is reachable with the `requestManager.get_response()` method. So using this class you can easilly get the sentiment of the comments users had to stories with `phrase` in the title, for any Live Data group of items' ids on HN.

Main Functions
1. `__init__(self, phrase, live_data_url)` - creating a class object. The constructor assigns a new `HNRequestManager(phrase, live_data_url)` object to a field named `_hnRequestManager` and a new `SentimentAnalysisRequestManager()` object to a field named `_sentimentAnalysisRequestManager`. Another field named `_some_processing_succeeded` is set to `0`. While this field value is `0` it indicates that there are no comments to analyze.
2. `make_request(self, phrase=None, live_data_url=None)` - when both parameters are `None`, calls `self._get_comments_from_hn()` method and then calling `self._get_aws_sentiment_analysis()` method. This means that the query will be with the values of `phrase`, `live_data_url` that the object was initiallized with. Otherwise, update the object stored in `_hnRequestManager` with the values that are not `None` and make the query. 
3. `_get_comments_from_hn(self)` - getting from HN APIs the stories from `live_data_url` with `phrase` in the title. If any comments were retrieved then `_some_processing_succeeded` is set to `1` and the comments' text is saved into `self._comments_text`.
4. `_get_aws_sentiment_analysis(self)` - getting the sentiment analysis of the comments that are stored in `self._comments_text`. If no comment was analyzed raises an `Exception`. Otherwise the response is calculated and is stored in `self._response_body`.


#### hn_request_manager.HNRequestManager

Given a `phrase` and a HN `live_data_url` of a Live Data ids group, this class manages the request infront of the different HN APIs. It fetches the Live Data group od ids, making a full-text query to get top stories with `phrase` in the title and then fetching the story items with its' comments. Each story item is then wrapped by a V1Item class (coming up next) that handles the extraction of the comments from each story item.

Moreover, given a phrase and a list of items' ids this class can get all the stories in that list with `phrase` in the title, so in the future it is possible to search stories with `phrase` in the title from any given list of ids.

  Main Functions
  1. `__init__(self, phrase, live_data_url)` - creating a class object to search HN stories from `live_data_url` with `phrase` in the title.
  2. `get_and_store_relevant_stories_ids(self)` - calling `_prepare_list_ids_to_query(self)` to get the ids of the items in `self._live_data_url` as strings that will be used for querying the v1 public API (as mentioned above). Based on the previous result,  it uses a `ParallelJob` object (last class explained) to make multiple quries in parallel and get the relevant items. The function that is executed in parallel is `HNRequestManager.get_top_stories_items`. Then it checks the correctness of the items returned (i.e that `phrase` is in the title) and stores the relevant items' ids in `self._ids_of_stories_to_fetch`.
  3. `_prepare_list_ids_to_query(self)` - querying the url stored in `self._live_data_url` (this time, fetching the HN top stories' ids from v0 public API). The response is stored in a local variable and then query strings are made based on the ids fetched. The strings are of the type: `(story_id1, story_id2, ..., story_idn)`. The output is an array with the query strings as elements.
  4. `get_and_store_relevant_stories(self)` - uses a `ParallelJob` object to get the relevant story items based on the ids stored in `self._ids_of_stories_to_fetch`. The function that is executed in parallel is `HNRequestManager.get_v1_item`.
  5. `set_stories(self, items_list)` - sets in `self._stories` the elements of `items_list` as `V1Item` (coming up next) elements. Right now the assumption is that all the elements in `items_list` are items from the v1 public API.

#### hn_request_manager.V1Item

Right now, an object of this class is designed to hold items that come from 'http://hn.algolia.com/api/v1/items/:item_id' only. When this is the situation - use the `v1Item.get_comments_text()` method to extract the text of all the comments of the given item. In this application v1Item objects hold HN stories, but it can hold comments as well.

Main Functions
1. `__init__(self, item)` - creates a class object and assigning `item` to the `self._item` field. Extracts the id of `item` if exists and stores it in `self._item_id`.
2. `get_children_text(self)` - iterating over the tree that `self._item` is its root and extracting the text from each node (except the root's) into a local array variable named `strings`. The output is `strings`.

#### aws_request_manager.SentimentAnalysisRequestManager

This class is responsible for getting the sentiment analysis of the comments, making POST requests to the ComprehendLambda function at the AWS. It can also compute the average and median of the scores in each sentiment category.
  
   Main Functions
  1. `strings_to_batches(self, strings)` - gets an array of strings and splits them into batches of up to 25 strings in a batch. The result is an array of arrays ("batches"). Each inner array holds up to 25 strings. The result is saved into `self._batches_to_analyze`
  2. `get_and_store_sentiment_analysis_batches(self)` - uses a `ParallelJob` object to get the sentiment analysis of the batches stored in `self._batches_to_analyze`. The function that is executed in parallel is `SentimentAnalysisRequestManager.sentiment_analysis`. The result is saved into `self._sentiment_analysis_batches`.
  3. `extract_and_store_comments_scores(self)` - extracts from `self._sentiment_analysis_batches` the sentiment analysis score of each analyzed comment and gather all of them into an array. The result is stored in `self._analysis_scores`.
  4. `avg_median_of_all_scores(self)` - for each sentiment category, computes the average and median of the scores stored in `self._analysis_scores`. The output is a python dictionary as desired in the service's response.

#### parallel_job.ParallelJob

This class uses the `concurrent.futures` package to improve the efficiency of jobs used by the service that can be done in parallel.
    
   Main Functions
   1. `__init__(self, num_of_threads=None)` - creating a class object and stores a `concurrent.futures.ThreadPoolExecutor()` object in `self._executor`. `num_of_threads` indicates the maximum number of threads to work in parallel in a job. If `num_of_threads` is `None`, it will default to the number of processors on the machine multiplied by 5.
   2. `get_items(self, ids, func, num_of_threads=None, phrase=None)` - using `self._executor` to execute the function `func` in parallel by threads. In each execution the input to `func` is a different `id` from `ids` array. `phrase` can be used to pass a second parameter to `func`. The output is an array with the result of all the succesfull executions. If `num_of_threads` is not `None` then a new `concurrent.futures.ThreadPoolExecutor()` object is created and stored in `self._executor`. Then the job is executed with the new maximum number of threads. 

### Main Libraries

#### requests

Used inside `HNRequestManager` class to make GET requests to the different HN APIs. Used inside `SentimentAnalysisRequestManager` class to make POST requests to the ComprehendLambda function in AWS. 

#### concurrent.futures

Used inside `ParallelJob` class at the construction of a new object to initiate a `concurrent.futures.ThreadPoolExecutor()` object that is stored in the `self._executor` field. The `ParallelJob` object is using `self._executor` to execute a function in parallel by threads.

#### numpy

Used in `SentimentAnalysisRequestManager` to optimize operations on arrays holding floats.

## Future Improvements

As mentioned above, if the `handler.hn_sentiment_analysis(event, context)` function doesn't return in 30 seconds the user will get an `Endpoint request timed out` error message from the server and no results are shown. This is not the best behavior one can expect, and I believe it is preffered that some results will be shown even if the computation is not over. I started searching for solution to the problem and found some interesting ideas but due to lack of time I wasn't able to implement the solution. So in the future I will try to assign a handler that handles a signal that is sent to the service 2-3 seconds before the time out. The signal will be scheduled to be sent 2-3 seconds before time out using the `signal.alarm(int(context.get_remaining_time_in_millis() / 1000) - 3)` methods (importing python `signal` package). The handler will run the service from the point after getting the sentiment analysis from the ComprehendLambda function, based on the analysis that was gathered before the signal was sent. It is most likely that in a situation like this many comments will be already analyzed and there will be results to show.
