# hash_pandas_object Implementation Details

## Core Implementation

The `hash_pandas_object` function follows different logic paths depending on the input type:

### 1. MultiIndex Path
```python
if isinstance(obj, ABCMultiIndex):
    return Series(hash_tuples(obj, encoding, hash_key), dtype="uint64", copy=False)
```
- Calls `hash_tuples()` helper function
- Returns hashed tuples directly

### 2. Index Path
```python
elif isinstance(obj, ABCIndex):
    h = hash_array(obj._values, encoding, hash_key, categorize).astype("uint64", copy=False)
    ser = Series(h, index=obj, dtype="uint64", copy=False)
```
- Calls `hash_array()` on the index values
- Returns Series with the index as both data and index

### 3. Series Path
```python
elif isinstance(obj, ABCSeries):
    h = hash_array(obj._values, encoding, hash_key, categorize).astype("uint64", copy=False)
    if index:
        # Hash index and combine with values
        index_iter = (hash_pandas_object(obj.index, index=False, ...) for _ in [None])
        arrays = itertools.chain([h], index_iter)
        h = combine_hash_arrays(arrays, 2)
    ser = Series(h, index=obj.index, dtype="uint64", copy=False)
```
- Hashes the Series values
- Optionally hashes and combines the index using `combine_hash_arrays()`
- Returns Series with hashed values

### 4. DataFrame Path
```python
elif isinstance(obj, ABCDataFrame):
    hashes = (hash_array(series._values, encoding, hash_key, categorize) 
              for _, series in obj.items())
    num_items = len(obj.columns)
    if index:
        # Hash index and include in combination
        index_hash_generator = (hash_pandas_object(obj.index, index=False, ...) for _ in [None])
        num_items += 1
        _hashes = itertools.chain(hashes, index_hash_generator)
        hashes = (x for x in _hashes)
    h = combine_hash_arrays(hashes, num_items)
    ser = Series(h, index=obj.index, dtype="uint64", copy=False)
```
- Iterates through columns, hashing each Series
- Optionally includes the index hash
- Combines all hashes using `combine_hash_arrays()`
- Returns Series with combined hash values

## Helper Functions

### hash_array()
Located in `pandas/core/util/hashing.py` (line 235)

```python
def hash_array(
    vals: ArrayLike,
    encoding: str = "utf8",
    hash_key: str = _default_hash_key,
    categorize: bool = True,
) -> npt.NDArray[np.uint64]
```

- Handles actual array hashing
- Dispatches to `_hash_pandas_object()` for ExtensionArrays
- Falls back to `_hash_ndarray()` for regular numpy arrays

### hash_tuples()
Located in `pandas/core/util/hashing.py` (line 185)

```python
def hash_tuples(
    vals: MultiIndex | Iterable[tuple[Hashable, ...]],
    encoding: str = "utf8",
    hash_key: str = _default_hash_key,
) -> npt.NDArray[np.uint64]
```

- Specialized function for hashing MultiIndex or tuple lists
- Creates Categorical arrays for each level
- Hashes each Categorical and combines results

### combine_hash_arrays()
Located in `pandas/core/util/hashing.py` (line 48)

```python
def combine_hash_arrays(
    arrays: Iterator[np.ndarray], num_items: int
) -> npt.NDArray[np.uint64]
```

- Combines multiple hash arrays into a single hash
- Uses algorithm similar to CPython's tuple hashing
- XOR and multiplication operations for hash combination

### _hash_ndarray()
Located in `pandas/core/util/hashing.py` (line 290)

```python
def _hash_ndarray(
    vals: np.ndarray,
    encoding: str = "utf8",
    hash_key: str = _default_hash_key,
    categorize: bool = True,
) -> npt.NDArray[np.uint64]
```

- Low-level hashing for numpy arrays
- Handles special dtypes (bool, datetime64, timedelta64, complex128)
- Uses categorization for object dtypes with repeated values
- Applies bit-mixing operations for better hash distribution
