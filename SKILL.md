---
name: "sru-query"
description: "Query Khánh Hòa Provincial Library SRU catalog via CQL and output structured JSON records"
---

# SRU Library Query Skill

## Overview
Enable querying the Khánh Hòa Provincial Library SRU service via CQL (Common Query Language) to search for books, articles, and other resources at https://sru.thuvienkhanhhoa.gov.vn.

## Prerequisites
- Access to https://sru.thuvienkhanhhoa.gov.vn
- Basic understanding of CQL syntax

## Usage

### Primary Function: `sru_search`
```
openclaw skills invoke sru_query --query "python"
```

#### Parameters
- `query`: search term (required)
- `author`: optional, author name
- `title`: optional, specific title keywords
- `subject`: optional, subject/keywords
- `limit`: optional, max results (default 10)
- `start`: optional, result offset for pagination

### 1. Search by Keyword
```
sru_search "python"
sru_search "lập trình python"
sru_search "Python for kids"
```

### 2. Search by Title
```
sru_search "Python for kids" title:"Python for kids"
```

### 3. Advanced CQL Queries

#### Find books on specific subjects
```
sru_search "ngôn ngữ lập trình" subject:"ngôn ngữ python"
sru_search "lập trình web" subject:"lập trình web"
```

### 4. Direct SRU URL Examples (Working)
```
https://sru.thuvienkhanhhoa.gov.vn/khanhhoa?operation=searchRetrieve&version=1.1&query=dc.title%3D%22python%22&recordSchema=marcxml&maximumRecords=10

https://sru.thuvienkhanhhoa.gov.vn/khanhhoa?operation=searchRetrieve&version=1.1&query=dc.title%3D%22L%E1%BA%ADp+tr%C3%ACnh+Web+v%E1%BB%9Bi+Python%22&recordSchema=marcxml&maximumRecords=5
```

## Implementation Details
- Uses CQL/SRU protocol standard (Z39.50) with YAZ backend
- SRU service responds with XML (typically MARC21)
- Returns parsed results: title, author, year, publisher, description
- Handles pagination via `startRecord` parameter
- Supports XML parsing into readable JSON

## Error Handling
- Invalid CQL → returns error message, suggests valid syntax
- Service unavailable → retries with exponential backoff (3 retries)
- No results → returns empty array with helpful message
- Malformed response → logs raw response for debugging

## Integration
Call via `openclaw skills invoke sru_query --query "search terms"` or integrate into applications needing library catalog access to Khánh Hòa Provincial Library.

## Functions
1. **sru_search**: Main search function with query parameters
2. **sru_get_record**: Retrieve specific record by ID
3. **sru_explain**: Get service configuration/metadata
