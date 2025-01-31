# standard libraries
import collections
import gettext
import uuid

# third party libraries
# None

# local libraries
from nion.utils import Event
from nion.utils import Observable
from nion.utils import Persistence

_ = gettext.gettext


"""

    Group layout.
    Live. Live acquisition items.
    Library. Static items.

    *   The user can edit/delete the Library group, and create additional top level groups.
    However, at least one group in addition to the Live group must always be present.
    *   The user cannot delete the live group.
    *   The user cannot add/delete items from the Live group.
    *   Groups can be re-ordered, but the Live group is always first.
    *   New items are put in the first group after Live.

    *   NOTES
    Groups can contain child groups and data items.

    One design option is to have the document controller hold a single data group.
    This has the advantage of making access very uniform. However, this also makes
    it very easy for the user to "lose" items at the top level, which they might not
    see unless they selected the topmost group.

    Another design option is to have the document controller hold a list of data
    groups. This is more complex structure, but makes it easier for the user to
    understand the structure.

    Smart Groups

    Smart groups work on sibling data groups (aka the data items in the smart group's
    container). A smart group at the top level of groups will be able to filter
    and sort data items contained in other top level groups.
    Is there a need for smart groups anywhere except at the top level?

    - (A1a: 1, A1b: 1, A1b1: 2, A1b1a: 2, A1b2: 1, B1: 1, B1a: 1) [0]
    Smart Group [-]
    Group A (A1a: 1, A1b: 1, A1b1: 1, A1b1a: 1, A1b2: 1) [-]
    Group A1 (A1a: 1, A1b: 1, A1b1: 1, A1b1a: 1, A1b2: 1) [A]
    Data Item A1a () [A1]
    Data Item A1b (A1b1: 1, A1b1a: 1, A1b2: 1) [A1]
    Data Item A1b1 (A1b1a: 1 [A1b]
    Data Item A1b1a () [A1b1]
    Data Item A1b2 () [A1b]
    Group B (B1: 1, B1a: 1, A1b1: 1, A1b1a: 1) [-]
    Data Item B1 (B1a: 1) [B]
    Data Item B1a [B1]
    Data Item A1b1 (A1b1a: 1) [B, A1b]
    Data Item A1b1a [A1b1]

    Data item A1b1b gets added to A1b1. A1b1 counted_display_items gets updated, then tells its containers B, A1b
    that they have been updated. B, A1b counted_display_items get updated, then tell their containers, etc.
    When each group gets the counted_display_items_updated message, it tells any smart container children
    that they need to re-filter.

    Data item A2 gets added to Group A.

    """


class UuidsToStringsConverter:
    def convert(self, value):
        return [str(uuid_) for uuid_ in value]
    def convert_back(self, value):
        return [uuid.UUID(uuid_str) for uuid_str in value]


