#!/usr/bin/env python

import argparse
import pandas as pd
import requests
from rcsbapi.search import NestedAttributeQuery, AttributeQuery, search_attributes as attrs

def parse_args():
    parser = argparse.ArgumentParser(description="Query RCSB PDB entries by UniProt accession")
    parser.add_argument("-u", "--uniprot", required=True, help="UniProt accession (e.g., P09619)")
    parser.add_argument("--method", default=None, help="Experimental method filter (e.g., X-RAY DIFFRACTION)")
    parser.add_argument("--resolution", type=float, default=None, help="Resolution cutoff (e.g., 3.0)")
    parser.add_argument("--limit", type=int, default=20, help="Number of PDB IDs to preview")
    return parser.parse_args()

def get_pdb_ids_via_search(args):
    """使用 Search API 快速筛选符合条件的 PDB ID"""
    # 使用 NestedAttributeQuery 解决 400 错误
    q_uniprot = NestedAttributeQuery(
        AttributeQuery(
            attribute="rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
            operator="exact_match",
            value=args.uniprot
        ),
        AttributeQuery(
            attribute="rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_name",
            operator="exact_match",
            value="UniProt"
        )
    )
    
    # 组合筛选条件
    q = q_uniprot & (attrs.rcsb_entry_info.structure_determination_methodology == "experimental")
    
    if args.method:
        q = q & (attrs.exptl.method == args.method)
    if args.resolution:
        q = q & (attrs.rcsb_entry_info.resolution_combined < args.resolution)
        
    return list(q())

def get_details_via_rest_api(pdb_ids):
    """【精简版】使用 RCSB REST API 仅获取 Release Date 和 Method"""
    table_data = []
    
    for pdb_id in pdb_ids:
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception:
            continue
            
        # 1. 提取 Release Date
        release_date = data.get("rcsb_accession_info", {}).get("initial_release_date", "N/A")
        if release_date != "N/A":
            release_date = release_date.split("T")[0] # 格式化为 YYYY-MM-DD
            
        # 2. 提取 Method
        exptl_list = data.get("exptl", [])
        method = exptl_list[0].get("method", "N/A") if exptl_list else "N/A"
        
        table_data.append({
            "PDB Code": pdb_id,
            "Released Date": release_date,
            "Method": method
        })
        
    return table_data

def main():
    args = parse_args()
    print(f"🔍 Searching PDB entries for UniProt ID: {args.uniprot}...")
    
    # 1. 获取 PDB ID 列表
    try:
        pdb_ids = get_pdb_ids_via_search(args)
    except Exception as e:
        print(f"❌ Search API 查询失败: {e}")
        return
    
    print(f"\n✅ Total PDB entries found: {len(pdb_ids)}")
    print(f"Preview (first {args.limit}): {pdb_ids[:args.limit]}\n")
    
    if not pdb_ids:
        return

    # 2. 获取详细信息
    print("📊 Fetching details via REST API...")
    table_data = get_details_via_rest_api(pdb_ids)
    
    if table_data:
        df = pd.DataFrame(table_data)
        # 按照 Released Date 降序排列（最新的在前面）
        df = df.sort_values(by="Released Date", ascending=False, na_position='last')
        
        print("\n" + "="*70)
        print(df.to_string(index=False))
        print("="*70 + "\n")
    else:
        print("⚠️ Could not retrieve details.")

if __name__ == "__main__":
    main()
