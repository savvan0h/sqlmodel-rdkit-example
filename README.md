# SQLModel/RDKit database cartridge integration
This repo demonstrates how to integrate [SQLModel](https://sqlmodel.tiangolo.com/) with [the RDKit database cartridge](https://www.rdkit.org/docs/Cartridge.html) in the simplest way possible.  
You may want to check out an existing solution like [razi](https://github.com/rvianello/razi), but it requires some modifications to work with SQLModel at the time of writing, such as updating similarity search operators and result value processing.

## Requirements
PostgreSQL with the RDKit extension, which is not included in this repo, must use the same version of RDKit as the one in the Python environment (See [pyproject.toml](pyproject.toml)).

## Exact structure search( `@=` )

* Python

```python
statement = select(Compound).where(Compound.molecule == "COC(c1ccccc1)c1ccccc1") # value can be a mol object
results = session.execute(statement)
```

* SQL

```sql
SELECT compoundstructure.id, compoundstructure.name, mol_to_pkl(compoundstructure.molecule) AS molecule, bfp_to_binary_text(compoundstructure.mfp2) AS mfp2
FROM compoundstructure
WHERE compoundstructure.molecule @= mol_from_pkl(:molecule_1)
```

## Substructure search
### hassubstruct( `@>` )

* Python

```python
statement = select(Compound).where(Compound.molecule.hassubstruct("C1=C(C)C=CC=C1"))
results = session.execute(statement)
```

* SQL

```sql
SELECT compoundstructure.id, compoundstructure.name, mol_to_pkl(compoundstructure.molecule) AS molecule, bfp_to_binary_text(compoundstructure.mfp2) AS mfp2
FROM compoundstructure
WHERE compoundstructure.molecule @> mol_from_pkl(:molecule_1)
```

#### SMARTS-based query

* Python

```python
qmol = cast("c1[c,n]cccc1", QMol)
statement = select(Compound).where(Compound.molecule.hassubstruct(qmol))
results = session.execute(statement)
```

* SQL

```sql
SELECT compoundstructure.id, compoundstructure.name, mol_to_pkl(compoundstructure.molecule) AS molecule, bfp_to_binary_text(compoundstructure.mfp2) AS mfp2
FROM compoundstructure
WHERE compoundstructure.molecule @> CAST(:param_1 AS qmol)
```

### issubstruct( `<@` )

* Python

```python
statement = select(Compound).where(Compound.molecule.issubstruct("CCN1c2ccccc2Sc2ccccc21"))
results = session.execute(statement)
```

* SQL

```sql
SELECT compoundstructure.id, compoundstructure.name, mol_to_pkl(compoundstructure.molecule) AS molecule, bfp_to_binary_text(compoundstructure.mfp2) AS mfp2
FROM compoundstructure
WHERE compoundstructure.molecule <@ mol_from_pkl(:molecule_1)
```

## Similarity search

* Python

```python
from models import morganbv_fp

smiles = "CCN1c2ccccc2Sc2ccccc21"
statement = select(Compound).where(Compound.mfp2.tanimoto_sml(morganbv_fp(smiles)))
results = session.execute(statement)
```

* SQL

```sql
SELECT compoundstructure.id,
       compoundstructure.name,
       mol_to_pkl(compoundstructure.molecule) AS molecule,
       bfp_to_binary_text(compoundstructure.mfp2) AS mfp2
FROM compoundstructure
WHERE compoundstructure.mfp2 %% morganbv_fp(%(morganbv_fp_1)s::VARCHAR)
```

### Adjusting the similarity cutoff

* Python

```python
session.execute(text("SET rdkit.tanimoto_threshold=0.6")) # default is 0.5
```

* SQL

```sql
SET rdkit.tanimoto_threshold=0.6
```
