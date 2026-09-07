import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.models import (
    BoQ,
    Document,
    LineItem,
    Organisation,
    Quote,
    QuoteRequest,
    QuoteRequestSupplier,
    SupplierProfile,
    User,
    generate_uuid,
    utc_now,
)


async def seed_database():
    print("[INFO] Initializing and seeding database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        res = await session.execute(select(Organisation))
        if res.first():
            print("[INFO] Database already contains data. Skipping seed.")
            return

        now = utc_now()

        # 1. Create Contractor Organisation
        contractor_org = Organisation(
            id=generate_uuid(),
            type="contractor",
            legal_name="Amandla Infrastructure & Civil Contractors (Pty) Ltd",
            trading_name="Amandla Civils",
            email="estimator@amandlacivils.co.za",
            phone="+27 31 555 0192",
            region="KwaZulu-Natal",
            created_at=now,
            updated_at=now,
        )
        session.add(contractor_org)

        contractor_user = User(
            id=generate_uuid(),
            organisation_id=contractor_org.id,
            email="estimator@amandlacivils.co.za",
            name="Sipho Ndlovu",
            role="admin",
            created_at=now,
            updated_at=now,
        )
        session.add(contractor_user)

        # 2. Create Suppliers
        suppliers_data = [
            {
                "legal_name": "Durban Building Supplies & Cement CC",
                "trading_name": "Durban Builders Hub",
                "email": "sales@durbanbuilders.co.za",
                "phone": "+27 82 441 9021",
                "region": "KwaZulu-Natal",
                "categories": ["building-materials", "concrete", "earthworks"],
                "regions": ["KwaZulu-Natal", "Eastern Cape"],
                "compliance": {"bbee_level": "1", "cidb_grade": "6GB", "csd_registered": True},
                "contact": "whatsapp",
            },
            {
                "legal_name": "AfriReady Concrete & Aggregate Solutions",
                "trading_name": "AfriReady Concrete",
                "email": "orders@afriready.co.za",
                "phone": "+27 83 992 1104",
                "region": "KwaZulu-Natal",
                "categories": ["concrete", "earthworks"],
                "regions": ["KwaZulu-Natal", "Gauteng"],
                "compliance": {"bbee_level": "2", "cidb_grade": "7CE", "csd_registered": True},
                "contact": "whatsapp",
            },
            {
                "legal_name": "Natal Roofing & Timber Fabricators (Pty) Ltd",
                "trading_name": "Natal Roof Trusses",
                "email": "quotes@natalroofing.co.za",
                "phone": "+27 84 330 8820",
                "region": "KwaZulu-Natal",
                "categories": ["roofing", "building-materials"],
                "regions": ["KwaZulu-Natal"],
                "compliance": {"bbee_level": "1", "csd_registered": True},
                "contact": "email",
            },
            {
                "legal_name": "Protec Safety & PPE Supplies SA",
                "trading_name": "Protec Safety Direct",
                "email": "sales@protecsafety.co.za",
                "phone": "+27 11 889 0044",
                "region": "Gauteng",
                "categories": ["ppe", "general-building"],
                "regions": ["Gauteng", "KwaZulu-Natal", "Western Cape", "National"],
                "compliance": {"bbee_level": "1", "csd_registered": True},
                "contact": "whatsapp",
            },
        ]

        supplier_orgs = []
        for s in suppliers_data:
            s_org = Organisation(
                id=generate_uuid(),
                type="supplier",
                legal_name=s["legal_name"],
                trading_name=s["trading_name"],
                email=s["email"],
                phone=s["phone"],
                region=s["region"],
                created_at=now,
                updated_at=now,
            )
            session.add(s_org)
            supplier_orgs.append(s_org)

            s_user = User(
                id=generate_uuid(),
                organisation_id=s_org.id,
                email=s["email"],
                name=f"{s['trading_name']} Representative",
                role="admin",
                created_at=now,
                updated_at=now,
            )
            session.add(s_user)

            s_profile = SupplierProfile(
                id=generate_uuid(),
                organisation_id=s_org.id,
                categories=s["categories"],
                service_regions=s["regions"],
                compliance_flags=s["compliance"],
                preferred_contact_method=s["contact"],
                active=True,
                created_at=now,
                updated_at=now,
            )
            session.add(s_profile)

        # 3. Create Sample BoQ
        sample_boq = BoQ(
            id=generate_uuid(),
            contractor_organisation_id=contractor_org.id,
            title="KZN Dept of Education - Umlazi High School Science Wing Upgrade",
            tender_reference="DOE-KZN-2026-088",
            tender_deadline=now + timedelta(days=14),
            region="KwaZulu-Natal",
            status="in_sourcing",
            created_at=now - timedelta(days=1),
            updated_at=now,
        )
        session.add(sample_boq)

        sample_items_data = [
            ("1.01", "Excavation in earth for foundation trenches not exceeding 2.0m deep", "m3", 320.0, "earthworks", 6500, 11000),
            ("1.02", "Supply and place 25MPa ready-mix concrete in foundation footings & slab", "m3", 115.0, "concrete", 185000, 240000),
            ("1.03", "Standard clay stock bricks (NFP) in 1:4 cement mortar for load-bearing walls", "no", 35000.0, "building-materials", 320, 450),
            ("1.04", "50kg All-Purpose Portland Cement CEM II 42.5N bags", "no", 500.0, "building-materials", 9200, 12500),
            ("1.05", "Treated timber roof trusses designed and fabricated to engineer specs", "m2", 240.0, "roofing", 26000, 42000),
            ("1.06", "0.5mm IBR Chromadek roof sheeting with sealants and fixings", "m2", 290.0, "roofing", 18000, 31000),
            ("1.07", "Personal Protective Equipment (PPE) site kits: hardhats, vests, boots", "no", 25.0, "ppe", 15000, 35000),
        ]

        for ref, desc, unit, qty, cat, b_min, b_max in sample_items_data:
            item = LineItem(
                id=generate_uuid(),
                boq_id=sample_boq.id,
                source_row_reference=ref,
                description=desc,
                unit=unit,
                quantity=qty,
                category=cat,
                benchmark_min_minor=b_min,
                benchmark_max_minor=b_max,
                benchmark_source="SA Industry Rate Guide 2026",
                benchmark_currency="ZAR",
                pricing_status="unsourced",
                parsing_confidence=0.96,
                created_at=now - timedelta(days=1),
                updated_at=now - timedelta(days=1),
            )
            session.add(item)

        await session.commit()
        print("[SUCCESS] Database successfully seeded with demo contractor, suppliers, and BoQ!")


if __name__ == "__main__":
    asyncio.run(seed_database())
