# Dependency Graph for hash_pandas_object

## Visual Dependency Tree

```
hash_pandas_object (PUBLIC API)
├── Used By (Direct Callers)
│   ├── User Code (pd.util.hash_pandas_object)
│   ├── Tests (test_hashing.py, extension tests)
│   └── Benchmarks (asv_bench/benchmarks/algorithms.py)
│
├── Internal Calls (Within hash_pandas_object)
│   ├── hash_tuples() ──────────────┐
│   │   └── Categorical._hash_pandas_object()
│   │       └── hash_array()
│   │
│   ├── hash_array() ───────────────┼─────────────────────┐
│   │   ├── ExtensionArray._hash_pandas_object()         │
│   │   │   ├── Base implementation                       │
│   │   │   ├── NDArrayBackedExtensionArray               │
│   │   │   ├── BaseMaskedArray                           │
│   │   │   ├── Categorical (custom)                      │
│   │   │   └── SparseArray (via _values_for_factorize)  │
│   │   └── _hash_ndarray() (for regular numpy arrays)   │
│   │       ├── Handles bool, datetime64, timedelta64     │
│   │       ├── Handles complex128                        │
│   │       ├── Handles numeric types                     │
│   │       └── hash_object_array() (C-level)             │
│   │                                                      │
│   └── combine_hash_arrays() ◄──────────────────────────┘
│       └── Used for combining column hashes (DataFrame)
│           and value+index hashes (Series with index=True)
│
└── Dependencies (What it needs)
    ├── pandas._libs.hashing.hash_object_array (C extension)
    ├── numpy operations (view, astype, XOR, multiplication)
    ├── pandas.core.dtypes.generic (ABCDataFrame, ABCSeries, etc.)
    └── pandas.Series (for return type)
```

## Detailed Component Dependencies

### 1. hash_pandas_object
**Depends on**:
- `hash_tuples()` - for MultiIndex
- `hash_array()` - for Index, Series values, DataFrame columns
- `combine_hash_arrays()` - for combining hashes
- `pandas.Series` - for return type
- Type checks: ABCMultiIndex, ABCIndex, ABCSeries, ABCDataFrame

**Called by**:
- User code via `pd.util.hash_pandas_object`
- Test suites
- Benchmarks
- Itself (recursive call for index hashing)

### 2. hash_array
**Depends on**:
- `ExtensionArray._hash_pandas_object()` - dispatch mechanism
- `_hash_ndarray()` - for numpy arrays
- Type checks: ABCExtensionArray

**Called by**:
- `hash_pandas_object()` - for Index, Series, DataFrame columns
- `hash_tuples()` - indirectly via Categorical._hash_pandas_object()
- ExtensionArray._hash_pandas_object() default implementation

### 3. _hash_ndarray
**Depends on**:
- `hash_object_array()` from pandas._libs.hashing (C extension)
- `pandas.Categorical` and `factorize` (for object dtype with categorize=True)
- numpy operations: view, astype, XOR, multiplication

**Called by**:
- `hash_array()` - for regular numpy arrays
- ExtensionArray._hash_pandas_object() implementations (indirectly)

### 4. hash_tuples
**Depends on**:
- `pandas.Categorical` and `MultiIndex`
- `Categorical._hash_pandas_object()`
- `combine_hash_arrays()`

**Called by**:
- `hash_pandas_object()` - for MultiIndex objects

### 5. combine_hash_arrays
**Depends on**:
- numpy operations only
- Pure algorithm (CPython tuple hashing variant)

**Called by**:
- `hash_pandas_object()` - for combining column/index hashes
- `hash_tuples()` - for combining MultiIndex level hashes

### 6. ExtensionArray._hash_pandas_object
**Depends on** (varies by implementation):
- Base: `hash_array()`, `_values_for_factorize()`
- NDArrayBacked: `hash_array()`, `self._ndarray`
- BaseMasked: `hash_array()`, `self._data`, `self._mask`
- Categorical: `hash_array()`, `algos.take_nd()`
- Sparse: Dense conversion

**Called by**:
- `hash_array()` - dispatch mechanism for ExtensionArrays
- `hash_tuples()` - for Categorical arrays in MultiIndex

## Dependency Levels

### Level 0 (No pandas dependencies):
- `combine_hash_arrays()` - pure numpy/Python
- `hash_object_array()` - C extension (pandas._libs.hashing)

### Level 1 (Depends on Level 0):
- `_hash_ndarray()` - uses hash_object_array, numpy ops

### Level 2 (Depends on Level 1):
- `ExtensionArray._hash_pandas_object()` - uses hash_array → _hash_ndarray
- `hash_array()` - dispatches to _hash_ndarray or _hash_pandas_object

### Level 3 (Depends on Level 2):
- `hash_tuples()` - uses _hash_pandas_object and combine_hash_arrays

### Level 4 (Top level, depends on all below):
- `hash_pandas_object()` - orchestrates everything

## External Dependencies

### From pandas._libs (C extensions):
1. **hash_object_array()**: Low-level hashing of object arrays
   - Located in: pandas/_libs/hashing.pyx
   - Purpose: Fast C-level hashing of Python objects

### From numpy:
1. Array operations: view, astype, XOR (^), multiplication (*)
2. Data type handling: dtype checks and conversions
3. Array utilities: concatenate, zeros, full, etc.

### From pandas.core:
1. **dtypes.generic**: ABCDataFrame, ABCSeries, ABCIndex, ABCMultiIndex, ABCExtensionArray
2. **Series**: Return type for hash_pandas_object
3. **Categorical**: Used in hash_tuples and _hash_ndarray
4. **algorithms.factorize**: Used in _hash_ndarray for object dtype

## No Circular Dependencies

The design ensures there are **no circular dependencies**:
- hash_pandas_object is at the top level
- It depends on lower-level functions
- Lower-level functions never call back up to hash_pandas_object
- Exception: hash_pandas_object calls itself for index hashing (controlled recursion)

## Data Flow

```
Input (Index/Series/DataFrame)
    │
    ▼
Type Checking & Dispatch (hash_pandas_object)
    │
    ├─► MultiIndex ──► hash_tuples ──► Categorical._hash_pandas_object ──► hash_array
    │                                                                           │
    ├─► Index ──────────────► hash_array ◄─────────────────────────────────────┘
    │                            │
    ├─► Series ─────────────► hash_array + optional index hash + combine
    │                            │
    └─► DataFrame ──► hash_array per column + optional index hash + combine
                         │
                         ▼
        ┌────────────────┴────────────────┐
        │                                 │
    ExtensionArray?                  numpy array?
        │                                 │
        ▼                                 ▼
    _hash_pandas_object()          _hash_ndarray()
        │                                 │
        │                                 ├─► numeric: direct bit operations
        │                                 ├─► datetime/timedelta: view as int
        │                                 ├─► bool: astype to uint8
        │                                 ├─► complex: hash real+imag separately
        │                                 └─► object: hash_object_array() or categorize
        │
        └─────────────┬───────────────────┘
                      │
                      ▼
            uint64 hash array
                      │
                      ▼
                Series (result)
```
