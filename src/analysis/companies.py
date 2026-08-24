"""Facts about the employers behind postings."""

from __future__ import annotations

import re
from urllib.parse import urlparse


# Applicant tracking hosts. A posting served from one of these says where the
# employer advertises, not who the employer is, so the domain has to come from
# the company name instead.
ATS_HOSTS = {
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "myworkdayjobs.com",
    "workable.com",
    "smartrecruiters.com",
    "bamboohr.com",
    "icims.com",
    "taleo.net",
    "breezy.hr",
    "recruitee.com",
}


def company_domain(company: str, source_urls: list[object]) -> str:
    """Best guess at an employer's own domain, used to look up a logo.

    A posting hosted on the employer's own careers page names the domain
    outright. Everything else is a guess from the name, which is right often
    enough to be worth showing and wrong quietly enough to fall back to a
    monogram when the logo does not resolve.
    """
    for url in source_urls:
        host = urlparse(str(url or "")).netloc.lower()
        host = host.removeprefix("www.")

        if not host:
            continue

        if any(host == ats or host.endswith(f".{ats}") for ats in ATS_HOSTS):
            continue

        return host

    slug = re.sub(r"[^a-z0-9]", "", company.lower())

    return f"{slug}.com" if slug else ""
