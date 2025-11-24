
import pandas as pd
import numpy as np
from pandas._libs import lib

print(f"lib.u8max: {lib.u8max}")
print(f"Hex: {hex(lib.u8max)}")

s = pd.Series([np.nan, None, "nan", "None"])

print("\nDefault (categorize=True):")
print(pd.util.hash_pandas_object(s, categorize=True))

print("\ncategorize=False:")
print(pd.util.hash_pandas_object(s, categorize=False))