class DataGroup(Observable.Observable, Persistence.PersistentObject):

    def __init__(self):
        super().__init__()
        self.define_type("data_group")
        self.define_property("title", _("Untitled"), validate=self.__validate_title, changed=self.__property_changed)
        self.define_property("display_item_references", list(), validate=self.__validate_display_item_references, converter=UuidsToStringsConverter(), changed=self.__property_changed)
        self.define_relationship("data_groups", data_group_factory, insert=self.__insert_data_group, remove=self.__remove_data_group)
        self.__get_display_item_by_uuid = None
        self.__display_items = list()
        self.__counted_display_items = collections.Counter()
        self.display_item_inserted_event = Event.Event()
        self.display_item_removed_event = Event.Event()

    def __str__(self):
        return self.title

    def __validate_title(self, value):
        return str(value) if value is not None else str()

    def __validate_display_item_references(self, display_item_references):
        return list(collections.OrderedDict.fromkeys(display_item_references))

    def __property_changed(self, name, value):
        self.notify_property_changed(name)

    def connect_display_items(self, lookup_display_item):
        for data_group in self.data_groups:
            data_group.connect_display_items(lookup_display_item)
        for display_item_uuid in self.display_item_references:
            display_item = lookup_display_item(display_item_uuid)
            if display_item and display_item not in self.__display_items:
                self.__display_items.append(display_item)
        self.__get_display_item_by_uuid = lookup_display_item

    def disconnect_display_items(self):
        for data_group in self.data_groups:
            data_group.disconnect_display_items()
        self.__get_display_item_by_uuid = None

    def append_display_item(self, display_item):
        self.insert_display_item(len(self.__display_items), display_item)

    def insert_display_item(self, before_index, display_item):
        assert display_item not in self.__display_items
        assert display_item.uuid not in self.display_item_references
        self.__display_items.insert(before_index, display_item)
        self.display_item_inserted_event.fire(self, display_item, before_index, False)
        self.notify_insert_item("display_items", display_item, before_index)
        self.update_counted_display_items(collections.Counter([display_item]))
        display_item_references = self.display_item_references
        display_item_references.insert(before_index, display_item.uuid)
        self.display_item_references = display_item_references
        self.notify_property_changed("display_item_references")

    def remove_display_item(self, display_item):
        index = self.__display_items.index(display_item)
        self.__display_items.remove(display_item)
        self.subtract_counted_display_items(collections.Counter([display_item]))
        self.display_item_removed_event.fire(self, display_item, index, False)
        self.notify_remove_item("display_items", display_item, index)
        display_item_references = self.display_item_references
        display_item_references.remove(display_item.uuid)
        self.display_item_references = display_item_references
        self.notify_property_changed("display_item_references")

    @property
    def display_items(self):
        return tuple(self.__display_items)

    def append_data_group(self, data_group):
        self.insert_data_group(len(self.data_groups), data_group)

    def insert_data_group(self, before_index, data_group):
        self.insert_item("data_groups", before_index, data_group)
        if self.__get_display_item_by_uuid:
            data_group.connect_display_items(self.__get_display_item_by_uuid)
        self.notify_insert_item("data_groups", data_group, before_index)

    def remove_data_group(self, data_group):
        data_group.disconnect_display_items()
        index = self.data_groups.index(data_group)
        self.remove_item("data_groups", data_group)
        self.notify_remove_item("data_groups", data_group, index)

    # watch for insertions data_groups so that smart filters get updated.
    def __insert_data_group(self, name, before_index, data_group):
        self.update_counted_display_items(data_group.counted_display_items)

    # watch for removals and data_groups so that smart filters get updated.
    def __remove_data_group(self, name, index, data_group):
        self.subtract_counted_display_items(data_group.counted_display_items)

    @property
    def counted_display_items(self):
        return self.__counted_display_items

    def update_counted_display_items(self, counted_display_items):
        self.__counted_display_items.update(counted_display_items)

    def subtract_counted_display_items(self, counted_display_items):
        self.__counted_display_items.subtract(counted_display_items)
        self.__counted_display_items += collections.Counter()  # strip empty items


# return a generator for all data groups and child data groups in container
def get_flat_data_group_generator_in_container(container):
    for data_group in container.data_groups:
        yield data_group
        for child_data_group in get_flat_data_group_generator_in_container(data_group):
            yield child_data_group


# return a generator for all data items, child data items, and data items in child groups in container
def get_flat_display_item_generator_in_container(container):
    if hasattr(container, "display_items"):
        for display_item in container.display_items:
            yield display_item
    if hasattr(container, "data_groups"):
        for data_group in container.data_groups:
            for display_item in get_flat_display_item_generator_in_container(data_group):
                yield display_item


# Return the data_group matching name that is the descendent of the container.
def get_data_group_in_container_by_title(container, data_group_title):
    for data_group in container.data_groups:
        if data_group.title == data_group_title:
            return data_group
    return None


# Return the display_item matching name that is the descendent of the container.
def get_display_item_in_container_by_title(container, display_item_title):
    for display_item in container.display_items:
        if display_item.title == display_item_title:
            return display_item
    return None


# Return the data_group matching name that is the descendent of the container.
def get_data_group_in_container_by_uuid(container, data_group_uuid):
    for data_group in container.data_groups:
        if data_group.uuid == data_group_uuid:
            return data_group
    return None


# Return the display_item matching name that is the descendent of the container.
def get_display_item_in_container_by_uuid(container, display_item_uuid):
    for display_item in container.display_items:
        if display_item.uuid == display_item_uuid:
            return display_item
    return None


def data_group_factory(lookup_id):
    return DataGroup()
