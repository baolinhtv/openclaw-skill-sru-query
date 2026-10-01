import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import json
import argparse

def clean_marc_text(text):
    """Xóa bỏ các dấu câu chuẩn ISBD còn sót lại ở cuối chuỗi trong MARC21"""
    if not text:
        return ""
    return text.strip().rstrip(" /:;,.")

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
            sleep_time = backoff_factor ** attempt
            time.sleep(sleep_time)

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
                "author": "",
                "publisher": "",
                "year": "",
                "price": "",
                "locations": []
            }
            
            # 1. ID (001)
            f001 = record.find('.//marc:controlfield[@tag="001"]', namespaces)
            if f001 is not None and f001.text:
                item["id"] = f001.text.strip()
                
            # 2. Tác giả (100 $a hoặc fallback 110/700 nếu cần)
            f100_a = record.find('.//marc:datafield[@tag="100"]/marc:subfield[@code="a"]', namespaces)
            if f100_a is not None and f100_a.text:
                item["author"] = clean_marc_text(f100_a.text)
                
            # 3. Nhan đề (245 $a, $b)
            f245 = record.find('.//marc:datafield[@tag="245"]', namespaces)
            if f245 is not None:
                sub_a = f245.find('marc:subfield[@code="a"]', namespaces)
                sub_b = f245.find('marc:subfield[@code="b"]', namespaces)
                title_parts = []
                if sub_a is not None and sub_a.text:
                    title_parts.append(clean_marc_text(sub_a.text))
                if sub_b is not None and sub_b.text:
                    title_parts.append(clean_marc_text(sub_b.text))
                item["title"] = " - ".join(title_parts) if len(title_parts) > 1 else "".join(title_parts)
                
            # 4. Nhà xuất bản & Năm (Hỗ trợ cả chuẩn 260 và chuẩn mới 264)
            f26x = record.find('.//marc:datafield[@tag="260"]', namespaces) or record.find('.//marc:datafield[@tag="264"]', namespaces)
            if f26x is not None:
                sub_b = f26x.find('marc:subfield[@code="b"]', namespaces)
                sub_c = f26x.find('marc:subfield[@code="c"]', namespaces)
                if sub_b is not None and sub_b.text:
                    item["publisher"] = clean_marc_text(sub_b.text)
                if sub_c is not None and sub_c.text:
                    item["year"] = clean_marc_text(sub_c.text)
                    
            # 5. Giá tiền (020 $c)
            f020_c = record.find('.//marc:datafield[@tag="020"]/marc:subfield[@code="c"]', namespaces)
            if f020_c is not None and f020_c.text:
                item["price"] = clean_marc_text(f020_c.text)
                
            # 6. Vị trí kho (Lấy tất cả các thẻ 852 lặp lại)
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
    parser.add_argument("query", help="CQL query or search term (e.g. 'python' or 'dc.title=\"python\"')")
    parser.add_argument("--author", help="Optional author name filter")
    parser.add_argument("--title", help="Optional title filter")
    parser.add_argument("--limit", type=int, default=10, help="Max records to return")
    
    args = parser.parse_args()
    
    # 1. Chuẩn hóa query chính trước nếu là từ khóa thông thường
    raw_query = args.query.strip()
    if "=" not in raw_query and not any(op in raw_query for op in [" AND ", " OR ", " NOT "]):
        cql_query = f'dc.title="{raw_query}"'
    else:
        cql_query = raw_query
        
    # 2. Ghép thêm các điều kiện bổ trợ
    if args.author:
        cql_query += f' AND dc.creator="{args.author.strip()}"'
    if args.title:
        cql_query += f' AND dc.title="{args.title.strip()}"'
        
    records = search_sru(cql_query, args.limit)
    print(json.dumps(records, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
