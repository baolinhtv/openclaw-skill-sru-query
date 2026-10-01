import sys
import time
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import json
import argparse

def clean_marc_text(text):
    """Xóa bỏ các ký tự phân cách chuẩn ISBD còn sót lại ở hai đầu chuỗi"""
    if not text:
        return ""
    return text.strip().strip(" /:;,.")

def clean_year(year_text):
    """Trích xuất 4 chữ số năm từ các chuỗi như 'c1995.', '[2020]', '1998'"""
    if not year_text:
        return ""
    match = re.search(r'\b(19\d{2}|20\d{2})\b', year_text)
    return match.group(0) if match else clean_marc_text(year_text)

def search_sru(query, maximum_records=10, retries=3, backoff_factor=1.5):
    base_url = "https://sru.thuvienkhanhhoa.gov.vn/khanhhoa"
    params = {
        "operation": "searchRetrieve",
        "version": "1.1",
        "query": query,
        "recordSchema": "marcxml",
        "maximumRecords": str(maximum_records)
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'OpenClaw-SRU-Client/1.0'})
    
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_data = response.read()
            return parse_marcxml(xml_data)
        except Exception as e:
            if attempt == retries:
                print(f"Error fetching SRU data (Attempt {attempt}/{retries}): {e}", file=sys.stderr)
                return []
            time.sleep(backoff_factor ** attempt)

def parse_marcxml(xml_bytes):
    results = []
    try:
        root = ET.fromstring(xml_bytes)
        namespaces = {
            'zs': 'http://www.loc.gov/zing/srw/',
            'marc': 'http://www.loc.gov/MARC21/slim'
        }
        
        records = root.findall('.//marc:record', namespaces)
        if not records:
            records = root.findall('.//{http://www.loc.gov/MARC21/slim}record')
            
        for record in records:
            item = {
                "id": "",
                "title": "",
                "authors": [],
                "publisher": "",
                "year": "",
                "call_number": "",
                "price": "",
                "locations": []
            }
            
            # 1. Mã biểu ghi (001)
            f001 = record.find('.//marc:controlfield[@tag="001"]', namespaces)
            if f001 is not None and f001.text:
                item["id"] = f001.text.strip()
                
            # 2. Tác giả: Kiểm tra 100, sau đó quét toàn bộ 700 (tác giả phụ/đồng tác giả)
            authors = []
            f100_a = record.find('.//marc:datafield[@tag="100"]/marc:subfield[@code="a"]', namespaces)
            if f100_a is not None and f100_a.text:
                authors.append(clean_marc_text(f100_a.text))
                
            for f700 in record.findall('.//marc:datafield[@tag="700"]', namespaces):
                sub_a = f700.find('marc:subfield[@code="a"]', namespaces)
                if sub_a is not None and sub_a.text:
                    author_name = clean_marc_text(sub_a.text)
                    if author_name not in authors:
                        authors.append(author_name)
            item["authors"] = authors

            # 3. Nhan đề & Thông tin trách nhiệm (245 $a, $b, $c)
            f245 = record.find('.//marc:datafield[@tag="245"]', namespaces)
            if f245 is not None:
                sub_a = f245.find('marc:subfield[@code="a"]', namespaces)
                sub_b = f245.find('marc:subfield[@code="b"]', namespaces)
                sub_c = f245.find('marc:subfield[@code="c"]', namespaces)
                
                title_parts = []
                if sub_a is not None and sub_a.text:
                    title_parts.append(clean_marc_text(sub_a.text))
                if sub_b is not None and sub_b.text:
                    title_parts.append(clean_marc_text(sub_b.text))
                item["title"] = " - ".join(title_parts) if len(title_parts) > 1 else "".join(title_parts)
                
                # Nếu không có thẻ 100/700, fallback dùng thông tin trách nhiệm ở 245$c
                if not item["authors"] and sub_c is not None and sub_c.text:
                    item["authors"] = [clean_marc_text(sub_c.text)]
                
            # 4. Phân loại DDC / Số xếp giá (082 $a $b)
            f082 = record.find('.//marc:datafield[@tag="082"]', namespaces)
            if f082 is not None:
                sub_a = f082.find('marc:subfield[@code="a"]', namespaces)
                sub_b = f082.find('marc:subfield[@code="b"]', namespaces)
                ddc_parts = []
                if sub_a is not None and sub_a.text:
                    ddc_parts.append(clean_marc_text(sub_a.text))
                if sub_b is not None and sub_b.text:
                    ddc_parts.append(clean_marc_text(sub_b.text))
                item["call_number"] = " ".join(ddc_parts)

            # 5. Xuất bản (260 hoặc 264)
            f26x = record.find('.//marc:datafield[@tag="260"]', namespaces) or record.find('.//marc:datafield[@tag="264"]', namespaces)
            if f26x is not None:
                sub_b = f26x.find('marc:subfield[@code="b"]', namespaces)
                sub_c = f26x.find('marc:subfield[@code="c"]', namespaces)
                if sub_b is not None and sub_b.text:
                    item["publisher"] = clean_marc_text(sub_b.text)
                if sub_c is not None and sub_c.text:
                    item["year"] = clean_year(sub_c.text)
                    
            # 6. Giá tiền (020 $c)
            f020_c = record.find('.//marc:datafield[@tag="020"]/marc:subfield[@code="c"]', namespaces)
            if f020_c is not None and f020_c.text:
                item["price"] = clean_marc_text(f020_c.text)
                
            # 7. Vị trí kho (852 $b $c)
            for f852 in record.findall('.//marc:datafield[@tag="852"]', namespaces):
                sub_b = f852.find('marc:subfield[@code="b"]', namespaces)
                sub_c = f852.find('marc:subfield[@code="c"]', namespaces)
                loc_parts = []
                if sub_b is not None and sub_b.text:
                    loc_parts.append(clean_marc_text(sub_b.text))
                if sub_c is not None and sub_c.text:
                    loc_parts.append(clean_marc_text(sub_c.text))
                if loc_parts:
                    loc_str = " / ".join(loc_parts)
                    if loc_str not in item["locations"]:
                        item["locations"].append(loc_str)

            results.append(item)
    except Exception as e:
        print(f"Error parsing MARCXML: {e}", file=sys.stderr)
        
    return results

def main():
    parser = argparse.ArgumentParser(description="Query Khanh Hoa Provincial Library SRU catalog.")
    parser.add_argument("query", help="CQL query or search term (e.g. 'calculus' or 'dc.title=\"calculus\"')")
    parser.add_argument("--author", help="Optional author name filter")
    parser.add_argument("--title", help="Optional title filter")
    parser.add_argument("--limit", type=int, default=10, help="Max records to return")
    
    args = parser.parse_args()
    
    raw_query = args.query.strip()
    if "=" not in raw_query and not any(op in raw_query for op in [" AND ", " OR ", " NOT "]):
        cql_query = f'dc.title="{raw_query}"'
    else:
        cql_query = raw_query
        
    if args.author:
        cql_query += f' AND dc.creator="{args.author.strip()}"'
    if args.title:
        cql_query += f' AND dc.title="{args.title.strip()}"'
        
    records = search_sru(cql_query, args.limit)
    print(json.dumps(records, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
