# Critical Issues Diagnosis Report
**Date:** 2026-01-04 21:23
**Status:** 🔴 **CRITICAL ERRORS IDENTIFIED**
**Trigger:** Gemini testing caused multiple failures

---

## Executive Summary

After Gemini ran tests, the application has **3 critical failures** that prevent deployment and operation:

1. 🔴 **Backend Docker build failure** - Invalid CUDA dependency wheel
2. 🔴 **ZIP extraction failure** - "Invalid ZIP file format"
3. 🟡 **Metadata 404 errors** - Some UUIDs return 404

---

## Error Analysis

### 🔴 CRITICAL #1: Backend Docker Build Failure

**Error:**
```
ERROR: Wheel 'nvidia-cusparselt-cu12' located at /wheels/nvidia_cusparselt_cu12-0.7.1-py3-none-manylinux2014_x86_64.whl is invalid.
failed to solve: process "/bin/sh -c pip install --no-cache-dir /wheels/* && rm -rf /wheels" did not complete successfully: exit code: 1
```

**Location:** `backend/Dockerfile` line 32

**Root Cause:**
- PyTorch 2.9.1 dependencies include CUDA libraries
- `nvidia-cusparselt-cu12==0.7.1` wheel file is corrupted or incompatible
- Docker multi-stage build fails at runtime stage when installing pre-built wheels

**Impact:** **CRITICAL** - Backend container cannot be built, deployment impossible

**PDF Requirement Status:** ❌ FAIL - Cannot deploy solution

---

### 🔴 CRITICAL #2: ZIP Extraction Failure

**Error:**
```
2026-01-04 12:23:10,147 - src.scripts.etl_runner - ERROR - ✗ Failed to process data files: Invalid ZIP file format
```

**Test UUID:** `755e0369-f8db-4550-aabe-3f9c9fbcb93d`
**URL:** `https://catalogue.ceh.ac.uk/datastore/eidchub/755e0369-f8db-4550-aabe-3f9c9fbcb93d`
**Downloaded:** 0.03MB (29.9KB)

**Root Cause:**
The download URL returns an HTML page (likely a landing page or authentication form), not a ZIP file.

**Evidence:**
```python
# From zip_extractor.py - this expects a ZIP file
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    # But the downloaded file is HTML, not ZIP
```

**Impact:** **CRITICAL** - Core ETL functionality broken, cannot extract dataset files

**PDF Requirement Status:** ❌ FAIL
> "Datasets can be accessed using the download option. These datasets are usually provided as zip files, so your ETL library must be able to extract the zip file and then extract its contents."

---

### 🟡 WARNING #3: Metadata 404 Errors

**Error:**
```
404 Client Error: for url: https://catalogue.ceh.ac.uk/documents/00039bf8-b4de-461d-bcfc-d1973bb0287c.xml
404 Client Error: for url: https://catalogue.ceh.ac.uk/documents/00039bf8-b4de-461d-bcfc-d1973bb0287c.json
```

**Failed UUID:** `00039bf8-b4de-461d-bcfc-d1973bb0287c`

**Root Cause:**
- This UUID may not exist in the CEH catalogue
- URL pattern `/documents/` might be incorrect
- Should try `/id/` pattern instead

**Impact:** **MEDIUM** - Some datasets cannot be fetched

---

## PDF Task Requirements Verification

### ✅ PASS: ETL Subsystem (Partial)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| 4 metadata extractors (XML, JSON, JSON-LD, RDF) | ✅ | All exist in `backend/src/infrastructure/etl/extractors/` |
| Store raw documents | ✅ | `models.py`: `raw_document_json`, `raw_document_xml` |
| Extract to SQLite | ✅ | Working for successful fetches |
| ZIP extraction | ❌ | **BROKEN** - "Invalid ZIP file format" |
| fileAccess handling | ⚠️ | Not tested |
| Supporting docs | ✅ | Downloaded successfully (2/2 for working UUID) |

**Overall:** ❌ FAIL - ZIP extraction broken

---

### ❓ UNKNOWN: Semantic Database

**PDF Requirement:**
> "You must then use these fields to create vector embeddings that capture the semantic meaning of the titles and abstracts. You need to store this semantic information in a vector store of your choice to support semantic search."

**Need to Verify:**
1. Are embeddings being created?
2. Is ChromaDB being populated?
3. Is vector search working?

**Action Required:** Test with `vector_search=True` flag

---

### ❓ UNKNOWN: Frontend

**PDF Requirement:**
> "You are required to develop a web app that supports the search and discovery of datasets. The web app must be built using Svelte and shadcn-ui or Vue."

**Need to Verify:**
1. Can frontend start? (Docker build successful ✅)
2. Does semantic search work?
3. Is the UI functional?

**Action Required:** Test frontend deployment

---

## Root Cause Analysis: What Gemini Did

