# Extension Array Integration with hash_pandas_object

## _hash_pandas_object() Method

All ExtensionArray subclasses can implement the `_hash_pandas_object()` method to customize their hashing behavior. This is the primary integration point between `hash_pandas_object` and custom array types.

## Method Signature
```python
def _hash_pandas_object(
    self, *, encoding: str, hash_key: str, categorize: bool
) -> npt.NDArray[np.uint64]:
```

## Implementation Locations

### 1. Base ExtensionArray (Default)
**File**: `pandas/core/arrays/base.py` (line 2278)

```python
def _hash_pandas_object(
    self, *, encoding: str, hash_key: str, categorize: bool
) -> npt.NDArray[np.uint64]:
    from pandas.core.util.hashing import hash_array
    
    values, _ = self._values_for_factorize()
    return hash_array(
        values, encoding=encoding, hash_key=hash_key, categorize=categorize
    )
```

**Behavior**: 
- Uses `_values_for_factorize()` to get hashable values
- Delegates to `hash_array()` for actual hashing
- This is the fallback for ExtensionArrays without custom implementations

### 2. NDArrayBackedExtensionArray
**File**: `pandas/core/arrays/_mixins.py` (line 201)

```python
def _hash_pandas_object(
    self, *, encoding: str, hash_key: str, categorize: bool
) -> npt.NDArray[np.uint64]:
    from pandas.core.util.hashing import hash_array
    
    values = self._ndarray
    return hash_array(
        values, encoding=encoding, hash_key=hash_key, categorize=categorize
    )
```

**Behavior**: 
- Directly hashes the underlying `_ndarray`
- Used by: DatetimeArray, TimedeltaArray, PeriodArray
- More efficient as it avoids the `_values_for_factorize()` conversion

### 3. BaseMaskedArray
**File**: `pandas/core/arrays/masked.py` (line 1045)

```python
def _hash_pandas_object(
    self, *, encoding: str, hash_key: str, categorize: bool
) -> npt.NDArray[np.uint64]:
    hashed_array = hash_array(
        self._data, encoding=encoding, hash_key=hash_key, categorize=categorize
    )
    hashed_array[self.isna()] = hash(self.dtype.na_value)
    return hashed_array
```

**Behavior**:
- Hashes the data array (`_data`)
- Replaces NA positions with hash of the NA value
- Used by: IntegerArray, FloatingArray, BooleanArray
- Ensures consistent hashing of missing values

### 4. Categorical
**File**: `pandas/core/arrays/categorical.py` (line 2179)

```python
def _hash_pandas_object(
    self, *, encoding: str, hash_key: str, categorize: bool
) -> npt.NDArray[np.uint64]:
    from pandas.core.util.hashing import hash_array
    
    values = hash_array(self.categories._values, encoding, hash_key, categorize)
    
    # Use take to handle -1 codes (NA values)
    result = algos.take_nd(
        values, self._codes, allow_fill=True, fill_value=hash(self.categories.dtype.na_value)
    )
    return result
```

**Behavior**:
- Hashes the unique categories once
- Maps codes to their corresponding hashes
- Handles NA values (-1 codes) with fill value
- Very efficient for data with many duplicates

### 5. SparseArray
**File**: `pandas/core/arrays/sparse/array.py` (line 907)

```python
def _values_for_factorize(self):
    # Still override this for hash_pandas_object
    return np.asarray(self), self.fill_value
```

**Behavior**:
- Uses the base implementation via `_values_for_factorize()`
- Converts to dense array for hashing
- Returns dense array and fill value

### 6. ArrowExtensionArray
**File**: `pandas/core/arrays/arrow/array.py`

**Note**: ArrowExtensionArray uses the base implementation but has special handling in various operations. The implementation relies on converting to numpy arrays when needed.

## Call Chain

```
hash_pandas_object(obj)
    ├─> hash_array(obj._values, ...)  [if Index or Series]
    │   └─> vals._hash_pandas_object(...)  [if ExtensionArray]
    │       ├─> hash_array(...)  [Base implementation]
    │       ├─> hash_array(self._ndarray, ...)  [NDArrayBacked]
    │       ├─> hash_array(self._data, ...); handle NA  [BaseMasked]
    │       ├─> hash categories; map codes  [Categorical]
    │       └─> convert to dense; hash  [Sparse]
    └─> combine_hash_arrays(...)  [if multiple columns/index]
```

## Key Design Principles

1. **Extensibility**: ExtensionArrays can customize hashing via `_hash_pandas_object()`
2. **Fallback**: Default implementation via `_values_for_factorize()` works for all arrays
3. **Consistency**: All implementations return uint64 arrays of the same length
4. **Efficiency**: Specialized implementations (e.g., Categorical) optimize for their data structure
5. **NA Handling**: Each implementation handles missing values appropriately for its dtype
