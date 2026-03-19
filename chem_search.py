from rcsbsearchapi.search import ChemSimilarityQuery

# Query with type = descriptor, descriptor type = SMILES, match type = similar ligands (sterospecific) or graph-relaxed-stereo
q2 = ChemSimilarityQuery(value="Cc1c(sc[n+]1Cc2cnc(nc2N)C)CCO",
                         query_type="descriptor",
                         descriptor_type="SMILES",
                         match_type="graph-relaxed-stereo")
print(list(q2()))
