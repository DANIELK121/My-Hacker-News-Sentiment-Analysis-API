import requests
from config import *
from classes.parallel_job import ParallelJob


class HNRequestManager:

    def __init__(self, phrase, live_data_url):
        self._phrase = phrase
        self._live_data_url = live_data_url
        self._ids_of_stories_to_fetch = []
        self._stories = []

    @staticmethod
    def get_v1_item(item_id):
        item_string = f'http://hn.algolia.com/api/v1/items/{item_id}'
        return requests.get(item_string)

    @staticmethod
    def get_top_stories_items(ids_list, phrase):
        query_string = f"http://hn.algolia.com/api/v1/search?query={phrase}&restrictSearchableAttributes=title&tags=story,{ids_list}&hitsPerPage=500"
        return requests.get(query_string)

    def set_phrase(self, phrase):
        self._phrase = phrase

    def set_live_data_url(self, url):
        self._live_data_url = url

    def get_stories(self):
        return self._stories

    def set_stories(self, items_list):
        stories_list = [None for i in range(len(items_list))]
        for i, item in enumerate(items_list):
            if type(item) != V1Item:
                stories_list[i] = V1Item(item)
        self._stories = stories_list

    def _prepare_list_ids_to_query(self):
        strings = [[] for j in range(5)]
        top_stories_ids = requests.get(self._live_data_url).json()
        # creating strings of top stories ids for querying HN_algolia API
        for i in range(5):
            string = ''
            for story_id in top_stories_ids[i * 100: (i + 1) * 100]:
                string += f',story_{str(story_id)}'
            string = f'({string[1:]})'
            strings[i] = string
        return strings

    def get_and_store_relevant_stories_ids(self):
        relevant_ids = []
        executor = ParallelJob(5)
        strings = self._prepare_list_ids_to_query()
        queries_result = executor.get_items(strings, HNRequestManager.get_top_stories_items, phrase=self._phrase)
        for query_result in queries_result:
            stories_list = query_result[hits_attr]  # 'hits' is surely a key in query_result
            for story in stories_list:
                # this is needed because not all the results actually have "phrase" in their title (checked)
                if self._phrase.lower() in story[title_attr].lower():  # for every non-empty 'story', 'title' is a key in 'story'
                    relevant_ids.append(story[objectID_attr])
        self._ids_of_stories_to_fetch = relevant_ids

    def get_and_store_relevant_stories(self):
        executor = ParallelJob(5)
        self.set_stories(executor.get_items(
            self._ids_of_stories_to_fetch,
            HNRequestManager.get_v1_item)
        )


class V1Item:
    # right now this class is designed for items that come from
    # 'http://hn.algolia.com/api/v1/items/:item_id' only

    def __init__(self, item):
        self._item = item
        if id_attr in self._item.keys():
            self._item_id = self._item[id_attr]
        else:
            self._item_id = None

    def get_item(self):
        return self._item

    def get_item_id(self):
        return self._item_id

    def get_children_text(self):
        strings = []
        if children_attr in self._item.keys():
            children = self._item[children_attr]
            next_children = []
            while len(children) > 0:
                for child in children:
                    if child[text_attr] is not None:
                        strings.append(child[text_attr])
                    next_children.extend(child[children_attr])
                children = next_children
                next_children = []
        return strings
