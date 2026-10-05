# -*- coding: utf-8 -*-
"""ERPNext API 客户端封装"""
import json
import requests
from urllib.parse import quote

BASE = "http://220.162.99.166:88"
TOKEN = "77455c7d4b3a8fe:432939a748243fd"


def q(name):
    """URL-encode docname for path usage"""
    return quote(str(name), safe="")


def _err(j):
    """提取服务端错误信息"""
    raw = j.get("_server_messages")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return raw[:400]
    msgs = []
    if isinstance(raw, list):
        for m in raw:
            try:
                d = json.loads(m) if isinstance(m, str) else m
                msgs.append(d.get("message", "") if isinstance(d, dict) else str(d))
            except Exception:
                msgs.append(str(m))
    exc = j.get("exception") or ""
    text = " | ".join(m for m in msgs if m)
    if exc:
        text = (text + " || " + str(exc))[:800]
    return text[:800] or json.dumps(j, ensure_ascii=False)[:400]


session = requests.Session()
session.headers.update({
    "Authorization": f"token {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
})


def check(r, what):
    if r.status_code != 200:
        j = {}
        try:
            j = r.json()
        except Exception:
            pass
        raise Exception(f"{what} HTTP {r.status_code}: {_err(j)}")
    return r.json()


def get_list(doctype, fields=None, filters=None, limit=0):
    params = {"limit_page_length": limit}
    if fields:
        params["fields"] = json.dumps(fields)
    if filters:
        params["filters"] = json.dumps(filters)
    r = session.get(f"{BASE}/api/resource/{q(doctype)}", params=params, timeout=60)
    return check(r, f"get_list {doctype}").get("data", [])


def get_doc(doctype, name):
    r = session.get(f"{BASE}/api/resource/{q(doctype)}/{q(name)}", timeout=60)
    return check(r, f"get_doc {doctype}/{name}")["data"]


def new_doc(doctype, data):
    r = session.post(f"{BASE}/api/resource/{q(doctype)}", json=data, timeout=120)
    return check(r, f"new {doctype}").get("data")


def set_doc(doctype, name, data):
    r = session.put(f"{BASE}/api/resource/{q(doctype)}/{q(name)}", json=data, timeout=120)
    return check(r, f"set {doctype}/{name}").get("data")


def submit_doc(doctype, name):
    """提交单据（docstatus 0 -> 1）：先取全量文档避免时间戳冲突"""
    doc = get_doc(doctype, name)
    return run_method("frappe.client.submit", doc=doc)


def cancel_doc(doctype, name):
    """取消单据（docstatus 1 -> 2）"""
    return run_method("frappe.client.cancel", doctype=doctype, name=name)


def run_method(method, **kwargs):
    r = session.post(f"{BASE}/api/method/{method}", json=kwargs, timeout=300)
    return check(r, f"method {method}")


def run_doc_method(method, doc, **kwargs):
    """运行文档级白名单方法（传入完整文档）"""
    r = session.post(f"{BASE}/api/method/frappe.handler.run_doc_method",
                     json={"method": method, "docs": doc, "args": kwargs}, timeout=300)
    return check(r, f"run_doc_method {method}")


def whitelisted(path, **kwargs):
    """调用白名单函数"""
    r = session.post(f"{BASE}/api/method/{path}", json=kwargs, timeout=300)
    return check(r, f"{path}")
