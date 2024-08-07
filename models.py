from pydantic import ConfigDict
from rdkit import DataStructs
from rdkit.Chem import AllChem as Chem
from rdkit.DataStructs import ExplicitBitVect
from sqlalchemy import Index
from sqlalchemy import types as sqltypes
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import operators
from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.types import UserDefinedType
from sqlmodel import Field, SQLModel


class Mol(UserDefinedType):
    cache_ok = True

    class comparator_factory(UserDefinedType.Comparator):
        def hassubstruct(self, other):
            return self.operate(
                operators.custom_op("@>"), other, result_type=sqltypes.Boolean
            )

        def issubstruct(self, other):
            return self.operate(
                operators.custom_op("<@"), other, result_type=sqltypes.Boolean
            )

        def __eq__(self, other):
            return self.operate(
                operators.custom_op("@="), other, result_type=sqltypes.Boolean
            )

    def get_col_spec(self, **kw):
        return "mol"

    def bind_processor(self, dialect):
        def process(value):
            if isinstance(value, Chem.Mol):
                value = memoryview(value.ToBinary())
            elif isinstance(value, str):
                value = memoryview(Chem.MolFromSmiles(value).ToBinary())
            return value

        return process

    def bind_expression(self, bindvalue):
        return mol_from_pkl(bindvalue)

    def column_expression(self, colexpr):
        return mol_to_pkl(colexpr, type_=self)

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return value
            return Chem.Mol(bytes(value))

        return process


class mol_from_pkl(GenericFunction):
    name = "mol_from_pkl"
    type = Mol()


class mol_to_pkl(GenericFunction):
    name = "mol_to_pkl"
    type = postgresql.BYTEA()


class QMol(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw):
        return "qmol"


class Bfp(UserDefinedType):
    cache_ok = True

    class comparator_factory(UserDefinedType.Comparator):
        def tanimoto_sml(self, other):
            return self.operate(
                operators.custom_op("%"), other, result_type=sqltypes.Boolean
            )

    def get_col_spec(self, **kw):
        return "bfp"

    def bind_processor(self, dialect):
        def process(value):
            if isinstance(value, ExplicitBitVect):
                value = memoryview(DataStructs.BitVectToBinaryText(value))
            return value

        return process

    def bind_expression(self, bindvalue):
        return bfp_from_binary_text(bindvalue)

    def column_expression(self, colexpr):
        return bfp_to_binary_text(colexpr, type_=self)

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return value
            elif isinstance(value, bytes | bytearray | memoryview):
                return DataStructs.CreateFromBinaryText(bytes(value))
            else:
                raise RuntimeError("Unexpected row value type for a Bfp instance")

        return process


class bfp_from_binary_text(GenericFunction):
    name = "bfp_from_binary_text"
    type = Bfp()


class bfp_to_binary_text(GenericFunction):
    name = "bfp_to_binary_text"
    type = postgresql.BYTEA()


class morganbv_fp(GenericFunction):
    inherit_cache = True
    name = "morganbv_fp"
    type = Bfp()


class Compound(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    molecule: Mol = Field(sa_type=Mol)
    mfp2: Bfp = Field(sa_type=Bfp, nullable=True)

    __table_args__ = (
        Index("compoundstructure_molecule", "molecule", postgresql_using="gist"),
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __repr__(self):
        return f"({self.name}) < {self.molecule} >"
