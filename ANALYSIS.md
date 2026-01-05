# 🔍 Veterans Verification Analysis

## Problem: Why All Attempts Return "notApproved"

### Root Cause
The data scraped from VA.gov **Veterans Legacy Memorial** contains information about **DECEASED veterans**.

SheerID verifies against the **DoD/DEERS (Defense Enrollment Eligibility Reporting System)** database, which only contains:
- Active Duty military personnel
- Veterans who discharged within the last 12 months
- Living veterans with valid records

### How SheerID Veterans Verification Works

```
┌────────────────────────────────────────────────────────────────┐
│                 SheerID Veterans Flow                          │
├────────────────────────────────────────────────────────────────┤
│ 1. ChatGPT API → Create verification ID                        │
│ 2. Submit military status (VETERAN)                            │
│ 3. Submit personal info (name, DOB, branch, discharge date)    │
│ 4. SheerID → Query DoD/DEERS Database                          │
│    │                                                            │
│    ├── FOUND + Data matches → "emailLoop" → email verify       │
│    ├── FOUND + Recent discharge → "success" (auto-approve)     │
│    └── NOT FOUND → "error" + "notApproved" ❌                  │
│                                                                 │
│ Note: Unlike Student verification, there is NO document upload │
│       fallback. If not in DEERS = permanently rejected.        │
└────────────────────────────────────────────────────────────────┘
```

### Key Differences: Veterans vs Student/Teacher

| Feature | Student/Teacher | Veterans |
|---------|-----------------|----------|
| Instant Database Check | No | Yes (DEERS) |
| Document Upload Fallback | Yes | **NO** |
| SSO Skip | Yes | N/A |
| Auto-Pass Possible | Yes | Only if in DEERS |
| Manual Review | Yes | **NO** |

## Solutions

### ❌ What WON'T Work
1. **Document Upload** - Veterans verification doesn't support doc fallback
2. **Fake/Generated Data** - Must match DEERS exactly
3. **Deceased Veterans Data** - Not in DEERS database

### ✅ What MIGHT Work
1. **Real veteran data** from someone who:
   - Is still alive
   - Discharged within last 12 months
   - Has valid DEERS record

2. **Active Duty data** (but this is harder to get and verify)

### Data Requirements for Success
- First Name: Must match DEERS exactly
- Last Name: Must match DEERS exactly  
- Birth Date: Must match DEERS exactly
- Branch: Must match service record
- Discharge Date: Should be within last 12 months (2024-01 to 2025-01)

## Recommendations

1. **For Testing**: Use the tool as-is to understand the flow
2. **For Success**: Need actual veteran data from someone eligible
3. **Alternative**: Use K12 Teacher verification (has auto-pass feature)

## References
- SheerID Veterans Program: https://www.sheerid.com/shoppers/military-verification/
- DEERS: https://www.tricare.mil/DEERS
- Original Tool: https://github.com/ThanhNguyxn/SheerID-Verification-Tool
