import os, json
from record import Record

WISHLIST_PATH = "wishlist.json"
LIBRARY_PATH = "library.json"

class Database:
    def __init__(self):
        if os.path.exists(WISHLIST_PATH) and os.path.getsize(WISHLIST_PATH) > 0:
            with open(WISHLIST_PATH, "r", encoding="utf-8") as f:
                self.wishlist = set([Record(*(val.split("/"))) for val in json.load(f)])
        else :
            self.wishlist = set([])

        if os.path.exists(LIBRARY_PATH) and os.path.getsize(LIBRARY_PATH) > 0:
            with open(LIBRARY_PATH, "r", encoding="utf-8") as f:
                self.library = set([Record(*(val.split("/"))) for val in json.load(f)])
        else :
            self.library = set([])

    def add_to_wishlist(self, record: Record):
        self.wishlist.add(record)

    def remove_from_wishlist(self, record: Record):
        self.wishlist.remove(record)

    def add_to_library(self, record: Record, rating):
        if record in self.wishlist:
            self.remove_from_wishlist(record)
        record.rate(rating)
        self.library.add(record)

    def remove_from_library(self, record: Record):
        record.rate(None)
        self.library.remove(record)

    def clear_library(self):
        self.library = []

    def clear_wishlist(self):
        self.wishlist = []

    def clear_all(self):
        self.library = []
        self.wishlist = []

    def save(self):
        for path, var in zip([WISHLIST_PATH, LIBRARY_PATH], [self.wishlist, self.library]):
            with open(path, "w", encoding="utf-8") as f:
                json.dump([str(val) for val in var], f, indent=4)
