# standard libraries
import collections
import copy
import functools
import logging
import threading

# third party libraries
# None

# local libraries
from nion.swift import DataGroup
from nion.swift import Utility
from nion.ui import UserInterfaceUtility


class DataItemsBinding(UserInterfaceUtility.Binding):

    def __init__(self):
        super(DataItemsBinding, self).__init__(None)
        self.__data_items = list()
        self._update_mutex = threading.RLock()
        self.inserters = dict()
        self.removers = dict()
        self.__filter = None
        self.__sort = None
        self.__change_level = 0

    def begin_change(self):
        self.__change_level += 1

    def end_change(self):
        self.__change_level -= 1
        if self.__change_level == 0:
            self._update_data_items()

    def changes(self):
        """ Acquire this while setting filter or sort so that changes get made simultaneously. """
        class ChangeTracker(object):
            def __init__(self, binding):
                self.__binding = binding
            def __enter__(self):
                self.__binding.begin_change()
                return self
            def __exit__(self, type, value, traceback):
                self.__binding.end_change()
        return ChangeTracker(self)

    # thread safe.
    def __get_sort(self):
        return self.__sort
    def __set_sort(self, sort):
        with self._update_mutex:
            self.__sort = sort
        self._update_data_items()
    sort = property(__get_sort, __set_sort)

    # thread safe.
    def __get_filter(self):
        return self.__filter
    def __set_filter(self, filter):
        with self._update_mutex:
            self.__filter = filter
        self._update_data_items()
    filter = property(__get_filter, __set_filter)

    # thread safe
    # data items are the currently filtered and sorted list.
    def __get_data_items(self):
        with self._update_mutex:
            return copy.copy(self.__data_items)
    data_items = property(__get_data_items)

    # thread safe
    # subclasses should implement this to return the master list of data items
    def _get_master_data_items(self):
        raise NotImplementedError()

    # thread safe.
    def _update_data_items(self):
        if self.__change_level > 0:
            return
        with self._update_mutex:
            # first build the new data_items list, including data items with master data.
            old_data_items = copy.copy(self.__data_items)
            master_data_items = list()
            for data_item in self._get_master_data_items():
                if data_item.has_master_data:
                    master_data_items.append(data_item)
            # sort the master data list
            if self.sort:
                sort_key, reverse = self.sort(self.container)
                master_data_items.sort(key=sort_key, reverse=reverse)
            # construct the data items list by expanding each master data item to
            # include its children
            data_items = list()
            for data_item in master_data_items:
                # apply filter
                if not self.__filter or self.__filter(data_item):
                    # add data item and its dependent data items
                    data_items.append(data_item)
                    data_items.extend(list(DataGroup.get_flat_data_item_generator_in_container(data_item)))
            # now generate the insert/remove instructions to make the official
            # list match the proposed list.
            assert len(set(self._get_master_data_items())) == len(self._get_master_data_items())
            assert len(set(master_data_items)) == len(master_data_items)
            assert len(set(data_items)) == len(data_items)
            index = 0
            for data_item in data_items:
                # if old data item at current index isn't in new list, remove it
                if index < len(old_data_items) and old_data_items[index] not in data_items:
                    data_item_to_remove = old_data_items[index]
                    assert data_item_to_remove in self.__data_items
                    del old_data_items[index]
                    del self.__data_items[index]
                    for remover in self.removers.values():
                        remover(data_item_to_remove, index)
                # otherwise, if new data item at current index is in old list, remove it, then re-insert
                if data_item in old_data_items:
                    old_index = old_data_items.index(data_item)
                    assert index <= old_index
                    # remove, re-insert, unless old and new position are the same
                    if index < old_index:
                        assert data_item in self.__data_items
                        del old_data_items[old_index]
                        del self.__data_items[old_index]
                        for remover in self.removers.values():
                            remover(data_item, old_index)
                        assert data_item not in self.__data_items
                        old_data_items.insert(index, data_item)
                        self.__data_items.insert(index, data_item)
                        for inserter in self.inserters.values():
                            inserter(data_item, index)
                # else new data item at current index is not in old list, insert it
                else:
                    assert data_item not in self.__data_items
                    old_data_items.insert(index, data_item)
                    self.__data_items.insert(index, data_item)
                    for inserter in self.inserters.values():
                        inserter(data_item, index)
                index += 1
            # finally anything left in the old list can be removed
            while index < len(old_data_items):
                data_item_to_remove = old_data_items[index]
                assert data_item_to_remove in self.__data_items
                del old_data_items[index]
                del self.__data_items[index]
                for remover in self.removers.values():
                    remover(data_item_to_remove, index)


