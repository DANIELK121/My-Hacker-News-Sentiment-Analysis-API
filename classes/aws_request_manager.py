import json
import numpy as np
import requests
from config import *
from classes.parallel_job import ParallelJob


class SentimentAnalysisRequestManager:

    def __init__(self):
        self._batches_to_analyze = []
        self._sentiment_analysis_batches = []
        self._analysis_scores = []

    @staticmethod
    def sentiment_analysis(stringList):
        url = 'https://v64gp2lxcc.execute-api.us-east-2.amazonaws.com/prod/sentimentanalysisapi'
        return requests.post(url, json.dumps({'Text': stringList}))

    def get_batches_to_analyze(self):
        return self._batches_to_analyze

    def get_sentiment_analysis_batches(self):
        return self._sentiment_analysis_batches

    def get_analysis_scores(self):
        return self._analysis_scores

    def strings_to_batches(self, strings):
        num_of_strings = len(strings)
        num_of_batches = np.math.floor(num_of_strings / 25)
        left_overs = num_of_strings % 25
        batches = [['' for j in range(25)] for i in range(num_of_batches)]

        for i in range(num_of_batches):
            for j in range(25):
                batches[i][j] = strings[i * 25 + j]

        if left_overs != 0:
            last_batch = ['' for i in range(left_overs)]
            for i in range(left_overs):
                last_batch[i] = strings[-(i + 1)]
            batches.append(last_batch)

        self._batches_to_analyze = batches

    def get_and_store_sentiment_analysis_batches(self):
        executor = ParallelJob(5)
        self._sentiment_analysis_batches = executor.get_items(
            self._batches_to_analyze,
            SentimentAnalysisRequestManager.sentiment_analysis
        )

    def extract_and_store_comments_scores(self):
        analysis_scores_list = []
        for item in self._sentiment_analysis_batches:  # list of: json for each analysis
            if status_code_attr in item.keys() and item[status_code_attr] == 200:
                item_analysis_list = item[response_attr]  # list of 25 analysis
                curr_analysis_scores = ['' for i in range(len(item_analysis_list))]
                for i, comment_scores in enumerate(item_analysis_list):
                    curr_analysis_scores[i] = comment_scores[sen_score_attr]
                analysis_scores_list.extend(curr_analysis_scores)

        self._analysis_scores = analysis_scores_list

    def avg_median_of_all_scores(self):
        scores = self._analysis_scores
        n = len(scores)
        pos_avg = 0; pos_med = 0; neg_avg = 0; neg_med = 0
        neu_avg = 0; neu_med = 0; mix_avg = 0; mix_med = 0
        if n != 0:
            positives = np.zeros(n)
            negatives = np.zeros(n)
            neutrals = np.zeros(n)
            mixed = np.zeros(n)
            for i in range(n):
                positives[i] = scores[i][positive_attr]
                negatives[i] = scores[i][negative_attr]
                neutrals[i] = scores[i][neutral_attr]
                mixed[i] = scores[i][mixed_attr]
            pos_avg = np.round(np.average(positives), decimals=2)
            pos_med = np.round(np.median(positives), decimals=2)
            neg_avg = np.round(np.average(negatives), decimals=2)
            neg_med = np.round(np.median(negatives), decimals=2)
            neu_avg = np.round(np.average(neutrals), decimals=2)
            neu_med = np.round(np.median(neutrals), decimals=2)
            mix_avg = np.round(np.average(mixed), decimals=2)
            mix_med = np.round(np.median(mixed), decimals=2)
        return {
            'comments': n,
            'positive': {'avg': pos_avg, 'median': pos_med},
            'neutral': {'avg': neu_avg, 'median': neu_med},
            'negative': {'avg': neg_avg, 'median': neg_med},
            'mixed': {'avg': mix_avg, 'median': mix_med}
        }


