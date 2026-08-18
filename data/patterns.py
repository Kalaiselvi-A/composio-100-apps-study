# -*- coding: utf-8 -*-
"""
Turns the 100-row dataset into the aggregate findings shown on the case
study page. No API key needed to run this -- it's pure analysis over
apps.py. Run: python3 patterns.py
"""
import json
from collections import Counter, defaultdict
from apps import APPS

def norm_auth_bucket(auth_list):
    s = " ".join(auth_list).lower()
    if "oauth2" in s and ("key" in s or "token" in s or "basic" in s):
        return "OAuth2 + API key (either)"
    if "oauth2" in s:
        return "OAuth2 only"
    if "basic" in s and "key" not in s:
        return "Basic auth"
    if "key" in s or "token" in s:
        return "API key / token only"
    if "unclear" in s or not auth_list:
        return "Unclear / not found"
    return "Other"

def main():
    total = len(APPS)
    auth_counter = Counter(norm_auth_bucket(a["auth"]) for a in APPS)
    access_counter = Counter(a["access"] for a in APPS)
    verdict_counter = Counter(a["verdict"] for a in APPS)
    mcp_counter = Counter(a["mcp"].split(" ")[0] for a in APPS)  # official/community/preview/none

    by_category = defaultdict(lambda: Counter())
    for a in APPS:
        by_category[a["category"]][a["access"]] += 1

    # blocker text mining -- rough clustering by keyword
    blocker_kw = Counter()
    for a in APPS:
        b = a["blocker"].lower()
        if not b:
            continue
        if "paid" in b or "no free" in b:
            blocker_kw["requires a paid plan"] += 1
        if "review" in b or "approval" in b:
            blocker_kw["needs app/partner review"] += 1
        if "sales" in b or "contact-sales" in b or "enterprise" in b:
            blocker_kw["sales-led / enterprise-only onboarding"] += 1
        if "not found" in b or "could not locate" in b or "no public" in b:
            blocker_kw["no public API located"] += 1
        if "not" in b and "toolkit" in b:
            blocker_kw["not toolkit-shaped (CLI/local tool)"] += 1
        if "customer" in b and "onboard" in b:
            blocker_kw["must already be a paying customer"] += 1

    confidence_counter = Counter(a["confidence"] for a in APPS)

    out = dict(
        total=total,
        auth=dict(auth_counter),
        access=dict(access_counter),
        verdict=dict(verdict_counter),
        mcp=dict(mcp_counter),
        by_category={k: dict(v) for k, v in by_category.items()},
        blocker_clusters=dict(blocker_kw),
        confidence=dict(confidence_counter),
    )
    print(json.dumps(out, indent=2))
    return out

if __name__ == "__main__":
    main()
