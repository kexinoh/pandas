# Individual Function Roles and Responsibilities

## 1. hash_pandas_object()
**Location**: `pandas/core/util/hashing.py:84`

**Role**: Main entry point for hashing pandas objects

**Responsibilities**:
- Accept Index, Series, or DataFrame objects
- Dispatch to appropriate hashing logic based on object type
- Handle the `index` parameter (whether to include index in hash)
- Coordinate hash combination for multi-column/multi-dimensional data
- Return Series of uint64 hash values

**Key Logic**:
- MultiIndex → delegate to `hash_tuples()`
- Index → hash values with `hash_array()`
- Series → hash values, optionally combine with index hash
- DataFrame → hash each column, optionally combine with index hash

**Parameters Impact**:
- `index=True`: Includes index in hash computation (affects Series/DataFrame only)
- `encoding`: Passed down to string/object hashing
- `hash_key`: Passed down to low-level hashing for salt
- `categorize`: Enables optimization for object dtype with duplicates

---

## 2. hash_array()
**Location**: `pandas/core/util/hashing.py:235`

**Role**: Array-level hashing dispatcher

**Responsibilities**:
- Accept any array-like object (numpy array or ExtensionArray)
- Dispatch to appropriate implementation based on array type
- Return uint64 numpy array of hash values

**Key Logic**:
- ExtensionArray → call `_hash_pandas_object()` method
- numpy.ndarray → call `_hash_ndarray()`
- Other types → raise TypeError

**Why Important**:
- Single entry point for array hashing
- Enables polymorphic behavior for ExtensionArrays
- Maintains consistency in hash computation

---

## 3. _hash_ndarray()
**Location**: `pandas/core/util/hashing.py:290`

**Role**: Low-level numpy array hashing

**Responsibilities**:
- Hash regular numpy arrays
- Handle different dtype categories appropriately
- Apply bit-mixing operations for good hash distribution
- Optionally categorize object arrays for efficiency

**Key Logic by dtype**:
```python
# Boolean → uint8
if dtype == bool:
    vals = vals.astype("u8")

# Datetime/Timedelta → view as int64
elif issubclass(dtype.type, (np.datetime64, np.timedelta64)):
    vals = vals.view("i8").astype("u8", copy=False)

# Numeric (<=8 bytes) → view as uint
elif issubclass(dtype.type, np.number) and dtype.itemsize <= 8:
    vals = vals.view(f"u{vals.dtype.itemsize}").astype("u8")

# Object dtype → categorize or hash_object_array
else:
    if categorize:
        # Create Categorical, hash categories, map codes
        codes, categories = factorize(vals, sort=False)
        cat = Categorical._simple_new(codes, ...)
        return cat._hash_pandas_object(...)
    else:
        # Direct C-level object hashing
        vals = hash_object_array(vals, hash_key, encoding)
```

**Bit-mixing algorithm** (for better distribution):
```python
vals ^= vals >> 30
vals *= np.uint64(0xBF58476D1CE4E5B9)
vals ^= vals >> 27
vals *= np.uint64(0x94D049BB133111EB)
vals ^= vals >> 31
```

---

## 4. hash_tuples()
**Location**: `pandas/core/util/hashing.py:185`

**Role**: Specialized hashing for MultiIndex or tuple sequences

**Responsibilities**:
- Convert tuple sequences to MultiIndex if needed
- Hash each level of the MultiIndex separately
- Combine level hashes into single hash per tuple

**Key Logic**:
```python
# Create Categorical for each level
cat_vals = [
    Categorical._simple_new(
        mi.codes[level],
        CategoricalDtype(categories=mi.levels[level], ordered=False),
    )
    for level in range(mi.nlevels)
]

# Hash each Categorical
hashes = (
    cat._hash_pandas_object(encoding=encoding, hash_key=hash_key, categorize=False)
    for cat in cat_vals
)

# Combine using tuple-like algorithm
h = combine_hash_arrays(hashes, len(cat_vals))
```

**Why Efficient**:
- Leverages Categorical's efficient hashing
- Only hashes unique values per level
- Maps codes to hashes via lookup

---

## 5. combine_hash_arrays()
**Location**: `pandas/core/util/hashing.py:48`

**Role**: Combine multiple hash arrays into single hash

**Responsibilities**:
- Take iterator of hash arrays
- Combine them using deterministic algorithm
- Return single hash array

**Algorithm** (CPython tuple hashing variant):
```python
mult = np.uint64(1000003)
out = np.zeros_like(first) + np.uint64(0x345678)

for i, a in enumerate(arrays):
    inverse_i = num_items - i
    out ^= a                           # XOR with current hash
    out *= mult                        # Multiply
    mult += np.uint64(82520 + inverse_i + inverse_i)  # Update multiplier

out += np.uint64(97531)                # Final mix
```