class DataItemsFilterBinding(DataItemsBinding):

    def __init__(self, data_items_binding):
        super(DataItemsFilterBinding, self).__init__()
        self.__master_data_items = list()
        self.__data_items_binding = data_items_binding
        self.__data_items_binding.inserters[id(self)] = lambda data_item, before_index: self.data_item_inserted(data_item, before_index)
        self.__data_items_binding.removers[id(self)] = lambda data_item, index: self.data_item_removed(data_item, index)

    def close(self):
        del self.__data_items_binding.inserters[id(self)]
        del self.__data_items_binding.removers[id(self)]
        super(DataItemsFilterBinding, self).close()

    # thread safe.
    def data_item_inserted(self, data_item, before_index):
        with self._update_mutex:
            assert data_item not in self.__master_data_items
            self.__master_data_items.insert(before_index, data_item)
        self._update_data_items()

    # thread safe.
    def data_item_removed(self, data_item, index):
        with self._update_mutex:
            assert data_item in self.__master_data_items
            del self.__master_data_items[index]
        self._update_data_items()

    # thread safe
    def _get_master_data_items(self):
        return self.__master_data_items


class DataItemsInContainerBinding(DataItemsBinding):
    """
        Bind the data items in a container (recursively).

        When a data item is added or removed, the list is sorted, filtered, and
        a set of insert/remove messages are sent to the inserter and remover
        connections.

        The container must send the update_counted_data_items and
        subtract_counted_data_items messages to this object.
    """

    def __init__(self):
        super(DataItemsInContainerBinding, self).__init__()
        self.__counted_data_items = collections.Counter()
        self.__container = None

    def close(self):
        self.container = None
        super(DataItemsInContainerBinding, self).close()

    # thread safe.
    def __get_container(self):
        return self.__container
    # not thread safe.
    def __set_container(self, container):
        if self.__container:
            self.__container.remove_listener(self)
            self.subtract_counted_data_items(self.__container.counted_data_items)
            self.__container.remove_ref()
        self.__container = container
        if self.__container:
            self.__container.add_ref()
            self.update_counted_data_items(self.__container.counted_data_items)
            self.__container.add_listener(self)
    container = property(__get_container, __set_container)

    # thread safe.
    def update_counted_data_items(self, counted_data_items):
        with self._update_mutex:
            self.__counted_data_items.update(counted_data_items)
        self._update_data_items()

    # thread safe.
    def subtract_counted_data_items(self, counted_data_items):
        with self._update_mutex:
            self.__counted_data_items.subtract(counted_data_items)
            self.__counted_data_items += collections.Counter()  # strip empty items
        self._update_data_items()

    # thread safe
    def _get_master_data_items(self):
        return self.__counted_data_items


def sort_natural(container):
    flat_data_items = list(DataGroup.get_flat_data_item_generator_in_container(container))
    def sort_key(data_item):
        return flat_data_items.index(data_item)
    return sort_key, False


def sort_by_date_desc(container):
    def sort_key(data_item):
        date_item_datetime = Utility.get_datetime_from_datetime_item(data_item.datetime_original)
        return date_item_datetime
    return sort_key, True
