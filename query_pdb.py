#!/usr/bin/env python3

import argparse
from rcsbsearchapi import rcsb_attributes as attrs


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
    pdb_ids = list(q())

    print(f"Total PDB entries: {len(pdb_ids)}")
    print(f"Preview (first {args.limit}):")
    print(pdb_ids[:args.limit])


if __name__ == "__main__":
    main()