**Properties**:
- Order-sensitive: (a,b) ≠ (b,a)
- Avalanche effect: small changes propagate
- Deterministic: same input → same output

---

## 6. ExtensionArray._hash_pandas_object()
**Location**: Multiple files (see Extension Array Integration doc)

**Role**: Extension point for custom array types

**Responsibilities**:
- Implement type-specific hashing logic
- Return uint64 array of same length as input
- Handle missing values appropriately
- Maintain consistency with equals() semantics

### 6a. Base Implementation
**Location**: `pandas/core/arrays/base.py:2278`

**Logic**:
```python
values, _ = self._values_for_factorize()
return hash_array(values, ...)
```

**When Used**: Fallback for arrays without custom implementation

### 6b. NDArrayBackedExtensionArray
**Location**: `pandas/core/arrays/_mixins.py:201`

**Logic**:
```python
values = self._ndarray
return hash_array(values, ...)
```

**When Used**: DatetimeArray, TimedeltaArray, PeriodArray

### 6c. BaseMaskedArray
**Location**: `pandas/core/arrays/masked.py:1045`

**Logic**:
```python
hashed_array = hash_array(self._data, ...)
hashed_array[self.isna()] = hash(self.dtype.na_value)
return hashed_array
```

**When Used**: IntegerArray, FloatingArray, BooleanArray

**Special Handling**: Consistent hash for NA values

### 6d. Categorical
**Location**: `pandas/core/arrays/categorical.py:2179`

**Logic**:
```python
# Hash unique categories once
values = hash_array(self.categories._values, ...)

# Map codes to category hashes
result = algos.take_nd(
    values, self._codes,
    allow_fill=True,
    fill_value=hash(self.categories.dtype.na_value)
)
return result
```

**When Used**: CategoricalArray

**Optimization**: Hash categories once, map via codes

### 6e. SparseArray
**Location**: `pandas/core/arrays/sparse/array.py:907`

**Logic**:
```python
def _values_for_factorize(self):
    return np.asarray(self), self.fill_value
```

**When Used**: SparseArray

**Approach**: Convert to dense, use base implementation

---

## 7. hash_object_array() [C Extension]
**Location**: `pandas/_libs/hashing.pyx`

**Role**: Low-level C implementation for hashing Python objects

**Responsibilities**:
- Hash arbitrary Python objects efficiently
- Handle encoding of strings
- Use provided hash_key for salting
- Return uint64 array

**Why C Extension**:
- Performance: Direct access to Python object hashing
- Efficiency: Avoids Python loop overhead
- Flexibility: Can handle any hashable Python object

---

## Function Call Frequency (Typical DataFrame Hash)

For `hash_pandas_object(DataFrame with 3 columns and index)`:

1. `hash_pandas_object()`: Called 1 time (entry point)
2. `hash_array()`: Called 4 times (3 columns + 1 index)
3. `combine_hash_arrays()`: Called 1 time (combine all hashes)
4. `_hash_ndarray()` or `_hash_pandas_object()`: Called 4 times (once per hash_array call)
5. `hash_object_array()`: Called 0-4 times (depends on dtypes)

**Example timeline**:
```
hash_pandas_object(df)
├─ hash_array(column1)
│  └─ _hash_ndarray(column1_values)
├─ hash_array(column2)
│  └─ _hash_ndarray(column2_values)
├─ hash_array(column3)
│  └─ _hash_ndarray(column3_values)
├─ hash_array(index)
│  └─ _hash_ndarray(index_values)
└─ combine_hash_arrays([h1, h2, h3, h_idx])
   └─ return combined_hash
```

---

## Summary Table

| Function | Role | Input | Output | Complexity |
|----------|------|-------|--------|------------|
| hash_pandas_object | Orchestrator | Index/Series/DataFrame | Series[uint64] | O(n*m) for DataFrame |
| hash_array | Dispatcher | ArrayLike | ndarray[uint64] | O(n) |
| _hash_ndarray | numpy hasher | ndarray | ndarray[uint64] | O(n) |
| hash_tuples | MultiIndex hasher | tuples/MultiIndex | ndarray[uint64] | O(n*levels) |
| combine_hash_arrays | Hash combiner | Iterator[ndarray] | ndarray[uint64] | O(n*m) |
| _hash_pandas_object | EA method | ExtensionArray | ndarray[uint64] | O(n) |
| hash_object_array | C-level hasher | ndarray[object] | ndarray[uint64] | O(n) |

Where:
- n = number of rows
- m = number of columns (DataFrame) or levels (MultiIndex)
