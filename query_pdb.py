#!/usr/bin/env python

import argparse
# 修改1: 将导入语句从 rcsbsearchapi 改为 rcsb-api 的 search 模块
from rcsbapi.search import search_attributes as attrs


def parse_args():
    parser = argparse.ArgumentParser(
        description="Query RCSB PDB entries by UniProt accession"
    )
    parser.add_argument(
        "-u", "--uniprot",
        required=True,
        help="UniProt accession (e.g., P00533)"
    )
    parser.add_argument(
        "--method",
        default=None,
        help="Experimental method filter (e.g., X-RAY DIFFRACTION, ELECTRON MICROSCOPY)"
    )
    parser.add_argument(
        "--resolution",
        type=float,
        default=None,
        help="Resolution cutoff (e.g., 3.0)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of PDB IDs to preview"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # 【无需修改】属性路径遵循 RCSB PDB 官方标准 Schema，在 rcsb-api 中保持一致
    # UniProt query
    q = (
        attrs.rcsb_polymer_entity_container_identifiers
        .reference_sequence_identifiers.database_accession == args.uniprot
    )

    # experimental only
    q = q & (attrs.rcsb_entry_info.structure_determination_methodology == "experimental")

    # method filter
    if args.method:
        q = q & (attrs.exptl.method == args.method)

    # resolution filter
    if args.resolution:
        q = q & (attrs.rcsb_entry_info.resolution_combined < args.resolution)

    # execute query
    # 修改2. 在 rcsb-api 中，list(q()) 依然有效，也可以使用 q.exec()
    pdb_ids = list(q())

    print(f"Total PDB entries: {len(pdb_ids)}")
    print(f"Preview (first {args.limit}):")
    print(pdb_ids[:args.limit])


if __name__ == "__main__":
    main()
