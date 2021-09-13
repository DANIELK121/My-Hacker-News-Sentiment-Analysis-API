import time
from config import *
from classes.hn_request_manager import HNRequestManager
from classes.aws_request_manager import SentimentAnalysisRequestManager


class RequestManager:

    def __init__(self, phrase, live_data_url):
        self._hnRequestManager = HNRequestManager(phrase, live_data_url)
        self._sentimentAnalysisRequestManager = SentimentAnalysisRequestManager()
        self._some_processing_succeeded = 0
        self._comments_text = []
        self._response_body = {}

    def make_request(self, phrase=None, live_data_url=None):
        if phrase is not None:
            self._hnRequestManager.set_phrase(phrase)
        if live_data_url is not None:
            self._hnRequestManager.set_live_data_url(live_data_url)

        self._get_comments_from_hn()
        self._get_aws_sentiment_analysis()

    def _get_comments_from_hn(self):
        hnReqManager = self._hnRequestManager
        hnReqManager.get_and_store_relevant_stories_ids()
        hnReqManager.get_and_store_relevant_stories()
        # gathering all comments text into one array
        self._comments_text = []
        for story in hnReqManager.get_stories():
            self._comments_text.extend(story.get_children_text())
        if len(self._comments_text) > 0:
            self._some_processing_succeeded = 1  # some comments were gathered

    def _get_aws_sentiment_analysis(self):
        senAnalReqManager = self._sentimentAnalysisRequestManager
        # splitting the comments into batches. 25 strings in each
        senAnalReqManager.strings_to_batches(self._comments_text)
        senAnalReqManager.get_and_store_sentiment_analysis_batches()
        if self._some_processing_succeeded == 1 and \
                len(senAnalReqManager.get_sentiment_analysis_batches()) == 0:
            raise Exception("No comments were analyzed")  # problem with analyzing the comments
        senAnalReqManager.extract_and_store_comments_scores()
        self._response_body[response_attr] = senAnalReqManager.avg_median_of_all_scores()

    def get_response(self):
        return self._response_body
