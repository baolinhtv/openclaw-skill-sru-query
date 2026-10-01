---
name: "tvkh-sru-query"
description: "Query Khánh Hòa Provincial Library SRU catalog via CQL and output structured JSON records"
---

# SRU Library Query Skill

## Overview
Enable querying the Khánh Hòa Provincial Library SRU service via CQL (Common Query Language) to search for books, articles, and other resources at https://sru.thuvienkhanhhoa.gov.vn. The SRU endpoint (`/khanhhoa`) runs on top of the **Zebra** search and indexing engine, successfully modernizing and expanding upon the library's traditional **Z39.50** bibliographic protocol infrastructure.

## Installation
```bash
openclaw skills install @baolinhtv/tvkh-sru-query
```
*(Or via Git: `openclaw skills install https://github.com/baolinhtv/openclaw-skill-sru-query.git`)*

## Prerequisites
- Access to https://sru.thuvienkhanhhoa.gov.vn
- Basic understanding of CQL syntax

## Usage

### Primary Function: `sru_query.py` CLI
```bash
python3 sru_query.py "python"
python3 sru_query.py "tháp bà ponagar" --limit 10
python3 sru_query.py "Tô Hoài" --author "Tô Hoài"
```

#### Parameters
- `query`: search term or raw CQL query (required)
- `author`: optional, author name filter (`dc.creator`)
- `title`: optional, specific title keywords (`dc.title`)
- `limit`: optional, max records to return (default 20)

### CQL Query Syntax Examples

#### 1. Search by Keyword (Contains all words)
```text
dc.title all "lập trình python"
dc.title all "tháp bà ponagar"
```

#### 2. Search by Specific Field
- By Author: `dc.creator="Tô Hoài"`
- By Title Phrase: `dc.title="Discovering calculus"`
- By Subject: `dc.subject all "du lịch"`

#### 3. Combined / Advanced Queries
```text
dc.title all "python" AND dc.creator="Shaw"
dc.subject all "lịch sử" AND dc.title all "Khánh Hòa"
```

### Direct SRU URL Examples (Working)
```text
[https://sru.thuvienkhanhhoa.gov.vn/khanhhoa?operation=searchRetrieve&version=1.1&query=dc.title+all+%22th%C3%A1p+b%C3%A0%22&recordSchema=marcxml&maximumRecords=10](https://sru.thuvienkhanhhoa.gov.vn/khanhhoa?operation=searchRetrieve&version=1.1&query=dc.title+all+%22th%C3%A1p+b%C3%A0%22&recordSchema=marcxml&maximumRecords=10)

[https://sru.thuvienkhanhhoa.gov.vn/khanhhoa?operation=searchRetrieve&version=1.1&query=dc.title%3D%22python%22&recordSchema=marcxml&maximumRecords=10](https://sru.thuvienkhanhhoa.gov.vn/khanhhoa?operation=searchRetrieve&version=1.1&query=dc.title%3D%22python%22&recordSchema=marcxml&maximumRecords=10)
```

## Output Data Structure (JSON)
The skill parses raw MARC21 XML into clean, AI-ready JSON objects:
```json
[
  {
    "id": "801",
    "title": "Discovering calculus with mathematica",
    "author": "Evans, Benny, Jonson, Jerry, Knoll, Cecilia A., Shaw, Michael D.",
    "authors": [
      "Evans, Benny",
      "Jonson, Jerry",
      "Knoll, Cecilia A.",
      "Shaw, Michael D."
    ],
    "publisher": "John Wiley & Sons",
    "year": "1995",
    "call_number": "515 D313C",
    "price": "52000đ",
    "location": "Kho mở / Kho tiếng Anh",
    "locations": [
      "Kho mở / Kho tiếng Anh"
    ],
    "summary": ""
  }
]
```

## Implementation Details
- Uses CQL/SRU protocol standard (Z39.50) with YAZ/Zebra backend.
- Fetches MARC21 XML schema (`recordSchema=marcxml`).
- Robust metadata extraction:
  - Handles primary authors (`100`), co-authors/contributors (`700`), and statement of responsibility (`245$c`).
  - Supports modern RDA publishing statements (`264`) and traditional imprint (`260`).
  - Cleans ISBD punctuation and normalizes publication years.
  - Aggregates multiple shelf locations (`852`) and DDC call numbers (`082`).
- Retries with exponential backoff (3 attempts) on network/server hiccups.
