# Tenderpreneur Automation & Verification Scripts

This directory contains repeatable automation and verification scripts for Tenderpreneur.

## `verify_mvp_loop.py`

Validates the full contractor and supplier procurement lifecycle across all 13 core steps:
1. Platform health check
2. Contractor authentication (Sipho Ndlovu - Amandla Civils)
3. BoQ tender creation
4. Raw schedule of quantities ingestion and AI parsing
5. Manual line-item correction
6. Quote request generation and broadcast to matched regional suppliers
7. Supplier 1 quote submission (AfriReady Concrete)
8. Supplier 2 competing quote submission (Durban Builders Hub)
9. Contractor quote comparison matrix (verifying Lowest Price and Fastest Delivery badges)
10. Contractor quote selection
11. Manual price override with mandatory procurement audit reasoning
12. Defensible Excel (.xlsx) and PDF tender schedule export generation and download
13. Verification of the immutable `AuditEvent` trail

### Usage

**In-process zero-dependency execution:**
```bash
python scripts/verify_mvp_loop.py
```

**Live server execution:**
```bash
python scripts/verify_mvp_loop.py --url http://localhost:8000
```
