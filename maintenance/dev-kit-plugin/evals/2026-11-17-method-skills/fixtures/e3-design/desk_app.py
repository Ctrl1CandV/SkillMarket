"""前台借还书程序（节选）。"""
from datetime import date

import library as lib

DB = "books.json"


def borrow(isbn, member_id):
    db = lib.open_db(DB)
    book = lib.find_book(db, isbn)
    member = lib.find_member(db, member_id)
    if book is None or member is None:
        return "查无此书或此人"
    if lib.count_loans(db, member_id) >= 5:
        return "已借满 5 本"
    if not lib.check_available(book):
        return "已借完"
    lib.mark_borrowed(book)
    today = date.today()
    lib.add_loan(db, isbn, member_id, today, lib.compute_due(today, member))
    lib.save_db(db, DB)
    return "借书成功"


def give_back(isbn, member_id):
    db = lib.open_db(DB)
    book = lib.find_book(db, isbn)
    loan = lib.close_loan(db, isbn, member_id, date.today())
    if loan is None:
        return "没有这条借阅"
    lib.mark_returned(book)
    lib.save_db(db, DB)
    return "还书成功"
