from bs4 import BeautifulSoup
import os
import pandas as pd
import re
from math import prod

HTML_FILES = [
    "./tables/CVC. Plan Curricular del Instituto Cervantes. 9. Nociones específicas. Inventario. A1-A2.html",
    "./tables/CVC. Plan Curricular del Instituto Cervantes. 9. Nociones específicas. Inventario. B1-B2.html",
    "./tables/CVC. Plan Curricular del Instituto Cervantes. 9. Nociones específicas. Inventario. C1-C2.html",
]

HTML_DOCS = []
for hf in HTML_FILES:
    with open(hf, "rb") as f:
        HTML_DOCS.append(f.read())

COUNTS_SET = set()


def header_norm(header):
    if len(header) == 6:
        return header
    return header[0] + "0" + header[1:]


def chunk_breaker(chunk):
    global COUNTS_SET
    if "~" not in chunk:
        return [chunk]

    assert " ~ " in chunk
    subchunks = []
    for x in chunk.split(" ~ "):
        x = x.strip()
        if x[0] == "(" and x[-1] == ")":
            subchunks.append([f"({z})" for z in x[1:-1].split("/")])
        else:
            subchunks.append(x.split("/"))
    # subchunks = [x.split("/") for x in chunk.split(" ~ ")]
    max_count = max([len(x) for x in subchunks])
    new_chunks = [
        [x[min([i, len(x) - 1])] for x in subchunks] for i in range(max_count)
    ]
    new_chunks = [" ".join(x) for x in new_chunks]
    return new_chunks


def line_breaker(li):
    """Breaks lines into vocab"""
    li = li.replace("/ ", "/").strip()
    lines = li.splitlines()
    lines = [x.strip() for x in lines if not x.isspace() and not re.match("^\s+\\[", x)]
    chunks = sum([x.split(", ") for x in lines], [])
    chunks = sum([chunk_breaker(x) for x in chunks], [])
    chunks = [x for x in chunks if x is not None and not x.isspace()]
    return chunks


def acronym_proc(lipart):
    if lipart.name != "acronym":
        return lipart.text
    title = lipart.get("title")
    if title is None:
        return lipart.text
    return lipart.text + f" ({title})"


def process_table(table):
    tds = table.find("tbody").find("tr").find_all("td")
    caption = table.find("caption").text.split("\n")[0]
    raw_data = []
    for td in tds:
        if td.text.isspace():
            continue
        head = header_norm(td.get("headers")[0])
        ul = td.find("ul")
        if ul is None:
            continue
        lis = ul.find_all("li")
        lines = []
        for li in list(lis):

            lines.append("".join(acronym_proc(x) for x in list(li)))
        lines = sum([line_breaker(l) for l in lines], [])
        raw_data += [(head, l, caption) for l in lines]
    return pd.DataFrame(raw_data, columns=["header", "line", "caption"])

def verb_normer(vocab):
    vocab = vocab.replace("(se)","se")
    first = vocab.split(" ")[0]
    if len(first) < 3:
        return vocab
    verb_pat = "[aei]r(?:se)?$"
    if re.search(verb_pat, first) or first == "ir":
        return "a " + vocab
    return vocab

dfs = []
for html_doc in HTML_DOCS:
    soup = BeautifulSoup(html_doc, "html.parser")
    tables = soup.find(attrs={"id": "contenido"}).find(id="col1").find_all("table")
    dfs += [process_table(table) for table in tables]
df = pd.concat(dfs)
df["tag"] = df["header"].apply(lambda h: "DELE" + "::" + h[4:] + "::" + h[:4])
df["normed"] = df["line"].apply(verb_normer)
df = df.sort_values(by="tag")
df.reset_index(inplace=True, drop=True)
df.to_csv("ceres.csv")
print()
