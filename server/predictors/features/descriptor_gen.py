#!/usr/bin/env python

from rdkit import Chem
import numpy as np
from rdkit.Chem import rdFingerprintGenerator

# Pre-create generator (reusable, thread-safe)
_morgan_gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)


class DescriptorGen:

    def from_smiles(self, smi):
        mol = Chem.MolFromSmiles(smi)
        if mol:
            return self.from_mol(mol)
        else:
            return None

    def from_mol(self, mol):
        arr = _morgan_gen.GetFingerprintAsNumPy(mol)
        return arr


if __name__ == "__main__":
    descriptor_gen = DescriptorGen()
    print(descriptor_gen.from_smiles("CCCC"))