Based on the errors, Gemini likely:

1. **Modified download URL logic** that now returns HTML instead of ZIP files
2. **Updated PyTorch version** to 2.9.1 which has a broken CUDA dependency
3. **Changed URL patterns** for metadata fetching causing 404s

---

## Recommended Fixes

### FIX #1: Backend Docker Build (CRITICAL)

**Option A: Use CPU-only PyTorch** (Recommended for development)
```python
# requirements.txt
torch==2.1.2  # CPU version, more stable
# OR explicitly:
torch==2.1.2+cpu
```

**Option B: Fix CUDA dependencies**
```dockerfile
# In Dockerfile, add error handling
RUN pip install --no-cache-dir /wheels/* || \
    (echo "Wheel installation failed, installing directly..." && \
     pip install --no-cache-dir -r /app/requirements.txt)
```

**Option C: Skip problematic dependency**
```dockerfile
RUN pip install --no-cache-dir $(ls /wheels/*.whl | grep -v nvidia-cusparselt) && \
    rm -rf /wheels
```

---

###FIX #2: ZIP Extraction (CRITICAL)

**Problem:** Download URL returns HTML, not ZIP

**Diagnosis Steps:**
1. Check what `download_url` contains in database
2. Verify URL pattern is correct for CEH catalogue
3. Test direct browser access to confirm file type

**Potential Fixes:**

**Option A: Fix URL construction**
```python
# Check xml_extractor.py _extract_distribution_info()
# Ensure it extracts the CORRECT direct download URL
# Not the HTML landing page
```

**Option B: Add content-type checking**
```python
# In zip_extractor.py
response = requests.head(url)
content_type = response.headers.get('Content-Type', '')
if 'html' in content_type.lower():
    logger.warning(f"URL returns HTML, not ZIP: {url}")
    # Try alternative URL patterns
```

**Option C: Handle authentication**
```python
# CEH may require authentication
# Add session/cookies handling
```

---

### FIX #3: Metadata 404 Errors (MEDIUM)

**Fix URL patterns in fetcher.py:**

Current patterns (causing 404):
```python
"https://catalogue.ceh.ac.uk/documents/{uuid}.xml"
```

Should try:
```python
"https://catalogue.ceh.ac.uk/id/{uuid}.xml"
"https://catalogue.ceh.ac.uk/id/{uuid}"  # Without extension
```

---

## Immediate Action Plan

### 🔴 PRIORITY 1: Get System Running (30 min)

1. **Fix Backend Docker** (10 min)
   - Switch to CPU-only torch OR skip broken wheel
   - Rebuild backend container
   - Verify build succeeds

2. **Diagnose ZIP Issue** (10 min)
   - Query database for actual URLs being used
   - Test one URL directly in browser
   - Check if it's really a ZIP file

3. **Fix ZIP Extractor** (10 min)
   - Update URL logic based on findings
   - Test with known-good dataset

---

### 🟡 PRIORITY 2: Verify Requirements (45 min)

4. **Test Vector Embeddings** (15 min)
   - Run ETL with `vector_search=True`
   - Verify ChromaDB populated
   - Test semantic search query

5. **Test Frontend** (15 min)
   - Deploy frontend container
   - Access UI
   - Test search functionality

6. **End-to-End Test** (15 min)
   - Fetch metadata → Extract → Store → Search
   - Verify full pipeline works

---

## Success Criteria

Before considering system "working":

- [ ] Backend Docker builds successfully
- [ ] Frontend Docker builds successfully
- [ ] ETL can fetch metadata (at least 5 datasets)
- [ ] ZIP extraction works (at least 2 datasets)
- [ ] Vector embeddings created and stored
- [ ] Frontend can search datasets
- [ ] Semantic search returns relevant results

---

## Files to Check/Modify

**Docker:**
- `backend/Dockerfile` - Line 32 wheel installation
- `backend/requirements.txt` - PyTorch version

**ETL:**
- `backend/src/infrastructure/etl/zip_extractor.py` - ZIP extraction logic
- `backend/src/infrastructure/etl/fetcher.py` - URL patterns
- `backend/src/infrastructure/etl/extractors/xml_extractor.py` - `_extract_distribution_info()`

**Database:**
- Query: `SELECT id, download_url, landing_page_url FROM metadata LIMIT 10;`
- Check what URLs are actually being stored

---

## Next Steps

1. **Immediate:** Fix Backend Docker build (choose Option A: CPU-only PyTorch)
2. **Next:** Diagnose ZIP issue by checking actual URLs
3. **Then:** Fix ZIP extraction based on findings
4. **Finally:** Comprehensive testing against PDF requirements

---

**Report Generated:** 2026-01-04 21:23
**Severity:** 🔴 CRITICAL - System non-functional
**Action Required:** IMMEDIATE fixes needed before submission
