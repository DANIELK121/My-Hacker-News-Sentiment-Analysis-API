import concurrent.futures


class ParallelJob:

    def __init__(self, num_of_threads=None):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_of_threads)

    def get_items(self, ids, func, num_of_threads=None, phrase=None):
        if num_of_threads is not None:
            self._executor = concurrent.futures.ThreadPoolExecutor(num_of_threads)
        return self._get_items(ids, func, phrase=phrase)

    def _get_items(self, ids, func, phrase=None):
        items = []
        with self._executor:
            # Start the load operations and mark each future with its item_id
            if phrase is None:
                future_to_id = {self._executor.submit(func, item_id): item_id for item_id in ids}
            else:
                future_to_id = {self._executor.submit(func, item_id, phrase): item_id for item_id in ids}
            # Handling finished jobs
            for future in concurrent.futures.as_completed(future_to_id):
                item_id = future_to_id[future]
                try:
                    item = future.result()
                except Exception as exc:
                    print('%r generated an exception: %s' % (item_id, exc))
                else:
                    if item is not None and item.status_code == 200:
                        items.append(item.json())
        return items
