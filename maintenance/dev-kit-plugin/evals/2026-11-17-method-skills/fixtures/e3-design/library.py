"""社区图书角的借阅数据层。数据放在一个 JSON 文件里。"""
import json
from datetime import date, timedelta


def open_db(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_db(db, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def find_book(db, isbn):
    for book in db["books"]:
        if book["isbn"] == isbn:
            return book
    return None


def find_member(db, member_id):
    for m in db["members"]:
        if m["id"] == member_id:
            return m
    return None


def count_loans(db, member_id):
    return sum(1 for r in db["loans"] if r["member"] == member_id and r["returned"] is None)


def check_available(book):
    return book["copies"] - book["on_loan"] > 0


def mark_borrowed(book):
    book["on_loan"] += 1


def mark_returned(book):
    book["on_loan"] -= 1


def compute_due(today, member):
    days = 30 if member["type"] == "teacher" else 14
    return today + timedelta(days=days)


def add_loan(db, isbn, member_id, today, due):
    db["loans"].append({"isbn": isbn, "member": member_id, "borrowed": today.isoformat(),
                        "due": due.isoformat(), "returned": None})


def close_loan(db, isbn, member_id, today):
    for r in db["loans"]:
        if r["isbn"] == isbn and r["member"] == member_id and r["returned"] is None:
            r["returned"] = today.isoformat()
            return r
    return None
