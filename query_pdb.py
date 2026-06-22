#!/usr/bin/env python

import argparse
import pandas as pd
import requests
from rcsbapi.search import NestedAttributeQuery, AttributeQuery, search_attributes as attrs

def parse_args():
    parser = argparse.ArgumentParser(description="Query RCSB PDB entries by UniProt accession")
    parser.add_argument("-u", "--uniprot", required=True, help="UniProt accession (e.g., P00533)")
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

def _query_graphql_batch(pdb_ids_batch, uniprot_ac):
    """对一批 PDB ID 执行 GraphQL 查询，返回 table_data 列表"""
    entry_queries = []
    for pid in pdb_ids_batch:
        entry_queries.append(f'''
    e_{pid}: entry(entry_id: "{pid}") {{
      rcsb_accession_info {{ initial_release_date }}
      exptl {{ method }}
      polymer_entities {{
        entity_poly {{ pdbx_strand_id }}
        rcsb_polymer_entity_container_identifiers {{
          reference_sequence_identifiers {{
            database_name
            database_accession
          }}
        }}
        rcsb_polymer_entity_align {{
          reference_database_name
          reference_database_accession
          aligned_regions {{
            entity_beg_seq_id
            ref_beg_seq_id
            length
          }}
        }}
      }}
    }}''')

    query = "{\n" + "\n".join(entry_queries) + "\n}"

    url = "https://data.rcsb.org/graphql"
    try:
        resp = requests.post(url, json={"query": query}, timeout=60)
        if resp.status_code != 200:
            raise Exception(f"GraphQL returned {resp.status_code}")
        data = resp.json()
    except Exception as e:
        print(f"  GraphQL batch query failed: {e}")
        return []

    if "errors" in data:
        print(f"  GraphQL errors: {data['errors'][:2]}")

    table_data = []
    for pdb_id in pdb_ids_batch:
        key = f"e_{pdb_id}"
        entry = data.get("data", {}).get(key)
        if not entry:
            continue

        release_date = entry.get("rcsb_accession_info", {}).get("initial_release_date", "N/A")
        if release_date != "N/A":
            release_date = release_date.split("T")[0]

        exptl_list = entry.get("exptl") or []
        method = exptl_list[0].get("method", "N/A") if exptl_list else "N/A"

        chain_parts = []
        for entity in (entry.get("polymer_entities") or []):
            rci = entity.get("rcsb_polymer_entity_container_identifiers") or {}
            ref_ids = rci.get("reference_sequence_identifiers") or []
            matches_target = any(
                r.get("database_name") == "UniProt" and r.get("database_accession") == uniprot_ac
                for r in ref_ids
            )
            if not matches_target:
                continue

            chains = (entity.get("entity_poly") or {}).get("pdbx_strand_id", "N/A")

            for align in (entity.get("rcsb_polymer_entity_align") or []):
                if align.get("reference_database_name") == "UniProt" and align.get("reference_database_accession") == uniprot_ac:
                    for region in (align.get("aligned_regions") or []):
                        ref_beg = region.get("ref_beg_seq_id", "?")
                        ref_len = region.get("length", 0)
                        ref_end = ref_beg + ref_len - 1 if isinstance(ref_beg, int) and ref_len else "?"
                        chain_parts.append(f"{chains}({ref_beg}-{ref_end})")

        chain_info = "; ".join(chain_parts) if chain_parts else "N/A"

        table_data.append({
            "PDB Code": pdb_id,
            "Released Date": release_date,
            "Method": method,
            "Chain(s) [UniProt range]": chain_info
        })

    return table_data


def get_details_via_graphql(pdb_ids, uniprot_ac, batch_size=10):
    """分批使用 RCSB GraphQL API 获取详细信息"""
    all_data = []
    total = len(pdb_ids)
    for i in range(0, total, batch_size):
        batch = pdb_ids[i:i + batch_size]
        print(f"  Fetching batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size} ({len(batch)} entries)...")
        batch_data = _query_graphql_batch(batch, uniprot_ac)
        all_data.extend(batch_data)
    return all_data

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

    # 2. 获取详细信息（仅获取前 limit 个）
    print(f"📊 Fetching details via GraphQL API (first {args.limit})...")
    table_data = get_details_via_graphql(pdb_ids[:args.limit], args.uniprot)

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
