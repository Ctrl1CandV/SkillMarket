"""自助借书机（节选）。和前台各写了一遍借书流程。"""
from datetime import date

import library as lib


def self_borrow(db_path, isbn, card):
    db = lib.open_db(db_path)
    book = lib.find_book(db, isbn)
    member = lib.find_member(db, card)
    if not lib.check_available(book):
        return False
    lib.mark_borrowed(book)
    today = date.today()
    lib.add_loan(db, isbn, card, today, lib.compute_due(today, member))
    lib.save_db(db, db_path)
    return True
