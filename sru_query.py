import sys
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


def search_sru(query, maximum_records=20):
    base_url = "https://sru.thuvienkhanhhoa.gov.vn/khanhhoa"
    params = {
        "operation": "searchRetrieve",
        "version": "1.1",
        "query": query,
        "recordSchema": "marcxml",
        "maximumRecords": str(maximum_records)
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'OpenClaw-SRU-Client/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
        return parse_marcxml(xml_data)
    except Exception as e:
        print(f"Error fetching SRU data: {e}", file=sys.stderr)
        return []


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
                "location": "",
                "summary": ""
            }
            
            # Control field 001 (ID)
            f001 = record.find('.//marc:controlfield[@tag="001"]', namespaces)
            if f001 is not None and f001.text:
                item["id"] = f001.text.strip()
                
            # Author 100 $a
            f100 = record.find('.//marc:datafield[@tag="100"]/marc:subfield[@code="a"]', namespaces)
            if f100 is not None and f100.text:
                item["author"] = clean_marc_text(f100.text)
                
            # Title 245 $a $b
            f245 = record.find('.//marc:datafield[@tag="245"]', namespaces)
            if f245 is not None:
                sub_a = f245.find('marc:subfield[@code="a"]', namespaces)
                sub_b = f245.find('marc:subfield[@code="b"]', namespaces)
                title_parts = []
                if sub_a is not None and sub_a.text:
                    title_parts.append(clean_marc_text(sub_a.text))
                if sub_b is not None and sub_b.text:
                    title_parts.append(clean_marc_text(sub_b.text))
                item["title"] = " ".join(title_parts)
                
            # Publisher / Year 260 $b $c
            f260 = record.find('.//marc:datafield[@tag="260"]', namespaces)
            if f260 is not None:
                sub_b = f260.find('marc:subfield[@code="b"]', namespaces)
                sub_c = f260.find('marc:subfield[@code="c"]', namespaces)
                if sub_b is not None and sub_b.text:
                    item["publisher"] = clean_marc_text(sub_b.text)
                if sub_c is not None and sub_c.text:
                    item["year"] = clean_marc_text(sub_c.text)
                    
            # Price 020 $c
            f020 = record.find('.//marc:datafield[@tag="020"]/marc:subfield[@code="c"]', namespaces)
            if f020 is not None and f020.text:
                item["price"] = clean_marc_text(f020.text)
                
            # Location 852 $b $c
            f852 = record.find('.//marc:datafield[@tag="852"]', namespaces)
            if f852 is not None:
                sub_b = f852.find('marc:subfield[@code="b"]', namespaces)
                sub_c = f852.find('marc:subfield[@code="c"]', namespaces)
                loc_parts = []
                if sub_b is not None and sub_b.text:
                    loc_parts.append(clean_marc_text(sub_b.text))
                if sub_c is not None and sub_c.text:
                    loc_parts.append(clean_marc_text(sub_c.text))
                item["location"] = " / ".join(loc_parts)

            # Summary 520 $a
            f520 = record.find('.//marc:datafield[@tag="520"]', namespaces)
            if f520 is not None:
                sub_a = f520.find('marc:subfield[@code="a"]', namespaces)
                if sub_a is not None and sub_a.text:
                    item["summary"] = clean_marc_text(sub_a.text)

            results.append(item)
    except Exception as e:
        print(f"Error parsing MARCXML: {e}", file=sys.stderr)
        
    return results


def main():
    parser = argparse.ArgumentParser(description="Query Khanh Hoa Provincial Library SRU catalog.")
    parser.add_argument("query", help="CQL query or search term (e.g. 'python' or 'dc.title=\"python\"')")
    parser.add_argument("--author", help="Optional author name filter")
    parser.add_argument("--title", help="Optional title filter")
    parser.add_argument("--limit", type=int, default=20, help="Max records to return")
    
    args = parser.parse_args()
    
    cql_query = args.query
    if args.author:
        cql_query += f' AND dc.creator="{args.author}"'
    if args.title:
        cql_query += f' AND dc.title="{args.title}"'
        
    # If query is a plain keyword without field, wrap in dc.title
    if "=" not in cql_query and " AND " not in cql_query and " OR " not in cql_query:
        cql_query = f'dc.title="{cql_query}"'
        
    records = search_sru(cql_query, args.limit)
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()